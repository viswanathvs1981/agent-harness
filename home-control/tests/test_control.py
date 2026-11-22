from __future__ import annotations

import unittest
from unittest.mock import patch

from home_control.control import (
    SAMSUNG_KEYS,
    parse_mac,
    parse_samsung_event,
    samsung_key_payload,
    send_command,
    wol_packet,
)
from home_control.models import TV_ACTIONS, Device


def _samsung() -> Device:
    return Device(
        id="samsung-10-0-0-8",
        name="Bedroom TV",
        kind="tv",
        manufacturer="samsung",
        model="8001",
        address="10.0.0.8",
        port=8001,
        protocol="samsung",
        capabilities=list(TV_ACTIONS),
    )


class SamsungControlTests(unittest.TestCase):
    def test_mute_tries_secure_port_first(self) -> None:
        with patch(
            "home_control.control._samsung_send",
            return_value={"event": "ms.channel.connect", "token": "1"},
        ) as send:
            result = send_command(_samsung(), "mute")
        self.assertTrue(result.ok)
        self.assertEqual(send.call_args.args[:3], ("10.0.0.8", 8002, "KEY_MUTE"))
        self.assertIn("Bedroom TV", result.message)

    def test_no_channel_explains_settings(self) -> None:
        with patch("home_control.control._samsung_send", side_effect=OSError("no channel")):
            result = send_command(_samsung(), "mute")
        self.assertFalse(result.ok)
        self.assertIn("Access Notification", result.message)

    def test_parse_connect_token(self) -> None:
        info = parse_samsung_event('{"event":"ms.channel.connect","data":{"token":"99"}}')
        self.assertEqual(info["event"], "ms.channel.connect")
        self.assertEqual(info["token"], "99")

    def test_payload_is_remote_click(self) -> None:
        payload = samsung_key_payload("KEY_VOLUP")
        self.assertEqual(payload["method"], "ms.remote.control")
        self.assertEqual(payload["params"]["DataOfCmd"], "KEY_VOLUP")
        self.assertEqual(payload["params"]["Cmd"], "Click")

    def test_known_actions_have_keys(self) -> None:
        for action in ("mute", "home", "select", "power_toggle"):
            self.assertIn(action, SAMSUNG_KEYS)

    def test_wol_packet_and_mac(self) -> None:
        self.assertEqual(parse_mac("AA-BB-CC-DD-EE-FF"), "aa:bb:cc:dd:ee:ff")
        packet = wol_packet("aa:bb:cc:dd:ee:ff")
        self.assertEqual(packet[:6], b"\xff" * 6)
        self.assertEqual(len(packet), 102)

    def test_launch_netflix_posts_application(self) -> None:
        device = _samsung()
        response = type("Resp", (), {"status_code": 200, "raise_for_status": lambda self: None})()
        with patch("home_control.control.httpx.Client") as client_cls:
            client = client_cls.return_value.__enter__.return_value
            client.post.return_value = response
            result = send_command(device, "launch", "netflix")
        self.assertTrue(result.ok)
        self.assertIn("netflix", result.message.lower())
        client.post.assert_called()
        self.assertIn("11101200001", client.post.call_args.args[0])

    def test_power_on_sends_wake_not_toggle(self) -> None:
        device = _samsung()
        device.extras["wifiMac"] = "aa:bb:cc:dd:ee:ff"
        with (
            patch("home_control.control.wake_on_lan") as wake,
            patch("home_control.control._samsung_send") as send,
        ):
            result = send_command(device, "power_on")
        self.assertTrue(result.ok)
        wake.assert_called_once()
        send.assert_not_called()
        self.assertIn("wake", result.message.lower())
