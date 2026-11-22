from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from home_control.hub import Hub, empty_network_hint
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
        self.assertIn("Demo only", result.reply)
        device = self.hub.devices[result.device_ids[0]]
        self.assertFalse(device.extras["power"])

    def test_help_explains_demo_is_not_the_house_tv(self) -> None:
        result = self.hub.chat("why are no controls working for samsung tv")
        self.assertEqual(result.intent.action, "help")
        self.assertIn("DEMO", result.reply)
        self.assertIn("house", result.reply.lower())

    def test_focus_samsung_does_not_list_the_lamp(self) -> None:
        result = self.hub.chat("for samsung tv")
        self.assertNotIn("Desk Lamp", result.reply)
        self.assertIn("Samsung", result.reply)

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

    def test_empty_hint_tells_user_to_run_on_mac(self) -> None:
        hint = empty_network_hint(lan_ip="172.30.0.2", demo=False, error=None, count=0)
        self.assertIn("127.0.0.1:8787", hint)
        self.assertIn("same Wi-Fi", hint)
        self.assertIn("python3 -m home_control", hint)


class DashboardHubTests(unittest.IsolatedAsyncioTestCase):
    async def test_tick_records_now_playing(self) -> None:
        hub = Hub(demo=True)
        playing = await hub.tick()
        apps = {item.device_id: item.app for item in playing}
        self.assertEqual(apps["roku-192-168-1-40"], "Netflix")
        self.assertTrue(hub.history)

    async def test_agent_notes_after_three_same_ticks(self) -> None:
        hub = Hub(demo=True)
        for _ in range(3):
            await hub.tick()
        self.assertTrue(any("Netflix" in note for note in hub.notes))

    async def test_chat_now_playing(self) -> None:
        hub = Hub(demo=True)
        result = await hub.chat_async("what's playing on the tv")
        self.assertIn("Netflix", result.reply)

    async def test_chat_history_and_recommend(self) -> None:
        hub = Hub(demo=True)
        await hub.tick()
        history = await hub.chat_async("what have I been watching")
        self.assertIn("Netflix", history.reply)
        recs = await hub.chat_async("what should I watch")
        self.assertIn("youtube", recs.reply.lower())

    async def test_pin_layout(self) -> None:
        hub = Hub(demo=True)
        result = await hub.chat_async("pin plex")
        self.assertIn("Pinned", result.reply)
        self.assertIn("plex", hub.pins)
        hub.set_layout(device_order=["sonos-192-168-1-50", "roku-192-168-1-40"])
        names = [item.id for item in hub.snapshot() if item.id in {"sonos-192-168-1-50", "roku-192-168-1-40"}]
        self.assertEqual(names[0], "sonos-192-168-1-50")


class LiveHubTests(unittest.IsolatedAsyncioTestCase):
    async def test_scan_does_not_raise_when_discover_fails(self) -> None:
        hub = Hub(demo=False)
        with patch("home_control.hub.discover", AsyncMock(side_effect=RuntimeError("lan down"))):
            devices = await hub.scan()
        self.assertEqual(devices, [])
        self.assertTrue(hub.last_error)

    async def test_chat_discover_explains_how_to_run_locally(self) -> None:
        hub = Hub(demo=False)
        with patch("home_control.hub.discover", AsyncMock(return_value=[])):
            result = await hub.chat_async("what's on my wifi")
        self.assertIn("127.0.0.1:8787", result.reply)
        self.assertIn("python3 -m home_control", result.reply)


if __name__ == "__main__":
    unittest.main()
