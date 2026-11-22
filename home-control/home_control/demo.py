from __future__ import annotations

from home_control.models import SWITCH_ACTIONS, TV_ACTIONS, Device


def demo_devices() -> list[Device]:
    living = Device(
        id="roku-192-168-1-40",
        name="Living Room Roku",
        kind="tv",
        manufacturer="Roku",
        model="Streaming Stick 4K",
        address="192.168.1.40",
        port=8060,
        protocol="roku",
        capabilities=list(TV_ACTIONS),
        extras={"power": True, "volume": 14, "muted": False, "app": "Home", "demo": True},
    )
    bedroom = Device(
        id="samsung-192-168-1-41",
        name="Bedroom Samsung",
        kind="tv",
        manufacturer="Samsung",
        model="QN90B",
        address="192.168.1.41",
        port=8001,
        protocol="samsung",
        capabilities=list(TV_ACTIONS),
        extras={"power": True, "volume": 8, "muted": False, "app": "HDMI 1", "demo": True},
    )
    kitchen = Device(
        id="sonos-192-168-1-50",
        name="Kitchen Sonos",
        kind="speaker",
        manufacturer="Sonos",
        model="One",
        address="192.168.1.50",
        port=1400,
        protocol="sonos",
        capabilities=["play", "pause", "stop", "volume_up", "volume_down", "volume_set", "mute"],
        extras={"power": True, "volume": 22, "muted": False, "demo": True},
    )
    plug = Device(
        id="kasa-192-168-1-60",
        name="Bedroom Plug",
        kind="plug",
        manufacturer="TP-Link",
        model="HS103",
        address="192.168.1.60",
        port=9999,
        protocol="kasa",
        capabilities=list(SWITCH_ACTIONS),
        extras={"power": False, "demo": True},
    )
    lamp = Device(
        id="shelly-192-168-1-61",
        name="Desk Lamp",
        kind="light",
        manufacturer="Shelly",
        model="Plus 1",
        address="192.168.1.61",
        port=80,
        protocol="shelly",
        capabilities=list(SWITCH_ACTIONS),
        extras={"power": True, "demo": True},
    )
    printer = Device(
        id="ipp-192-168-1-80",
        name="Office Printer",
        kind="printer",
        manufacturer="Brother",
        model="HL-L2395DW",
        address="192.168.1.80",
        port=631,
        protocol="ipp",
        capabilities=[],
        extras={"demo": True, "status": "idle"},
    )
    return [living, bedroom, kitchen, plug, lamp, printer]
