from __future__ import annotations

from collections import Counter
from xml.etree import ElementTree

from home_control.models import NowPlaying, Recommendation, WatchEvent

DEFAULT_PINS = ["netflix", "youtube", "prime", "hulu", "disney", "plex"]

FOLLOW_ONS: dict[str, list[tuple[str, str]]] = {
    "netflix": [
        ("youtube", "Trailers and recaps after an episode"),
        ("prime", "Another full-length option on this TV"),
    ],
    "youtube": [
        ("netflix", "Sit down for a full episode"),
        ("plex", "Play something you already own"),
    ],
    "prime": [
        ("netflix", "Flip if Prime is quiet tonight"),
        ("youtube", "A lighter follow-up"),
    ],
    "hulu": [
        ("netflix", "Another catalog if Hulu is thin"),
        ("disney", "Family-length follow-up"),
    ],
    "home": [
        ("netflix", "Start a show"),
        ("youtube", "Put something on quickly"),
    ],
    "hdmi 1": [
        ("netflix", "Leave HDMI and start an app"),
        ("youtube", "A quick app instead of the box"),
    ],
}

DEMO_PLAYLIST: list[tuple[str, str, str, str]] = [
    ("roku-192-168-1-40", "Netflix", "The Diplomat", "play"),
    ("roku-192-168-1-40", "YouTube", "F1 qualifying", "play"),
    ("roku-192-168-1-40", "Prime", "Reacher", "play"),
    ("samsung-192-168-1-41", "HDMI 1", "Cable box", "play"),
    ("sonos-192-168-1-50", "Sonos", "Jazz cafe", "play"),
]


def parse_roku_active_app(xml: str) -> tuple[str, str | None]:
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return "Home", None
    app = None
    for tag in root.iter():
        if tag.tag.lower().rsplit("}", 1)[-1] == "app":
            app = tag
            break
    if app is None:
        return "Home", None
    name = (app.text or "Home").strip() or "Home"
    app_id = app.attrib.get("id")
    return name, app_id


def parse_roku_media_player(xml: str) -> dict[str, str]:
    info: dict[str, str] = {"state": "unknown", "title": ""}
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return info
    state = root.attrib.get("state") or ""
    if state:
        info["state"] = state
    for tag in root.iter():
        local = tag.tag.lower().rsplit("}", 1)[-1]
        if local == "title" and tag.text:
            info["title"] = tag.text.strip()
        if local == "state" and tag.text:
            info["state"] = tag.text.strip()
    return info


def recommendations(now: list[NowPlaying], history: list[WatchEvent], device_id: str | None = None) -> list[Recommendation]:
    current_app = ""
    if now:
        pick = next((item for item in now if device_id and item.device_id == device_id), now[0])
        current_app = pick.app.lower()
        device_id = pick.device_id
    recs: list[Recommendation] = []
    seen: set[str] = set()
    for app, reason in FOLLOW_ONS.get(current_app, FOLLOW_ONS["home"]):
        if app in seen:
            continue
        seen.add(app)
        recs.append(Recommendation(app=app, reason=reason, device_id=device_id))
    counts = Counter(event.app.lower() for event in history)
    for app, _count in counts.most_common(3):
        if app in seen or app == current_app:
            continue
        seen.add(app)
        recs.append(
            Recommendation(
                app=app,
                reason=f"You have been in {app} most this session.",
                device_id=device_id,
            )
        )
        if len(recs) >= 4:
            break
    return recs[:4]


def accessed_summary(history: list[WatchEvent]) -> list[dict[str, str | int]]:
    counts = Counter(event.app for event in history)
    rows: list[dict[str, str | int]] = []
    for app, count in counts.most_common(8):
        rows.append({"app": app, "count": count})
    return rows


def demo_sample(device_id: str, tick: int) -> tuple[str, str, str] | None:
    matching = [row for row in DEMO_PLAYLIST if row[0] == device_id]
    if not matching:
        return None
    app, title, state = matching[tick % len(matching)][1:]
    return app, title, state
