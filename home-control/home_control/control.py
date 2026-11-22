from __future__ import annotations

import json
import socket
import struct
from typing import Any
from urllib.parse import quote
from xml.sax.saxutils import escape

import httpx

from home_control.models import CommandResult, Device
from home_control.net import is_private_ip

ROKU_KEYS = {
    "power_on": "PowerOn",
    "power_off": "PowerOff",
    "power_toggle": "Power",
    "volume_up": "VolumeUp",
    "volume_down": "VolumeDown",
    "mute": "VolumeMute",
    "home": "Home",
    "back": "Back",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "select": "Select",
    "play": "Play",
    "pause": "Play",
    "stop": "Play",
    "rewind": "Rev",
    "forward": "Fwd",
    "info": "Info",
    "channel_up": "ChannelUp",
    "channel_down": "ChannelDown",
    "input": "InputHDMI1",
}

ROKU_APPS = {
    "netflix": "12",
    "youtube": "837",
    "prime": "13",
    "hulu": "2285",
    "disney": "291097",
    "spotify": "22297",
    "plex": "13535",
    "max": "61322",
}

SAMSUNG_KEYS = {
    "power_on": "KEY_POWER",
    "power_off": "KEY_POWER",
    "power_toggle": "KEY_POWER",
    "volume_up": "KEY_VOLUP",
    "volume_down": "KEY_VOLDOWN",
    "mute": "KEY_MUTE",
    "home": "KEY_HOME",
    "back": "KEY_RETURN",
    "up": "KEY_UP",
    "down": "KEY_DOWN",
    "left": "KEY_LEFT",
    "right": "KEY_RIGHT",
    "select": "KEY_ENTER",
    "play": "KEY_PLAY",
    "pause": "KEY_PAUSE",
    "stop": "KEY_STOP",
    "info": "KEY_INFO",
    "channel_up": "KEY_CHUP",
    "channel_down": "KEY_CHDOWN",
    "input": "KEY_HDMI",
}

SONY_IRCC = {
    "power_toggle": "AAAAAQAAAAEAAAAVAw==",
    "volume_up": "AAAAAQAAAAEAAAASAw==",
    "volume_down": "AAAAAQAAAAEAAAATAw==",
    "mute": "AAAAAQAAAAEAAAAUAw==",
    "home": "AAAAAQAAAAEAAABgAw==",
    "up": "AAAAAQAAAAEAAAB0Aw==",
    "down": "AAAAAQAAAAEAAAB1Aw==",
    "left": "AAAAAQAAAAEAAAA0Aw==",
    "right": "AAAAAQAAAAEAAAAzAw==",
    "select": "AAAAAQAAAAEAAABlAw==",
    "back": "AAAAAgAAAJcAAAAjAw==",
    "play": "AAAAAgAAAJcAAAAaAw==",
    "pause": "AAAAAgAAAJcAAAAZAw==",
    "input": "AAAAAQAAAAEAAAAlAw==",
}


def send_command(device: Device, action: str, value: Any = None, secrets: dict[str, str] | None = None) -> CommandResult:
    if not is_private_ip(device.address):
        return CommandResult(False, "Refusing to talk to a non-private address.", device.id)
    if action not in device.capabilities and device.protocol != "plugin":
        return CommandResult(False, f"{device.name} cannot {action.replace('_', ' ')}.", device.id)
    secrets = secrets or {}
    try:
        if device.protocol == "roku":
            return _roku(device, action, value)
        if device.protocol == "kasa":
            return _kasa(device, action)
        if device.protocol == "shelly":
            return _shelly(device, action)
        if device.protocol == "tasmota":
            return _tasmota(device, action)
        if device.protocol == "sonos":
            return _sonos(device, action, value)
        if device.protocol == "sony":
            return _sony(device, action, secrets.get("sony_psk", ""))
        if device.protocol == "samsung":
            return CommandResult(
                False,
                "Samsung TVs need a one-time pairing prompt on the TV. Use the Roku/cast path or drop tv.py in plugins/.",
                device.id,
            )
        if device.protocol in {"cast", "lg", "appletv", "firetv", "hue", "ipp", "plex", "jellyfin", "homeassistant", "unknown"}:
            return CommandResult(
                False,
                f"{device.name} was found, but {device.protocol} control needs pairing or a plugin. Drop tv.py in plugins/ to wire it.",
                device.id,
            )
        return CommandResult(False, f"No adapter for {device.protocol}.", device.id)
    except (OSError, httpx.HTTPError) as exc:
        return CommandResult(False, f"{device.name} did not respond ({exc.__class__.__name__}).", device.id)


def _roku(device: Device, action: str, value: Any) -> CommandResult:
    base = f"http://{device.address}:8060"
    with httpx.Client(timeout=2.5) as client:
        if action == "launch":
            app_id = ROKU_APPS.get(str(value or "").lower(), str(value or ""))
            response = client.post(f"{base}/launch/{quote(str(app_id))}")
            response.raise_for_status()
            return CommandResult(True, f"Opening {value} on {device.name}.", device.id, {"app": value})
        if action == "volume_set":
            return CommandResult(
                False,
                "Roku remotes can raise and lower volume, but cannot set an absolute level.",
                device.id,
            )
        key = ROKU_KEYS.get(action)
        if action == "input" and value:
            key = {
                "hdmi1": "InputHDMI1",
                "hdmi2": "InputHDMI2",
                "hdmi3": "InputHDMI3",
                "hdmi4": "InputHDMI4",
                "tuner": "InputTuner",
            }.get(str(value).lower(), "InputHDMI1")
        if not key:
            return CommandResult(False, f"No Roku key for {action}.", device.id)
        response = client.post(f"{base}/keypress/{key}")
        response.raise_for_status()
    return CommandResult(True, f"Sent {action.replace('_', ' ')} to {device.name}.", device.id)


def _kasa(device: Device, action: str) -> CommandResult:
    state = 1 if action in {"power_on"} else 0 if action == "power_off" else None
    if action == "power_toggle":
        info = _kasa_rpc(device.address, {"system": {"get_sysinfo": {}}})
        relay = info.get("system", {}).get("get_sysinfo", {}).get("relay_state", 0)
        state = 0 if relay else 1
    if state is None:
        return CommandResult(False, "This Kasa device only supports power.", device.id)
    _kasa_rpc(device.address, {"system": {"set_relay_state": {"state": state}}})
    verb = "on" if state else "off"
    return CommandResult(True, f"Turned {device.name} {verb}.", device.id, {"power": bool(state)})


def _kasa_rpc(host: str, payload: dict[str, Any]) -> dict[str, Any]:
    raw = _kasa_encrypt(json.dumps(payload).encode())
    with socket.create_connection((host, 9999), timeout=2) as sock:
        sock.sendall(raw)
        size = sock.recv(4)
        if len(size) < 4:
            return {}
        length = struct.unpack(">I", size)[0]
        data = b""
        while len(data) < length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                break
            data += chunk
    return json.loads(_kasa_decrypt(data).decode())


def _kasa_encrypt(body: bytes) -> bytes:
    key = 171
    out = bytearray()
    for byte in body:
        key = key ^ byte
        out.append(key)
    return struct.pack(">I", len(body)) + bytes(out)


def _kasa_decrypt(body: bytes) -> bytes:
    key = 171
    out = bytearray()
    for byte in body:
        out.append(key ^ byte)
        key = byte
    return bytes(out)


def _shelly(device: Device, action: str) -> CommandResult:
    turn = {"power_on": "on", "power_off": "off", "power_toggle": "toggle"}[action]
    with httpx.Client(timeout=2.5) as client:
        response = client.get(f"http://{device.address}/relay/0", params={"turn": turn})
        if response.status_code >= 400:
            response = client.get(f"http://{device.address}/light/0", params={"turn": turn})
        response.raise_for_status()
    return CommandResult(True, f"Sent {turn} to {device.name}.", device.id, {"power": turn != "off"})


def _tasmota(device: Device, action: str) -> CommandResult:
    cmnd = {"power_on": "Power On", "power_off": "Power Off", "power_toggle": "Power Toggle"}[action]
    with httpx.Client(timeout=2.5) as client:
        response = client.get(f"http://{device.address}/cm", params={"cmnd": cmnd})
        response.raise_for_status()
    return CommandResult(True, f"Sent {cmnd} to {device.name}.", device.id)


def _sonos(device: Device, action: str, value: Any) -> CommandResult:
    if action in {"play", "pause", "stop"}:
        body = f"<u:{action.capitalize()} xmlns:u=\"urn:schemas-upnp-org:service:AVTransport:1\"><InstanceID>0</InstanceID></u:{action.capitalize()}>"
        _soap(device.address, 1400, "/MediaRenderer/AVTransport/Control", f"urn:schemas-upnp-org:service:AVTransport:1#{action.capitalize()}", body)
        return CommandResult(True, f"{action.capitalize()}ed {device.name}.", device.id)
    if action in {"volume_up", "volume_down", "volume_set", "mute"}:
        if action == "mute":
            body = "<u:SetMute xmlns:u=\"urn:schemas-upnp-org:service:RenderingControl:1\"><InstanceID>0</InstanceID><Channel>Master</Channel><DesiredMute>1</DesiredMute></u:SetMute>"
            _soap(device.address, 1400, "/MediaRenderer/RenderingControl/Control", "urn:schemas-upnp-org:service:RenderingControl:1#SetMute", body)
            return CommandResult(True, f"Muted {device.name}.", device.id)
        level = 10 if value is None else int(value)
        if action == "volume_up":
            level = min(100, 20)
        if action == "volume_down":
            level = max(0, 8)
        body = f"<u:SetVolume xmlns:u=\"urn:schemas-upnp-org:service:RenderingControl:1\"><InstanceID>0</InstanceID><Channel>Master</Channel><DesiredVolume>{int(level)}</DesiredVolume></u:SetVolume>"
        _soap(device.address, 1400, "/MediaRenderer/RenderingControl/Control", "urn:schemas-upnp-org:service:RenderingControl:1#SetVolume", body)
        return CommandResult(True, f"Set {device.name} volume.", device.id, {"volume": int(level)})
    return CommandResult(False, f"{device.name} cannot {action}.", device.id)


def _sony(device: Device, action: str, psk: str) -> CommandResult:
    code = SONY_IRCC.get(action)
    if not code:
        return CommandResult(False, f"No Sony code for {action}.", device.id)
    envelope = (
        '<?xml version="1.0"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        "<s:Body><u:X_SendIRCC xmlns:u=\"urn:schemas-sony-com:service:IRCC:1\">"
        f"<IRCCCode>{escape(code)}</IRCCCode></u:X_SendIRCC></s:Body></s:Envelope>"
    )
    headers = {
        "Content-Type": "text/xml; charset=UTF-8",
        "SOAPACTION": '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"',
    }
    if psk:
        headers["X-Auth-PSK"] = psk
    with httpx.Client(timeout=2.5) as client:
        response = client.post(f"http://{device.address}/sony/IRCC", content=envelope, headers=headers)
        response.raise_for_status()
    return CommandResult(True, f"Sent {action.replace('_', ' ')} to {device.name}.", device.id)


def _soap(host: str, port: int, path: str, soap_action: str, inner: str) -> None:
    envelope = (
        '<?xml version="1.0"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        f"<s:Body>{inner}</s:Body></s:Envelope>"
    )
    headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPACTION": f'"{soap_action}"'}
    with httpx.Client(timeout=2.5) as client:
        response = client.post(f"http://{host}:{port}{path}", content=envelope, headers=headers)
        response.raise_for_status()
