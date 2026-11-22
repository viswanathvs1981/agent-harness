from __future__ import annotations

import unittest

from home_control.intent import parse_intent


class IntentTests(unittest.TestCase):
    def test_scan_wifi(self) -> None:
        intent = parse_intent("what's on my wifi")
        self.assertEqual(intent.action, "discover")
        self.assertFalse(intent.deep)
        self.assertIsNone(intent.name_hint)

    def test_deep_scan(self) -> None:
        intent = parse_intent("deep scan the network")
        self.assertEqual(intent.action, "discover")
        self.assertTrue(intent.deep)

    def test_power_off_tv(self) -> None:
        intent = parse_intent("turn off the living room tv")
        self.assertEqual(intent.action, "power_off")
        self.assertEqual(intent.target_kind, "tv")
        self.assertEqual(intent.name_hint, "living room")

    def test_power_on_brand(self) -> None:
        intent = parse_intent("power on the roku")
        self.assertEqual(intent.action, "power_on")
        self.assertEqual(intent.name_hint, "roku")
        self.assertEqual(intent.target_kind, "tv")

    def test_volume_set(self) -> None:
        intent = parse_intent("set volume to 18")
        self.assertEqual(intent.action, "volume_set")
        self.assertEqual(intent.value, 18)

    def test_mute(self) -> None:
        intent = parse_intent("mute")
        self.assertEqual(intent.action, "mute")

    def test_hdmi_input(self) -> None:
        intent = parse_intent("switch to hdmi 1")
        self.assertEqual(intent.action, "input")
        self.assertEqual(intent.value, "hdmi1")

    def test_pause(self) -> None:
        intent = parse_intent("pause")
        self.assertEqual(intent.action, "pause")

    def test_launch_app(self) -> None:
        intent = parse_intent("open youtube on the tv")
        self.assertEqual(intent.action, "launch")
        self.assertEqual(intent.value, "youtube")
        self.assertEqual(intent.target_kind, "tv")

    def test_switch_to_netflix(self) -> None:
        intent = parse_intent("switch to netflix")
        self.assertEqual(intent.action, "launch")
        self.assertEqual(intent.value, "netflix")

    def test_main_menu(self) -> None:
        intent = parse_intent("show the main menu")
        self.assertEqual(intent.action, "home")

    def test_yes_is_confirm(self) -> None:
        intent = parse_intent("yes")
        self.assertEqual(intent.action, "confirm")

    def test_plug(self) -> None:
        intent = parse_intent("turn on the bedroom plug")
        self.assertEqual(intent.action, "power_on")
        self.assertEqual(intent.target_kind, "plug")
        self.assertEqual(intent.name_hint, "bedroom")

    def test_list(self) -> None:
        intent = parse_intent("list devices")
        self.assertEqual(intent.action, "list")

    def test_now_playing(self) -> None:
        intent = parse_intent("what's playing on the tv")
        self.assertEqual(intent.action, "now_playing")

    def test_curly_apostrophe_now_playing(self) -> None:
        intent = parse_intent("what’s playing on the tv")
        self.assertEqual(intent.action, "now_playing")

    def test_pairing_prompt_is_help(self) -> None:
        intent = parse_intent("i dont see a pairing prompt")
        self.assertEqual(intent.action, "help")

    def test_wifi_scan_not_now_playing(self) -> None:
        intent = parse_intent("what's on my wifi")
        self.assertEqual(intent.action, "discover")

    def test_recommend(self) -> None:
        intent = parse_intent("what should I watch")
        self.assertEqual(intent.action, "recommend")

    def test_history(self) -> None:
        intent = parse_intent("what have I been watching")
        self.assertEqual(intent.action, "history")

    def test_pin(self) -> None:
        intent = parse_intent("pin youtube")
        self.assertEqual(intent.action, "pin")
        self.assertEqual(intent.value, "youtube")

    def test_help_controls_not_working(self) -> None:
        intent = parse_intent("why are no controls working")
        self.assertEqual(intent.action, "help")

    def test_focus_samsung(self) -> None:
        intent = parse_intent("for samsung tv")
        self.assertEqual(intent.action, "focus")
        self.assertEqual(intent.target_kind, "tv")
        self.assertEqual(intent.name_hint, "samsung")

    def test_remote_direction(self) -> None:
        intent = parse_intent("press right")
        self.assertEqual(intent.action, "right")


if __name__ == "__main__":
    unittest.main()
