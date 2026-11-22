from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx

from home_control.app import create_app
from home_control.brain import load_anthropic_key, run_claude
from home_control.hub import Hub
from fastapi.testclient import TestClient


def _payload(content, stop_reason: str = "end_turn") -> dict:
    return {"content": content, "stop_reason": stop_reason}


class LoadKeyTests(unittest.TestCase):
    def test_reads_env(self) -> None:
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-env"}, clear=False):
            with patch("home_control.brain.Path.home", return_value=Path("/tmp/no-room-home")):
                self.assertEqual(load_anthropic_key(), "sk-env")

    def test_reads_file_when_env_empty(self) -> None:
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "", "HOME_CONTROL_ANTHROPIC_KEY": ""}, clear=False):
            with patch("home_control.brain.Path.home") as home:
                root = Path("/tmp/room-key-test")
                home.return_value = root
                key_path = root / ".room" / "anthropic.key"
                key_path.parent.mkdir(parents=True, exist_ok=True)
                key_path.write_text(" sk-file \n")
                self.assertEqual(load_anthropic_key(), "sk-file")


class ClaudeChatTests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_use_launches_netflix_on_samsung(self) -> None:
        hub = Hub(demo=True, anthropic_key="sk-test")
        samsung = next(item for item in hub.snapshot() if item.protocol == "samsung")
        responses = [
            _payload(
                [
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "send_command",
                        "input": {
                            "device_id": samsung.id,
                            "action": "launch",
                            "value": "netflix",
                        },
                    }
                ],
                stop_reason="tool_use",
            ),
            _payload([{"type": "text", "text": "Opening Netflix on the Bedroom Samsung."}]),
        ]

        async def fake_post(_url, **_kwargs):
            payload = responses.pop(0)
            request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            return httpx.Response(200, json=payload, request=request)

        with patch("home_control.brain.httpx.AsyncClient") as client_cls:
            client = client_cls.return_value.__aenter__.return_value
            client.post = AsyncMock(side_effect=fake_post)
            result = await hub.chat_async("put something good on, maybe netflix")

        self.assertEqual(result.intent.action, "claude")
        self.assertTrue(result.command and result.command.ok)
        self.assertEqual(samsung.extras.get("app"), "netflix")
        self.assertIn("Netflix", result.reply)
        self.assertEqual(result.device_ids, [samsung.id])

    async def test_rejects_unknown_tool_action(self) -> None:
        hub = Hub(demo=True, anthropic_key="sk-test")
        samsung = next(item for item in hub.snapshot() if item.protocol == "samsung")
        responses = [
            _payload(
                [
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "send_command",
                        "input": {"device_id": samsung.id, "action": "rm_rf", "value": "/"},
                    }
                ],
                stop_reason="tool_use",
            ),
            _payload([{"type": "text", "text": "I will not send that."}]),
        ]

        async def fake_post(_url, **_kwargs):
            payload = responses.pop(0)
            request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            return httpx.Response(200, json=payload, request=request)

        with patch("home_control.brain.httpx.AsyncClient") as client_cls:
            client = client_cls.return_value.__aenter__.return_value
            client.post = AsyncMock(side_effect=fake_post)
            result = await run_claude(hub, "do something dangerous")

        self.assertIsNone(result.command)
        self.assertEqual(samsung.extras.get("app"), "HDMI 1")

    async def test_api_error_falls_back_to_rules(self) -> None:
        hub = Hub(demo=True, anthropic_key="sk-test")
        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        response = httpx.Response(401, request=request, text="nope")

        with patch("home_control.brain.httpx.AsyncClient") as client_cls:
            client = client_cls.return_value.__aenter__.return_value
            client.post = AsyncMock(return_value=response)
            result = await hub.chat_async("mute the samsung")

        self.assertTrue(result.command and result.command.ok)
        self.assertIn("Muted", result.reply)

    async def test_selected_device_is_sent_in_prompt(self) -> None:
        hub = Hub(demo=True, anthropic_key="sk-test")
        samsung = next(item for item in hub.snapshot() if item.protocol == "samsung")
        captured: list[dict] = []

        async def fake_post(_url, **kwargs):
            captured.append(kwargs["json"])
            request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
            return httpx.Response(
                200,
                json=_payload([{"type": "text", "text": "ok"}]),
                request=request,
            )

        with patch("home_control.brain.httpx.AsyncClient") as client_cls:
            client = client_cls.return_value.__aenter__.return_value
            client.post = AsyncMock(side_effect=fake_post)
            await hub.chat_async("mute", selected_id=samsung.id)

        user_text = captured[0]["messages"][0]["content"]
        self.assertIn(samsung.id, user_text)
        self.assertIn("Bedroom Samsung", user_text)


class HealthBrainTests(unittest.TestCase):
    def test_health_reports_claude_when_key_present(self) -> None:
        client = TestClient(create_app(Hub(demo=True, anthropic_key="sk-test")))
        data = client.get("/api/health").json()
        self.assertEqual(data["brain"], "claude")
        self.assertNotIn("sk-test", json.dumps(data))

    def test_health_reports_rules_without_key(self) -> None:
        client = TestClient(create_app(Hub(demo=True, anthropic_key="")))
        self.assertEqual(client.get("/api/health").json()["brain"], "rules")


if __name__ == "__main__":
    unittest.main()
