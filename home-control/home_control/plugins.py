from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from home_control.models import Device
from home_control.net import device_id, is_private_ip


def plugin_paths(explicit: str | None = None) -> list[Path]:
    paths: list[Path] = []
    if explicit:
        paths.append(Path(explicit).expanduser())
    bundled = Path(__file__).resolve().parent.parent / "plugins" / "tv.py"
    paths.append(bundled)
    cwd = Path.cwd() / "plugins" / "tv.py"
    if cwd not in paths:
        paths.append(cwd)
    seen: list[Path] = []
    for path in paths:
        if path.exists() and path not in seen:
            seen.append(path)
    return seen


def load_tv_plugin(path: Path) -> Any | None:
    spec = importlib.util.spec_from_file_location("home_control_tv_plugin", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def devices_from_plugin(module: Any) -> list[Device]:
    raw: list[Any] = []
    if hasattr(module, "discover"):
        raw = list(module.discover() or [])
    elif hasattr(module, "Controller"):
        raw = list(getattr(module.Controller(), "discover")() or [])
    devices: list[Device] = []
    for item in raw:
        devices.append(_coerce_device(item))
    return [device for device in devices if is_private_ip(device.address)]


def command_via_plugin(module: Any, device: Device, action: str, value: Any) -> dict[str, Any] | None:
    payload = device.to_dict()
    if hasattr(module, "command"):
        return _as_dict(module.command(payload, action, value))
    controller = getattr(module, "Controller", None)
    if controller is not None and hasattr(controller, "command"):
        return _as_dict(controller().command(payload, action, value))
    fn = getattr(module, action, None)
    if callable(fn):
        return _as_dict(fn(payload) if value is None else fn(payload, value))
    return None


def _coerce_device(item: Any) -> Device:
    if isinstance(item, Device):
        return item
    data = item if isinstance(item, dict) else getattr(item, "__dict__", {})
    address = str(data.get("address") or data.get("ip") or data.get("host") or "127.0.0.1")
    protocol = str(data.get("protocol") or "plugin")
    return Device(
        id=str(data.get("id") or device_id(protocol, address)),
        name=str(data.get("name") or "TV"),
        kind=data.get("kind") or "tv",
        manufacturer=str(data.get("manufacturer") or "plugin"),
        model=str(data.get("model") or ""),
        address=address,
        port=int(data.get("port") or 0),
        protocol=protocol,
        reachable=bool(data.get("reachable", True)),
        capabilities=list(data.get("capabilities") or ["power_on", "power_off", "volume_up", "volume_down", "mute"]),
        extras=dict(data.get("extras") or {"source": "plugin"}),
    )


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {"ok": True, "message": str(value)}
