from __future__ import annotations

import base64
import json
import os
import socket
import ssl
import struct
import time
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
            tokens = secrets.get("samsung_tokens") if isinstance(secrets.get("samsung_tokens"), dict) else {}
            token = str(tokens.get(device.id) or secrets.get("samsung_token") or "")
            return _samsung(device, action, token)
        if device.protocol in {"cast", "lg", "appletv", "firetv", "hue", "ipp", "plex", "jellyfin", "homeassistant", "unknown"}:
            return CommandResult(
                False,
                f"{device.name} was found, but {device.protocol} control needs pairing or a plugin. Drop tv.py in plugins/ to wire it.",
                device.id,
            )
        return CommandResult(False, f"No adapter for {device.protocol}.", device.id)
    except (OSError, httpx.HTTPError) as exc:
        return CommandResult(False, f"{device.name} did not respond ({exc.__class__.__name__}).", device.id)


def samsung_key_payload(key: str) -> dict[str, Any]:
    return {
        "method": "ms.remote.control",
        "params": {
            "Cmd": "Click",
            "DataOfCmd": key,
            "Option": "false",
            "TypeOfRemote": "SendRemoteKey",
        },
    }


SAMSUNG_PAIR_HELP = (
    "No pairing popup appeared. On the Samsung open Settings → General → "
    "External Device Manager → Device Connect Manager and turn Access Notification On. "
    "Go to the Smart Hub home screen (not Netflix), press Mute again, and look for an allow prompt for Room."
)


def parse_samsung_event(raw: bytes | str) -> dict[str, str]:
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"event": "", "token": ""}
    event = str(payload.get("event") or "")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    token = str(data.get("token") or "")
    return {"event": event, "token": token}


def _samsung(device: Device, action: str, token: str = "") -> CommandResult:
    key = SAMSUNG_KEYS.get(action)
    if action == "launch":
        key = "KEY_HOME"
    if action == "volume_set":
        return CommandResult(
            False,
            "Samsung remotes can raise and lower volume, but cannot set an absolute level.",
            device.id,
        )
    if not key:
        return CommandResult(False, f"No Samsung key for {action}.", device.id)
    last_error: OSError | None = None
    for port in (8002, 8001):
        try:
            info = _samsung_send(device.address, port, key, token=token)
        except OSError as exc:
            last_error = exc
            continue
        state = {"token": info.get("token") or token, "port": port}
        if action == "launch":
            return CommandResult(
                True,
                f"Opened Home on {device.name}.",
                device.id,
                state,
            )
        extra = " Paired and saved the TV token." if info.get("token") and not token else ""
        return CommandResult(
            True,
            f"Sent {action.replace('_', ' ')} to {device.name}.{extra}",
            device.id,
            state,
        )
    detail = f" ({last_error})" if last_error else ""
    return CommandResult(False, SAMSUNG_PAIR_HELP + detail, device.id)


def _samsung_send(host: str, port: int, key: str, token: str = "") -> dict[str, str]:
    sock = _samsung_socket(host, port, token)
    try:
        sock.settimeout(12)
        info = {"event": "", "token": ""}
        deadline = time.time() + 12
        while time.time() < deadline:
            try:
                frame = _ws_read_frame(sock)
            except OSError:
                break
            info = parse_samsung_event(frame)
            if info["event"] in {"ms.channel.connect", "ms.channel.unauthorized", "ms.error"}:
                break
        if info["event"] != "ms.channel.connect":
            raise OSError(info["event"] or "samsung did not open a remote channel")
        _ws_write_frame(sock, json.dumps(samsung_key_payload(key)).encode())
        return info
    finally:
        try:
            sock.close()
        except OSError:
            pass


def _samsung_socket(host: str, port: int, token: str) -> socket.socket:
    name = quote(base64.b64encode(b"Room").decode(), safe="")
    path = f"/api/v2/channels/samsung.remote.control?name={name}"
    if token:
        path += f"&token={quote(token, safe='')}"
    ws_key = base64.b64encode(os.urandom(16)).decode()
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {ws_key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    raw = socket.create_connection((host, port), timeout=8)
    sock: socket.socket = raw
    if port == 8002:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        sock = ctx.wrap_socket(raw, server_hostname=host)
    sock.sendall(request.encode())
    header = _read_http_headers(sock)
    status = header.split("\r\n", 1)[0]
    if "101" not in status:
        sock.close()
        raise OSError(f"Samsung handshake failed on {port}: {status}")
    return sock


def _read_http_headers(sock: socket.socket) -> str:
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise OSError("Samsung closed the websocket handshake")
        buf += chunk
        if len(buf) > 65536:
            raise OSError("Samsung handshake too large")
    return buf.decode("iso-8859-1")


def _recv_exact(sock: socket.socket, count: int) -> bytes:
    buf = b""
    while len(buf) < count:
        chunk = sock.recv(count - len(buf))
        if not chunk:
            raise OSError("short websocket read")
        buf += chunk
    return buf


def _ws_write_frame(sock: socket.socket, payload: bytes) -> None:
    mask = os.urandom(4)
    header = bytearray([0x81])
    length = len(payload)
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack(">H", length))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack(">Q", length))
    header.extend(mask)
    masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    sock.sendall(bytes(header) + masked)


def _ws_read_frame(sock: socket.socket) -> bytes:
    header = _recv_exact(sock, 2)
    masked = header[1] & 0x80
    length = header[1] & 0x7F
    if length == 126:
        length = struct.unpack(">H", _recv_exact(sock, 2))[0]
    elif length == 127:
        length = struct.unpack(">Q", _recv_exact(sock, 8))[0]
    mask = _recv_exact(sock, 4) if masked else b""
    payload = _recv_exact(sock, length)
    if mask:
        payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    return payload


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
