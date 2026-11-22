from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

from home_control.control import send_command
from home_control.demo import demo_devices
from home_control.discovery import discover
from home_control.intent import parse_intent
from home_control.models import ChatResult, CommandResult, Device, Intent, NowPlaying, WatchEvent
from home_control.net import is_private_ip, local_ipv4
from home_control.plugins import command_via_plugin, devices_from_plugin, load_tv_plugin, plugin_paths
from home_control.watch import (
    DEFAULT_PINS,
    accessed_summary,
    demo_sample,
    parse_roku_active_app,
    parse_roku_media_player,
    recommendations,
)


class Hub:
    def __init__(
        self,
        demo: bool = False,
        plugin_path: str | None = None,
        store_path: str | Path | None = None,
    ) -> None:
        self.demo = demo
        self.plugin_path = plugin_path or os.environ.get("HOME_CONTROL_TV_PLUGIN")
        self.devices: dict[str, Device] = {}
        self.last_error: str | None = None
        self.secrets = {
            "sony_psk": os.environ.get("HOME_CONTROL_SONY_PSK", ""),
        }
        self.now: list[NowPlaying] = []
        self.history: list[WatchEvent] = []
        self.notes: list[str] = []
        self.pins: list[str] = list(DEFAULT_PINS)
        self.device_order: list[str] = []
        self.ticks = 0
        self._last_sample: dict[str, tuple[str, str | None]] = {}
        self._same_count: dict[str, int] = {}
        self.store_path = Path(store_path) if store_path else None
        self._load()
        if self.demo:
            self._remember(demo_devices())

    def snapshot(self) -> list[Device]:
        order = {device_id: index for index, device_id in enumerate(self.device_order)}
        return sorted(
            self.devices.values(),
            key=lambda item: (order.get(item.id, 1000), item.kind, item.name.lower()),
        )

    def lan_ip(self) -> str | None:
        return local_ipv4()

    def hint(self) -> str:
        return empty_network_hint(self.lan_ip(), self.demo, self.last_error, len(self.devices))

    async def scan(self, deep: bool = False) -> list[Device]:
        found: list[Device] = []
        self.last_error = None
        if self.demo:
            found.extend(demo_devices())
        else:
            try:
                found.extend(await discover(timeout=3.0, deep=deep))
            except Exception as exc:
                self.last_error = f"{exc.__class__.__name__}: {exc}"
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
        result = send_command(device, action, value, self.secrets)
        return result

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
                return ChatResult(self.hint(), intent)
            listing = ", ".join(f"{item.name} ({item.kind})" for item in found)
            qualifier = "deep scan" if intent.deep else "scan"
            return ChatResult(f"{qualifier.capitalize()} found {len(found)} devices: {listing}.", intent, [item.id for item in found])
        if intent.action in {"now_playing", "history", "recommend", "pin", "unpin"}:
            await self.tick()
            return self._info_chat(intent)
        return self.chat(message)

    async def tick(self) -> list[NowPlaying]:
        self.ticks += 1
        playing: list[NowPlaying] = []
        for device in self.snapshot():
            if device.kind not in {"tv", "speaker"}:
                continue
            item = await self._sample(device)
            if item is None:
                continue
            playing.append(item)
            key = (item.app, item.title)
            if self._last_sample.get(device.id) != key:
                self.history.append(
                    WatchEvent(time.time(), device.id, device.name, item.app, item.title)
                )
                self.history = self.history[-200:]
                self._same_count[device.id] = 1
                self._last_sample[device.id] = key
                device.extras["app"] = item.app
                if item.title:
                    device.extras["title"] = item.title
                device.extras["watch_state"] = item.state
            else:
                self._same_count[device.id] = self._same_count.get(device.id, 0) + 1
                if self._same_count[device.id] == 3:
                    title = f" ({item.title})" if item.title else ""
                    note = f"Still on {item.app}{title} on {device.name}."
                    if not self.notes or self.notes[-1] != note:
                        self.notes.append(note)
                        self.notes = self.notes[-20:]
        self.now = playing
        self._save()
        return playing

    def dashboard(self) -> dict[str, Any]:
        recs = recommendations(self.now, self.history, self.now[0].device_id if self.now else None)
        return {
            "now": [item.to_dict() for item in self.now],
            "history": [item.to_dict() for item in reversed(self.history[-40:])],
            "recommendations": [item.to_dict() for item in recs],
            "accessed": accessed_summary(self.history),
            "pins": list(self.pins),
            "device_order": list(self.device_order),
            "notes": list(self.notes),
        }

    def set_layout(self, pins: list[str] | None = None, device_order: list[str] | None = None) -> dict[str, Any]:
        if pins is not None:
            cleaned: list[str] = []
            for pin in pins:
                name = str(pin).strip().lower().replace(" ", "")
                if name and name not in cleaned:
                    cleaned.append(name)
            self.pins = cleaned[:12]
        if device_order is not None:
            self.device_order = [str(item) for item in device_order if str(item) in self.devices]
        self._save()
        return {"pins": list(self.pins), "device_order": list(self.device_order)}

    def pin_app(self, app: str | None, remove: bool = False) -> bool:
        name = str(app or "").strip().lower().replace(" ", "")
        if not name:
            return False
        if remove:
            self.pins = [item for item in self.pins if item != name]
        elif name not in self.pins:
            self.pins.append(name)
        self._save()
        return True

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
                device.extras.update(
                    {
                        k: v
                        for k, v in current.extras.items()
                        if k in {"power", "volume", "muted", "app", "title", "launched", "watch_state"}
                    }
                )
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
            extras["title"] = None
            extras["launched"] = True
        elif action == "input":
            extras["app"] = str(value or "input")
            extras["launched"] = True
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

    def _info_chat(self, intent: Intent) -> ChatResult:
        if intent.action == "pin":
            ok = self.pin_app(str(intent.value) if intent.value else None)
            if not ok:
                return ChatResult("Name an app to pin, like pin youtube.", intent)
            return ChatResult(f"Pinned {intent.value} on the remote.", intent)
        if intent.action == "unpin":
            ok = self.pin_app(str(intent.value) if intent.value else None, remove=True)
            if not ok:
                return ChatResult("Name an app to unpin.", intent)
            return ChatResult(f"Removed {intent.value} from the remote.", intent)
        if intent.action == "now_playing":
            if not self.now:
                return ChatResult(
                    "Nothing is reporting as playing yet. Leave this page open and I will keep checking.",
                    intent,
                )
            lines = [
                f"{item.device_name}: {item.app}" + (f" — {item.title}" if item.title else "")
                for item in self.now
            ]
            return ChatResult("Now: " + "; ".join(lines), intent, [item.device_id for item in self.now])
        if intent.action == "history":
            if not self.history:
                return ChatResult("I have not seen any watching yet.", intent)
            recent = self.history[-8:]
            listing = ", ".join(
                f"{item.app}" + (f" ({item.title})" if item.title else "") for item in recent
            )
            return ChatResult(f"Accessed this session: {listing}.", intent)
        recs = recommendations(self.now, self.history, self.now[0].device_id if self.now else None)
        if not recs:
            return ChatResult("No recommendations yet. Watch something and I will suggest a follow-up.", intent)
        text = " ".join(f"{item.app}: {item.reason}." for item in recs)
        return ChatResult(text, intent, [item.device_id for item in recs if item.device_id])

    async def _sample(self, device: Device) -> NowPlaying | None:
        if self.demo or device.extras.get("demo"):
            if device.extras.get("launched") and device.extras.get("app"):
                return NowPlaying(
                    device.id,
                    device.name,
                    str(device.extras["app"]),
                    device.extras.get("title"),
                    "play",
                    "demo",
                )
            row = demo_sample(device.id, max(0, self.ticks - 1) // 3)
            if not row:
                return None
            app, title, state = row
            return NowPlaying(device.id, device.name, app, title, state, "demo")
        if device.protocol == "roku" and is_private_ip(device.address):
            return await self._sample_roku(device)
        app = device.extras.get("app")
        if app:
            return NowPlaying(
                device.id,
                device.name,
                str(app),
                device.extras.get("title"),
                str(device.extras.get("watch_state") or "unknown"),
                device.protocol,
            )
        return None

    async def _sample_roku(self, device: Device) -> NowPlaying | None:
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                app_response = await client.get(f"http://{device.address}:8060/query/active-app")
                app_response.raise_for_status()
                player_text = ""
                try:
                    player_response = await client.get(f"http://{device.address}:8060/query/media-player")
                    player_text = player_response.text
                except httpx.HTTPError:
                    player_text = ""
        except httpx.HTTPError:
            return None
        app, _app_id = parse_roku_active_app(app_response.text)
        player = parse_roku_media_player(player_text) if player_text else {}
        title = player.get("title") or None
        return NowPlaying(
            device.id,
            device.name,
            app,
            title,
            player.get("state") or "unknown",
            "roku",
        )

    def _load(self) -> None:
        if self.store_path is None or not self.store_path.exists():
            return
        try:
            payload = json.loads(self.store_path.read_text())
        except (OSError, json.JSONDecodeError):
            return
        pins = payload.get("pins")
        if isinstance(pins, list) and pins:
            self.pins = [str(item) for item in pins][:12]
        order = payload.get("device_order")
        if isinstance(order, list):
            self.device_order = [str(item) for item in order]
        for raw in payload.get("history") or []:
            try:
                self.history.append(
                    WatchEvent(
                        at=float(raw["at"]),
                        device_id=str(raw["device_id"]),
                        device_name=str(raw["device_name"]),
                        app=str(raw["app"]),
                        title=raw.get("title"),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        self.history = self.history[-200:]

    def _save(self) -> None:
        if self.store_path is None:
            return
        try:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "pins": self.pins,
                "device_order": self.device_order,
                "history": [item.to_dict() for item in self.history[-200:]],
            }
            self.store_path.write_text(json.dumps(payload))
        except OSError:
            return


def empty_network_hint(lan_ip: str | None, demo: bool, error: str | None, count: int) -> str:
    if demo:
        return (
            "Demo devices are loaded. Run this on a Mac on your home Wi-Fi without --demo "
            "to talk to the real network."
        )
    where = f" This machine’s address is {lan_ip}." if lan_ip else " This machine has no private LAN address."
    if error:
        return (
            f"Scan failed ({error}).{where} On a Mac on the same Wi-Fi as the TV, run: "
            "python3 -m home_control   then open http://127.0.0.1:8787"
        )
    if count:
        return ""
    return (
        "No devices answered. This process can only see the Wi-Fi of the machine it is running on — "
        "a Cursor Cloud agent cannot reach your house."
        f"{where} On a Mac on the same Wi-Fi as the TV, run: python3 -m home_control   "
        "then open http://127.0.0.1:8787. Try Deep scan, or --plugin ~/Downloads/tv.py."
    )


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
