from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from home_control.models import SWITCH_ACTIONS, TV_ACTIONS, ChatResult, CommandResult, Intent

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-4-5"
MAX_ROUNDS = 6
ALLOWED_COMMANDS = frozenset(TV_ACTIONS) | frozenset(SWITCH_ACTIONS)

SYSTEM = """You are Room, a local home-control agent.
You talk to TVs, speakers, plugs, and lights on this Wi-Fi only through tools.
Never invent device ids. Use list_devices if you are unsure.
If the UI selected a device, use that for vague requests like "the tv", "mute", or "switch to netflix".
If two devices still match, ask which one.
After send_command, report the tool result honestly. Do not claim a button was pressed unless ok is true.
Do not ask for API keys. Do not scan the public internet.
"""

TOOLS = [
    {
        "name": "list_devices",
        "description": "List devices currently known on this Wi-Fi.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "now_playing",
        "description": "What is on, recent access, and recommendations.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "scan",
        "description": "Scan this Wi-Fi for devices.",
        "input_schema": {
            "type": "object",
            "properties": {"deep": {"type": "boolean"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "pin_app",
        "description": "Pin or unpin an app shortcut on the remote.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app": {"type": "string"},
                "remove": {"type": "boolean"},
            },
            "required": ["app"],
            "additionalProperties": False,
        },
    },
    {
        "name": "send_command",
        "description": "Send a remote command to one known device.",
        "input_schema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "string"},
                "action": {"type": "string", "enum": sorted(ALLOWED_COMMANDS)},
                "value": {"type": ["string", "integer", "null"]},
            },
            "required": ["device_id", "action"],
            "additionalProperties": False,
        },
    },
]


def load_anthropic_key() -> str:
    env = (
        os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("HOME_CONTROL_ANTHROPIC_KEY")
        or ""
    ).strip()
    if env:
        return env
    path = Path.home() / ".room" / "anthropic.key"
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return ""


def public_device(device: Any) -> dict[str, Any]:
    extras = device.extras or {}
    return {
        "id": device.id,
        "name": device.name,
        "kind": device.kind,
        "protocol": device.protocol,
        "capabilities": list(device.capabilities),
        "app": extras.get("app"),
        "title": extras.get("title"),
        "muted": extras.get("muted"),
        "volume": extras.get("volume"),
        "power": extras.get("power"),
        "reachable": device.reachable,
    }


def _user_payload(hub: Any, message: str, selected_id: str | None) -> str:
    lines: list[str] = []
    selected = hub.devices.get(selected_id) if selected_id else None
    if selected is not None:
        lines.append(
            f"UI selected device: {selected.name} (id={selected.id}, protocol={selected.protocol}, kind={selected.kind})"
        )
    elif selected_id:
        lines.append(f"UI selected device id {selected_id} is not in the current device list.")
    last_id = getattr(hub, "last_device_id", None)
    last = hub.devices.get(last_id) if last_id else None
    if last is not None and (selected is None or last.id != selected.id):
        lines.append(f"Last commanded device: {last.name} (id={last.id})")
    lines.append(f"User said: {message}")
    return "\n".join(lines)


def _text_from(content: list[Any]) -> str:
    parts = [
        str(block.get("text") or "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ]
    return "\n".join(part for part in parts if part).strip()


async def execute_tool(hub: Any, name: str, raw: Any) -> tuple[str, CommandResult | None]:
    if name == "list_devices":
        return json.dumps({"devices": [public_device(item) for item in hub.snapshot()]}), None
    if name == "now_playing":
        await hub.tick()
        dash = hub.dashboard()
        return json.dumps({key: dash[key] for key in ("now", "history", "recommendations", "accessed")}), None
    if not isinstance(raw, dict):
        return json.dumps({"ok": False, "error": "bad input"}), None
    if name == "scan":
        found = await hub.scan(deep=bool(raw.get("deep")))
        return json.dumps({"devices": [public_device(item) for item in found]}), None
    if name == "pin_app":
        ok = hub.pin_app(str(raw.get("app") or ""), remove=bool(raw.get("remove")))
        return json.dumps({"ok": ok, "pins": list(hub.pins)}), None
    if name == "send_command":
        action = str(raw.get("action") or "")
        device_id = str(raw.get("device_id") or "")
        if action not in ALLOWED_COMMANDS:
            return json.dumps({"ok": False, "error": f"action {action} is not allowed"}), None
        if device_id not in hub.devices:
            return json.dumps({"ok": False, "error": "unknown device_id"}), None
        result = hub.command(device_id, action, raw.get("value"))
        return json.dumps(result.to_dict()), result
    return json.dumps({"ok": False, "error": f"unknown tool {name}"}), None


async def run_claude(hub: Any, message: str, selected_id: str | None = None) -> ChatResult:
    key = str(getattr(hub, "anthropic_key", "") or "")
    if not key:
        raise RuntimeError("no anthropic key")
    model = str(getattr(hub, "anthropic_model", "") or DEFAULT_MODEL)
    user = _user_payload(hub, message, selected_id)
    messages: list[dict[str, Any]] = list(getattr(hub, "transcript", [])) + [
        {"role": "user", "content": user}
    ]
    last_command: CommandResult | None = None
    device_ids: list[str] = []
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        for _ in range(MAX_ROUNDS):
            response = await client.post(
                ANTHROPIC_URL,
                headers=headers,
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "system": SYSTEM,
                    "tools": TOOLS,
                    "messages": messages,
                },
            )
            response.raise_for_status()
            body = response.json()
            content = body.get("content") if isinstance(body.get("content"), list) else []
            tool_uses = [
                block
                for block in content
                if isinstance(block, dict) and block.get("type") == "tool_use"
            ]
            if not tool_uses:
                text = _text_from(content) or "Done."
                hub.transcript = (
                    list(getattr(hub, "transcript", []))
                    + [
                        {"role": "user", "content": user},
                        {"role": "assistant", "content": text},
                    ]
                )[-16:]
                return ChatResult(text, Intent(action="claude"), device_ids, last_command)
            messages.append({"role": "assistant", "content": content})
            results: list[dict[str, Any]] = []
            for block in tool_uses:
                payload, command = await execute_tool(
                    hub,
                    str(block.get("name") or ""),
                    block.get("input") or {},
                )
                if command is not None:
                    last_command = command
                    if command.device_id:
                        device_ids = [command.device_id]
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.get("id"),
                        "content": payload,
                    }
                )
            messages.append({"role": "user", "content": results})
    return ChatResult(
        "Claude stopped after too many tool calls.",
        Intent(action="claude"),
        device_ids,
        last_command,
    )
