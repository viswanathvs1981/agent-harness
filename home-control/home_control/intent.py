from __future__ import annotations

import re

from home_control.models import Intent

_KIND_WORDS = {
    "tv": "tv",
    "tvs": "tv",
    "television": "tv",
    "televisions": "tv",
    "roku": "tv",
    "samsung": "tv",
    "lg": "tv",
    "sony": "tv",
    "vizio": "tv",
    "chromecast": "tv",
    "speaker": "speaker",
    "speakers": "speaker",
    "sonos": "speaker",
    "light": "light",
    "lights": "light",
    "lamp": "light",
    "bulb": "light",
    "plug": "plug",
    "plugs": "plug",
    "outlet": "plug",
    "printer": "printer",
    "hub": "hub",
}

_LAUNCH_APPS = (
    "youtube",
    "netflix",
    "hulu",
    "prime",
    "disney",
    "spotify",
    "plex",
    "hbo",
    "max",
    "apple tv",
)

_GENERIC_KIND = {
    "tv",
    "tvs",
    "television",
    "televisions",
    "speaker",
    "speakers",
    "light",
    "lights",
    "lamp",
    "bulb",
    "plug",
    "plugs",
    "outlet",
    "printer",
    "hub",
}

_NOISE = {
    "the",
    "a",
    "an",
    "my",
    "please",
    "on",
    "to",
    "for",
    "of",
    "in",
}


def parse_intent(text: str) -> Intent:
    raw = (text or "").strip()
    if not raw:
        return Intent(action="list")
    t = raw.lower().replace("’", "'").replace("‘", "'")
    kind = _extract_kind(t)
    name = _extract_name(t, kind)

    if re.search(r"\b(scan|discover|find devices|what(?:'s| is) on (?:my |the )?(?:wifi|wi-fi|network|lan))\b", t):
        return Intent(action="discover", target_kind=kind, name_hint=name, deep="deep" in t)

    if re.search(r"\b(recommend|suggestion|what should i watch|what to watch)\b", t):
        return Intent(action="recommend", target_kind=kind, name_hint=name)

    if re.search(r"\b(what have i (?:been )?watch(?:ing)?|watch history|what did i watch|accessed)\b", t):
        return Intent(action="history", target_kind=kind, name_hint=name)

    if re.search(
        r"\b(what(?:'s| is) (?:playing|on (?:the )?(?:tv|roku|samsung))|now playing|what am i watching|watching now)\b",
        t,
    ):
        return Intent(action="now_playing", target_kind=kind or "tv", name_hint=name)

    if re.search(r"\bunpin\b", t):
        app = _extract_app(t)
        return Intent(action="unpin", target_kind=kind, name_hint=name, value=app)

    if re.search(r"\bpin\b", t):
        app = _extract_app(t)
        return Intent(action="pin", target_kind=kind, name_hint=name, value=app)

    if re.search(
        r"\b(not working|doesn'?t work|do not work|no controls|why .*(work|control)|how do i|help|pair(?:ing)?|prompt)\b",
        t,
    ):
        return Intent(action="help", target_kind=kind or "tv", name_hint=name)

    if re.search(r"\b(list|show|what do you see)\b", t) and not re.search(
        r"\b(turn|power|volume|mute|pause|play|scan|discover|watch|recommend)\b", t
    ):
        return Intent(action="list", target_kind=kind, name_hint=name)

    if re.search(r"\b(hdmi\s*([1-4])|tuner|input)\b", t):
        match = re.search(r"hdmi\s*([1-4])", t)
        value = f"hdmi{match.group(1)}" if match else "input"
        return Intent(action="input", target_kind=kind or "tv", name_hint=name, value=value)

    app = _extract_app(t)
    if app and re.search(r"\b(open|launch|start|play)\b", t):
        return Intent(action="launch", target_kind=kind or "tv", name_hint=name, value=app)

    volume = re.search(r"\bvolume(?:\s*(?:to|at|=))?\s*(\d{1,3})\b", t)
    if volume:
        return Intent(
            action="volume_set",
            target_kind=kind,
            name_hint=name,
            value=max(0, min(100, int(volume.group(1)))),
        )
    if re.search(r"\b(volume up|turn it up|louder)\b", t):
        return Intent(action="volume_up", target_kind=kind, name_hint=name)
    if re.search(r"\b(volume down|turn it down|quieter)\b", t):
        return Intent(action="volume_down", target_kind=kind, name_hint=name)
    if re.search(r"\b(unmute|mute)\b", t):
        return Intent(action="mute", target_kind=kind, name_hint=name)

    if re.search(r"\b(turn|power|switch)\s+off\b", t) or re.search(r"\bshut off\b", t):
        return Intent(action="power_off", target_kind=kind, name_hint=name)
    if re.search(r"\b(turn|power|switch)\s+on\b", t):
        return Intent(action="power_on", target_kind=kind, name_hint=name)
    if re.search(r"\b(toggle|power toggle)\b", t):
        return Intent(action="power_toggle", target_kind=kind, name_hint=name)

    for action in (
        "home",
        "back",
        "pause",
        "play",
        "stop",
        "rewind",
        "forward",
        "select",
        "info",
    ):
        if re.search(rf"\b{action}\b", t):
            return Intent(action=action, target_kind=kind, name_hint=name)

    direction = re.search(r"\b(press |go )?(up|down|left|right)\b", t)
    if direction:
        return Intent(action=direction.group(2), target_kind=kind, name_hint=name)

    if re.search(r"\bchannel up\b", t):
        return Intent(action="channel_up", target_kind=kind or "tv", name_hint=name)
    if re.search(r"\bchannel down\b", t):
        return Intent(action="channel_down", target_kind=kind or "tv", name_hint=name)

    if kind or name:
        return Intent(action="focus", target_kind=kind, name_hint=name)
    return Intent(action="help", target_kind=kind, name_hint=name)


def _extract_kind(text: str) -> str | None:
    for word, kind in _KIND_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\b", text):
            return kind
    return None


def _extract_app(text: str) -> str | None:
    for app in _LAUNCH_APPS:
        if app in text:
            return app.replace(" ", "")
    return None


def _extract_name(text: str, kind: str | None) -> str | None:
    cleaned = re.sub(r"['’]", "", text.lower())
    cleaned = re.sub(r"[^a-z0-9\s-]", " ", cleaned)
    drop = set(_NOISE) | set(_GENERIC_KIND) | {
        "turn",
        "power",
        "switch",
        "off",
        "on",
        "set",
        "volume",
        "mute",
        "open",
        "launch",
        "start",
        "play",
        "pause",
        "scan",
        "discover",
        "list",
        "devices",
        "device",
        "wifi",
        "network",
        "press",
        "go",
        "up",
        "down",
        "left",
        "right",
        "hdmi",
        "input",
        "deep",
        "what",
        "whats",
        "is",
        "are",
        "it",
        "to",
        *{app.replace(" ", "") for app in _LAUNCH_APPS},
        "youtube",
        "netflix",
    }
    tokens = [
        tok
        for tok in cleaned.split()
        if tok not in drop and not tok.isdigit() and len(tok) > 1
    ]
    name = " ".join(tokens).strip()
    return name or None
