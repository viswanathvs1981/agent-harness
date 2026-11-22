from __future__ import annotations

import unittest

from home_control.models import NowPlaying, WatchEvent
from home_control.watch import (
    accessed_summary,
    parse_roku_active_app,
    parse_roku_media_player,
    recommendations,
)


class WatchTests(unittest.TestCase):
    def test_parse_roku_active_app(self) -> None:
        xml = '<?xml version="1.0"?><active-app><app id="12">Netflix</app></active-app>'
        name, app_id = parse_roku_active_app(xml)
        self.assertEqual(name, "Netflix")
        self.assertEqual(app_id, "12")

    def test_parse_roku_media_player(self) -> None:
        xml = '<player state="play"><title>The Diplomat</title></player>'
        info = parse_roku_media_player(xml)
        self.assertEqual(info["state"], "play")
        self.assertEqual(info["title"], "The Diplomat")

    def test_recommendations_follow_current_app(self) -> None:
        now = [
            NowPlaying(
                device_id="roku-1",
                device_name="Living Room",
                app="Netflix",
                title="The Diplomat",
                state="play",
            )
        ]
        recs = recommendations(now, [])
        apps = [item.app for item in recs]
        self.assertIn("youtube", apps)
        self.assertTrue(any("trailer" in item.reason.lower() or "recap" in item.reason.lower() for item in recs))

    def test_accessed_summary_counts_apps(self) -> None:
        history = [
            WatchEvent(1.0, "roku-1", "Living Room", "Netflix", None),
            WatchEvent(2.0, "roku-1", "Living Room", "Netflix", None),
            WatchEvent(3.0, "roku-1", "Living Room", "YouTube", None),
        ]
        rows = accessed_summary(history)
        self.assertEqual(rows[0]["app"], "Netflix")
        self.assertEqual(rows[0]["count"], 2)
