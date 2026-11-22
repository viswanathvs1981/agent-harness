from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Kind = Literal["tv", "speaker", "light", "plug", "hub", "computer", "printer", "media", "other"]

TV_ACTIONS = (
    "power_on",
    "power_off",
    "power_toggle",
    "volume_up",
    "volume_down",
    "volume_set",
    "mute",
    "home",
    "back",
    "up",
    "down",
    "left",
    "right",
    "select",
    "play",
    "pause",
    "stop",
    "rewind",
    "forward",
    "info",
    "input",
    "launch",
    "channel_up",
    "channel_down",
)

SWITCH_ACTIONS = ("power_on", "power_off", "power_toggle")


@dataclass
class Device:
    id: str
    name: str
    kind: Kind
    manufacturer: str
    model: str
    address: str
    port: int
    protocol: str
    reachable: bool = True
    capabilities: list[str] = field(default_factory=list)
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Intent:
    action: str
    target_kind: str | None = None
    name_hint: str | None = None
    value: str | int | None = None
    deep: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CommandResult:
    ok: bool
    message: str
    device_id: str | None = None
    state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ChatResult:
    reply: str
    intent: Intent
    device_ids: list[str] = field(default_factory=list)
    command: CommandResult | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "reply": self.reply,
            "intent": self.intent.to_dict(),
            "device_ids": self.device_ids,
            "command": self.command.to_dict() if self.command else None,
        }
        return payload
