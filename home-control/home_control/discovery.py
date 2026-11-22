from __future__ import annotations

import asyncio
import socket
import time
from collections.abc import Awaitable, Sequence
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx
from zeroconf import Zeroconf
from zeroconf.asyncio import AsyncServiceBrowser, AsyncZeroconf

from home_control.models import SWITCH_ACTIONS, TV_ACTIONS, Device
from home_control.net import classify_record, device_id, host_from_url, is_private_ip, local_ipv4

MDNS_TYPES = [
    "_googlecast._tcp.local.",
    "_androidtvremote2._tcp.local.",
    "_airplay._tcp.local.",
    "_raop._tcp.local.",
    "_hap._tcp.local.",
    "_hue._tcp.local.",
    "_sonos._tcp.local.",
    "_spotify-connect._tcp.local.",
    "_printer._tcp.local.",
    "_ipp._tcp.local.",
    "_companion-link._tcp.local.",
    "_http._tcp.local.",
    "_smb._tcp.local.",
    "_home-assistant._tcp.local.",
    "_elg._tcp.local.",
    "_matter._tcp.local.",
    "_smartthings._tcp.local.",
    "_nvstream._tcp.local.",
    "_roku._tcp.local.",
    "_lgconnect._tcp.local.",
]

SSDP_ST = [
    "ssdp:all",
    "upnp:rootdevice",
    "roku:ecp",
    "urn:dial-multiscreen-org:service:dial:1",
    "urn:schemas-upnp-org:device:MediaRenderer:1",
    "urn:schemas-upnp-org:device:MediaServer:1",
    "urn:lge-com:service:webos-second-screen:1",
    "urn:samsung.com:device:RemoteControlReceiver:1",
    "urn:schemas-sony-com:service:IRCC:1",
    "urn:Belkin:device:**",
]

PORT_HINTS = {
    8060: ("tv", "roku"),
    8001: ("tv", "samsung"),
    8002: ("tv", "samsung"),
    8008: ("tv", "cast"),
    8009: ("tv", "cast"),
    1400: ("speaker", "sonos"),
    3000: ("tv", "lg"),
    3001: ("tv", "lg"),
    9080: ("tv", "sony"),
    9999: ("plug", "kasa"),
    8123: ("hub", "homeassistant"),
    631: ("printer", "ipp"),
    32400: ("media", "plex"),
    8096: ("media", "jellyfin"),
    7345: ("tv", "vizio"),
}

DEFAULT_PROBE_PORTS: tuple[int, ...] = (8060, 8001, 8008, 1400, 3000, 9080)
DEEP_PROBE_PORTS: tuple[int, ...] = tuple(
    dict.fromkeys(
        [
            *DEFAULT_PROBE_PORTS,
            8002,
            8009,
            9999,
            8123,
            631,
            32400,
            8096,
            3001,
            7345,
        ]
    )
)


def capabilities_for(kind: str, protocol: str) -> list[str]:
    if protocol in {"roku", "samsung", "lg", "sony", "vizio", "appletv", "firetv", "cast"} or kind == "tv":
        caps = list(TV_ACTIONS)
        if protocol == "cast":
            caps = [item for item in caps if item not in {"power_on", "channel_up", "channel_down"}]
        return caps
    if protocol in {"kasa", "shelly", "tasmota", "wemo"} or kind in {"plug", "light"}:
        return list(SWITCH_ACTIONS)
    if protocol in {"sonos", "airplay"}:
        return ["play", "pause", "stop", "volume_up", "volume_down", "volume_set", "mute"]
    return []


async def discover(timeout: float = 3.0, deep: bool = False) -> list[Device]:
    found: dict[str, Device] = {}
    ports = DEEP_PROBE_PORTS if deep else DEFAULT_PROBE_PORTS
    groups = await asyncio.gather(
        _call(_mdns(timeout)),
        _call(asyncio.to_thread(_ssdp, timeout)),
        _call(_port_sweep(ports)),
    )
    for group in groups:
        for device in group:
            found.setdefault(device.id, device)
    await _enrich(found)
    return sorted(found.values(), key=lambda item: (item.kind, item.name.lower()))


async def _call(awaitable: Awaitable[list[Device]]) -> list[Device]:
    try:
        return await awaitable
    except Exception:
        return []


async def _mdns(timeout: float) -> list[Device]:
    devices: list[Device] = []
    try:
        azc = AsyncZeroconf()
    except OSError:
        return devices

    browser = None
    collected: list[tuple[str, str]] = []

    class Listener:
        def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            collected.append((type_, name))

        def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            return None

        def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            return None

        async def async_add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            collected.append((type_, name))

        async def async_update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            return None

        async def async_remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            return None

    try:
        browser = AsyncServiceBrowser(azc.zeroconf, MDNS_TYPES, Listener())
        await asyncio.sleep(timeout)
        for type_, name in collected:
            info = await azc.async_get_service_info(type_, name, timeout=500)
            if info is None or not info.parsed_addresses():
                continue
            address = info.parsed_addresses()[0]
            if not is_private_ip(address):
                continue
            label = name.split(".")[0].replace("\\", "")
            kind, protocol = classify_record(label, [type_], [info.port or 0])
            devices.append(
                Device(
                    id=device_id(protocol, address),
                    name=label,
                    kind=kind,  # type: ignore[arg-type]
                    manufacturer=protocol,
                    model=type_.rstrip("."),
                    address=address,
                    port=info.port or 0,
                    protocol=protocol,
                    capabilities=capabilities_for(kind, protocol),
                    extras={"source": "mdns", "service": type_},
                )
            )
    except Exception:
        return devices
    finally:
        if browser is not None:
            try:
                await browser.async_cancel()
            except Exception:
                pass
        try:
            await azc.async_close()
        except Exception:
            pass
    return devices


def _ssdp(timeout: float) -> list[Device]:
    devices: list[Device] = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lan = local_ipv4()
    if lan:
        try:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(lan))
        except OSError:
            pass
    sock.settimeout(0.4)
    try:
        for st in SSDP_ST:
            payload = _ssdp_packet(st)
            try:
                sock.sendto(payload, ("239.255.255.250", 1900))
            except OSError:
                continue
            try:
                sock.sendto(payload, ("255.255.255.255", 1900))
            except OSError:
                pass
        deadline = time.time() + timeout
        seen: set[str] = set()
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(65535)
            except TimeoutError:
                continue
            except OSError:
                break
            ip = addr[0]
            if not is_private_ip(ip):
                continue
            headers = _parse_ssdp(data.decode("utf-8", "replace"))
            location = headers.get("LOCATION", "")
            server = headers.get("SERVER", "")
            st = headers.get("ST", "")
            usn = headers.get("USN", "")
            key = usn or f"{ip}:{st}"
            if key in seen:
                continue
            seen.add(key)
            kind, protocol = classify_record(
                headers.get("WAKEUP", ""),
                [st, server, usn],
                [8060 if "roku" in (st + server).lower() else 0],
                extra=location,
            )
            port = urlparse(location).port or (8060 if protocol == "roku" else 0)
            name = _friendly_name(location) or protocol.upper()
            devices.append(
                Device(
                    id=device_id(protocol, ip),
                    name=name,
                    kind=kind,  # type: ignore[arg-type]
                    manufacturer=server.split("/")[0] if server else protocol,
                    model=st or "ssdp",
                    address=ip,
                    port=port,
                    protocol=protocol,
                    capabilities=capabilities_for(kind, protocol),
                    extras={"source": "ssdp", "location": location, "st": st},
                )
            )
    except OSError:
        return devices
    finally:
        sock.close()
    return devices


def _ssdp_packet(st: str) -> bytes:
    return "\r\n".join(
        [
            "M-SEARCH * HTTP/1.1",
            "HOST: 239.255.255.250:1900",
            'MAN: "ssdp:discover"',
            "MX: 2",
            f"ST: {st}",
            "",
            "",
        ]
    ).encode()


def _parse_ssdp(packet: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in packet.split("\r\n"):
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip().upper()] = value.strip()
    return headers


def _friendly_name(location: str) -> str | None:
    host = host_from_url(location)
    if not host or not is_private_ip(host):
        return None
    try:
        with httpx.Client(timeout=1.2, follow_redirects=True) as client:
            response = client.get(location)
            response.raise_for_status()
    except httpx.HTTPError:
        return None
    try:
        root = ElementTree.fromstring(response.text)
    except ElementTree.ParseError:
        return None
    for tag in root.iter():
        if tag.tag.lower().endswith("friendlyname") and tag.text:
            return tag.text.strip()
    return None


async def _port_sweep(ports: Sequence[int] | None = None) -> list[Device]:
    ip = local_ipv4()
    if not ip:
        return []
    prefix = ".".join(ip.split(".")[:3])
    probe_ports = list(ports or DEFAULT_PROBE_PORTS)
    devices: list[Device] = []
    sem = asyncio.Semaphore(64)

    async def probe(host: str, port: int) -> None:
        async with sem:
            try:
                _reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), 0.15)
                writer.close()
                try:
                    await writer.wait_closed()
                except OSError:
                    pass
            except (OSError, asyncio.TimeoutError):
                return
            kind, protocol = PORT_HINTS.get(port) or classify_record("", [], [port])
            devices.append(
                Device(
                    id=device_id(protocol, host),
                    name=f"{protocol} {host}",
                    kind=kind,  # type: ignore[arg-type]
                    manufacturer=protocol,
                    model=str(port),
                    address=host,
                    port=port,
                    protocol=protocol,
                    capabilities=capabilities_for(kind, protocol),
                    extras={"source": "port"},
                )
            )

    tasks = [probe(f"{prefix}.{n}", port) for n in range(1, 255) for port in probe_ports]
    await asyncio.gather(*tasks)
    return devices


async def _enrich(found: dict[str, Device]) -> None:
    await _enrich_roku(found)
    await _enrich_samsung(found)


async def _enrich_roku(found: dict[str, Device]) -> None:
    targets = [device for device in found.values() if device.protocol == "roku"]
    if not targets:
        return

    async with httpx.AsyncClient(timeout=1.5) as client:
        for device in targets:
            try:
                response = await client.get(f"http://{device.address}:8060/query/device-info")
                response.raise_for_status()
            except httpx.HTTPError:
                continue
            text = response.text
            device.port = 8060
            device.kind = "tv"
            device.protocol = "roku"
            device.capabilities = capabilities_for("tv", "roku")
            device.model = _xml_field(text, "model-name") or device.model
            device.manufacturer = "Roku"
            friendly = _xml_field(text, "user-device-name") or _xml_field(text, "friendly-device-name")
            if friendly:
                device.name = friendly


async def _enrich_samsung(found: dict[str, Device]) -> None:
    targets = [device for device in found.values() if device.protocol == "samsung"]
    if not targets:
        return
    async with httpx.AsyncClient(timeout=1.2) as client:
        for device in targets:
            port = device.port if device.port in {8001, 8002} else 8001
            try:
                response = await client.get(f"http://{device.address}:{port}/api/v2/")
                response.raise_for_status()
                info = response.json().get("device") or {}
            except (httpx.HTTPError, ValueError, TypeError):
                continue
            name = info.get("name") or info.get("model")
            if name:
                device.name = str(name)
            device.manufacturer = "Samsung"
            if info.get("model"):
                device.model = str(info["model"])
            device.port = port
            mac = info.get("wifiMac") or info.get("wifi_mac") or info.get("mac")
            if mac:
                device.extras["wifiMac"] = str(mac)


def _xml_field(text: str, tag: str) -> str | None:
    start = f"<{tag}>"
    end = f"</{tag}>"
    if start not in text:
        return None
    return text.split(start, 1)[1].split(end, 1)[0].strip() or None
