from __future__ import annotations

import ipaddress
import socket


def is_private_ip(value: str) -> bool:
    try:
        addr = ipaddress.ip_address(value.split("%")[0])
    except ValueError:
        return False
    return bool(addr.is_private or addr.is_loopback or addr.is_link_local)


def looks_like_cloud_lan(value: str | None) -> bool:
    if not value:
        return False
    try:
        addr = ipaddress.ip_address(value.split("%")[0])
    except ValueError:
        return False
    return addr in ipaddress.ip_network("172.16.0.0/12")


def local_ipv4() -> str | None:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("1.1.1.1", 80))
        ip = sock.getsockname()[0]
        sock.close()
    except OSError:
        return None
    return ip if is_private_ip(ip) else None


def host_from_url(url: str) -> str | None:
    if "://" not in url:
        return None
    rest = url.split("://", 1)[1]
    host = rest.split("/")[0].split("@")[-1]
    host = host.rsplit("]", 1)[-1]
    host = host.split(":")[0]
    return host or None


def classify_record(
    name: str,
    services: list[str],
    ports: list[int],
    extra: str = "",
) -> tuple[str, str]:
    blob = " ".join([name, extra, *services]).lower()
    port_set = set(ports)

    if "roku" in blob or 8060 in port_set:
        return "tv", "roku"
    if "chromecast" in blob or "googlecast" in blob or 8009 in port_set or 8008 in port_set:
        return "tv", "cast"
    if "webos" in blob or "lgsmartdevice" in blob or "lg electronics" in blob:
        return "tv", "lg"
    if "bravia" in blob or ("sony" in blob and ("tv" in blob or 80 in port_set)):
        return "tv", "sony"
    if "vizio" in blob:
        return "tv", "vizio"
    if "samsung" in blob or 8001 in port_set or 8002 in port_set:
        return "tv", "samsung"
    if "apple tv" in blob or "appletv" in blob or "companion-link" in blob:
        return "tv", "appletv"
    if "firetv" in blob or "fire tv" in blob:
        return "tv", "firetv"
    if "sonos" in blob:
        return "speaker", "sonos"
    if "kasa" in blob or "tp-link" in blob or "tplink" in blob or 9999 in port_set:
        kind = "light" if any(token in blob for token in ("bulb", "kl", "lb")) else "plug"
        return kind, "kasa"
    if "shelly" in blob:
        return ("light" if "light" in blob else "plug"), "shelly"
    if "tasmota" in blob:
        return "plug", "tasmota"
    if "hue" in blob:
        return "hub", "hue"
    if "homeassistant" in blob or "home assistant" in blob or 8123 in port_set:
        return "hub", "homeassistant"
    if "printer" in blob or "_ipp." in blob or "_printer." in blob or 631 in port_set:
        return "printer", "ipp"
    if "plex" in blob or 32400 in port_set:
        return "media", "plex"
    if "jellyfin" in blob or 8096 in port_set:
        return "media", "jellyfin"
    if "_hap." in blob or "homekit" in blob:
        return "other", "homekit"
    if "_raop." in blob or "airplay" in blob:
        return "speaker", "airplay"
    if 1400 in port_set:
        return "speaker", "sonos"
    return "other", "unknown"


def device_id(protocol: str, address: str) -> str:
    return f"{protocol}-{address.replace('.', '-').replace(':', '-')}"
