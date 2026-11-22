from __future__ import annotations

import unittest

from home_control.hub import Hub
from home_control.intent import parse_intent
from home_control.net import is_private_ip


class HubTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hub = Hub(demo=True)

    def test_demo_loads_tvs_and_other_devices(self) -> None:
        kinds = {item.kind for item in self.hub.snapshot()}
        self.assertIn("tv", kinds)
        self.assertIn("plug", kinds)
        self.assertIn("speaker", kinds)

    def test_turn_off_living_room_tv(self) -> None:
        result = self.hub.chat("turn off the living room tv")
        self.assertIn("Living Room Roku", result.reply)
        device = self.hub.devices[result.device_ids[0]]
        self.assertFalse(device.extras["power"])

    def test_ambiguous_tv(self) -> None:
        result = self.hub.chat("mute the tv")
        self.assertIn("Which one", result.reply)
        self.assertGreaterEqual(len(result.device_ids), 2)

    def test_volume_on_named_speaker(self) -> None:
        result = self.hub.chat("set volume to 30 on the kitchen sonos")
        self.assertTrue(result.command and result.command.ok)
        speaker = next(item for item in self.hub.snapshot() if item.protocol == "sonos")
        self.assertEqual(speaker.extras["volume"], 30)

    def test_plug(self) -> None:
        result = self.hub.chat("turn on the bedroom plug")
        self.assertIn("Bedroom Plug", result.reply)
        plug = next(item for item in self.hub.snapshot() if item.kind == "plug")
        self.assertTrue(plug.extras["power"])

    def test_resolve_roku(self) -> None:
        matches = self.hub.resolve(parse_intent("pause the roku"))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].protocol, "roku")

    def test_unknown_device_command(self) -> None:
        result = self.hub.command("missing", "power_off")
        self.assertFalse(result.ok)

    def test_refuses_public_ip(self) -> None:
        self.assertFalse(is_private_ip("8.8.8.8"))


if __name__ == "__main__":
    unittest.main()
