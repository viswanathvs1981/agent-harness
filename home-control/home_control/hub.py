from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from home_control.control import send_command
from home_control.demo import demo_devices
from home_control.discovery import discover
from home_control.intent import parse_intent
from home_control.models import ChatResult, CommandResult, Device, Intent
from home_control.net import local_ipv4
from home_control.plugins import command_via_plugin, devices_from_plugin, load_tv_plugin, plugin_paths


class Hub:
    def __init__(self, demo: bool = False, plugin_path: str | None = None) -> None:
        self.demo = demo
        self.plugin_path = plugin_path or os.environ.get("HOME_CONTROL_TV_PLUGIN")
        self.devices: dict[str, Device] = {}
        self.secrets = {
            "sony_psk": os.environ.get("HOME_CONTROL_SONY_PSK", ""),
        }
        if self.demo:
            self._remember(demo_devices())

    def snapshot(self) -> list[Device]:
        return sorted(self.devices.values(), key=lambda item: (item.kind, item.name.lower()))

    def lan_ip(self) -> str | None:
        return local_ipv4()

    async def scan(self, deep: bool = False) -> list[Device]:
        found: list[Device] = []
        if self.demo:
            found.extend(demo_devices())
        else:
            found.extend(await discover(timeout=3.0, deep=deep))
        for device in self._plugin_devices():
            found.append(device)
        self._remember(found)
        return self.snapshot()

    def command(self, device_id: str, action: str, value: Any = None) -> CommandResult:
        device = self.devices.get(device_id)
        if device is None:
            return CommandResult(False, "I do not know that device. Scan first.")
        if self.demo or device.extras.get("demo"):
            return self._demo_command(device, action, value)
        plugin = self._plugin_module()
        if plugin is not None and device.protocol in {"plugin", "tv"}:
            payload = command_via_plugin(plugin, device, action, value)
            if payload is not None:
                ok = bool(payload.get("ok", True))
                message = str(payload.get("message") or f"Sent {action} to {device.name}.")
                return CommandResult(ok, message, device.id, dict(payload.get("state") or {}))
        return send_command(device, action, value, self.secrets)

    def chat(self, message: str) -> ChatResult:
        intent = parse_intent(message)
        if intent.action == "discover":
            return ChatResult(
                reply="Scanning the LAN is async from the UI. Use the Scan button, or POST /api/scan.",
                intent=intent,
            )
        devices = self.resolve(intent)
        if intent.action == "list":
            if not self.devices:
                return ChatResult(
                    "I have not scanned yet. Ask me to scan, or press Scan in the UI.",
                    intent,
                )
            listing = ", ".join(f"{item.name} ({item.kind})" for item in devices or self.snapshot())
            return ChatResult(f"On this network I see: {listing}.", intent, [item.id for item in devices or self.snapshot()])
        if not self.devices:
            return ChatResult("Scan the Wi-Fi first, then I can send that command.", intent)
        if not devices:
            return ChatResult("I could not match that to a device I have seen.", intent)
        if len(devices) > 1:
            names = ", ".join(item.name for item in devices)
            return ChatResult(f"Which one: {names}?", intent, [item.id for item in devices])
        result = self.command(devices[0].id, intent.action, intent.value)
        return ChatResult(result.message, intent, [devices[0].id], result)

    async def chat_async(self, message: str) -> ChatResult:
        intent = parse_intent(message)
        if intent.action == "discover":
            found = await self.scan(deep=intent.deep)
            if not found:
                return ChatResult(
                    "No devices answered. Run this app on a computer on the same Wi-Fi as the TV.",
                    intent,
                )
            listing = ", ".join(f"{item.name} ({item.kind})" for item in found)
            qualifier = "deep scan" if intent.deep else "scan"
            return ChatResult(f"{qualifier.capitalize()} found {len(found)} devices: {listing}.", intent, [item.id for item in found])
        return self.chat(message)

    def resolve(self, intent: Intent) -> list[Device]:
        pool = self.snapshot()
        if intent.target_kind:
            pool = [item for item in pool if item.kind == intent.target_kind]
        if intent.name_hint:
            hint = intent.name_hint.lower()
            named = [item for item in pool if hint in item.name.lower() or hint in item.protocol.lower()]
            if named:
                pool = named
        return pool

    def _remember(self, devices: list[Device]) -> None:
        for device in devices:
            current = self.devices.get(device.id)
            if current and current.extras.get("demo") and device.extras.get("demo"):
                device.extras = {**device.extras, **{k: current.extras.get(k, v) for k, v in device.extras.items()}}
                device.extras.update({k: v for k, v in current.extras.items() if k in {"power", "volume", "muted", "app"}})
            self.devices[device.id] = device

    def _demo_command(self, device: Device, action: str, value: Any) -> CommandResult:
        extras = device.extras
        if action == "power_on":
            extras["power"] = True
        elif action == "power_off":
            extras["power"] = False
        elif action == "power_toggle":
            extras["power"] = not extras.get("power", True)
        elif action == "mute":
            extras["muted"] = not extras.get("muted", False)
        elif action == "volume_up":
            extras["volume"] = min(100, int(extras.get("volume", 10)) + 2)
        elif action == "volume_down":
            extras["volume"] = max(0, int(extras.get("volume", 10)) - 2)
        elif action == "volume_set":
            extras["volume"] = max(0, min(100, int(value or 0)))
        elif action == "launch":
            extras["app"] = str(value or "app")
        elif action == "input":
            extras["app"] = str(value or "input")
        elif action not in device.capabilities:
            return CommandResult(False, f"{device.name} cannot {action.replace('_', ' ')}.", device.id)
        return CommandResult(True, _demo_message(device, action, value), device.id, dict(extras))

    def _plugin_module(self) -> Any | None:
        paths = plugin_paths(self.plugin_path)
        if not paths:
            return None
        try:
            return load_tv_plugin(paths[0])
        except Exception:
            return None

    def _plugin_devices(self) -> list[Device]:
        module = self._plugin_module()
        if module is None:
            return []
        try:
            return devices_from_plugin(module)
        except Exception:
            return []


def default_plugin_hint() -> str:
    path = Path(__file__).resolve().parent.parent / "plugins" / "tv.py"
    return str(path)


def _demo_message(device: Device, action: str, value: Any) -> str:
    if action == "power_on":
        return f"Turned {device.name} on."
    if action == "power_off":
        return f"Turned {device.name} off."
    if action == "mute":
        return f"{'Muted' if device.extras.get('muted') else 'Unmuted'} {device.name}."
    if action.startswith("volume"):
        return f"{device.name} volume is {device.extras.get('volume')}."
    if action == "launch":
        return f"Opening {value} on {device.name}."
    return f"Sent {action.replace('_', ' ')} to {device.name}."
