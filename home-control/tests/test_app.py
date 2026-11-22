from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

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
        self.assertIn("127.0.0.1:8787", response.text)
        self.assertIn("same Wi-Fi", response.text)
        self.assertIn("Now", response.text)
        self.assertIn("Recommendations", response.text)
        self.assertIn("Accessed", response.text)

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

    def test_dashboard_and_layout(self) -> None:
        data = self.client.get("/api/dashboard").json()
        self.assertTrue(data["now"])
        self.assertTrue(data["recommendations"])
        self.assertIn("netflix", data["pins"])
        layout = self.client.put("/api/layout", json={"pins": ["youtube", "plex"]}).json()
        self.assertEqual(layout["pins"], ["youtube", "plex"])


class LiveAppTests(unittest.TestCase):
    def test_health_includes_run_locally_hint(self) -> None:
        client = TestClient(create_app(Hub(demo=False)))
        data = client.get("/api/health").json()
        self.assertFalse(data["demo"])
        self.assertIn("hint", data)
        self.assertIn("8787", data["hint"])

    def test_scan_returns_hint_when_empty(self) -> None:
        hub = Hub(demo=False)
        with patch("home_control.hub.discover", AsyncMock(return_value=[])):
            client = TestClient(create_app(hub))
            data = client.post("/api/scan", json={"deep": False}).json()
        self.assertEqual(data["devices"], [])
        self.assertIn("hint", data)
        self.assertIn("python3 -m home_control", data["hint"])


if __name__ == "__main__":
    unittest.main()

