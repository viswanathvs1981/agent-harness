from __future__ import annotations

import unittest
from unittest.mock import patch

from home_control.control import SAMSUNG_KEYS, samsung_key_payload, send_command
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
    def test_mute_sends_websocket_key(self) -> None:
        with patch("home_control.control._samsung_send") as send:
            result = send_command(_samsung(), "mute")
        self.assertTrue(result.ok)
        send.assert_called_once_with("10.0.0.8", 8001, "KEY_MUTE")
        self.assertIn("Bedroom TV", result.message)

    def test_payload_is_remote_click(self) -> None:
        payload = samsung_key_payload("KEY_VOLUP")
        self.assertEqual(payload["method"], "ms.remote.control")
        self.assertEqual(payload["params"]["DataOfCmd"], "KEY_VOLUP")
        self.assertEqual(payload["params"]["Cmd"], "Click")

    def test_known_actions_have_keys(self) -> None:
        for action in ("mute", "home", "select", "power_toggle"):
            self.assertIn(action, SAMSUNG_KEYS)
