from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from home_control.app import create_app
from home_control.hub import Hub


class AppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app(Hub(demo=True)))

    def test_index(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Room", response.text)
        self.assertIn("Agent", response.text)

    def test_health_demo(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["demo"])

    def test_devices_and_command(self) -> None:
        devices = self.client.get("/api/devices").json()["devices"]
        roku = next(item for item in devices if item["protocol"] == "roku")
        result = self.client.post(
            f"/api/devices/{roku['id']}/command",
            json={"action": "power_off"},
        )
        self.assertTrue(result.json()["ok"])

    def test_chat_scan(self) -> None:
        result = self.client.post("/api/chat", json={"message": "what's on my wifi"})
        self.assertEqual(result.status_code, 200)
        self.assertIn("devices", result.json()["reply"].lower())

    def test_missing_device(self) -> None:
        result = self.client.post("/api/devices/nope/command", json={"action": "power_off"})
        self.assertEqual(result.status_code, 404)


if __name__ == "__main__":
    unittest.main()
