"""LLM providers. Default is a heuristic so the harness runs with no API key."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .types import Action, LLMResponse


class HeuristicLLM:
    """Deterministic planner used in tests and offline demos."""

    def __init__(self, script: list[Action] | None = None):
        self.script = list(script or [])
        self.i = 0

    def complete(self, messages: list[dict[str, Any]], *, tools: list[str] | None = None) -> LLMResponse:
        if self.i < len(self.script):
            action = self.script[self.i]
            self.i += 1
            return LLMResponse(text=action.content or action.kind, action=action)
        user = _last_user(messages)
        system = _system(messages)
        action = self._plan(user, system, tools or [])
        return LLMResponse(text=action.content or action.kind, action=action)

    def _plan(self, user: str, system: str, tools: list[str]) -> Action:
        blob = f"{system}\n{user}".lower()
        if "decide the next action" in user.lower() and "coding" in system.lower() and "tdd" in blob:
            if "activated skill" not in blob and "verifier-first" in blob:
                return Action(kind="activate_skill", name="verifier-first-coding", content="load verifier skill")
        if "unknown skill" in blob or "tool error" in blob:
            return Action(kind="finish", content="Recovered from a tool/skill failure and stopped.")
        if any(k in blob for k in ("write a failing test", "implement", "repo", "function")) and "files" in tools:
            if "outputs" not in blob:
                return Action(
                    kind="tool",
                    name="files",
                    args={"op": "note", "path": "plan.md", "content": "implement behind tests"},
                    content="draft implementation plan",
                )
        if "eval scores" in blob and "0." in blob:
            return Action(kind="finish", content="Loop complete; returning current artifacts.")
        if "goal:" in blob:
            return Action(kind="finish", content=_summary(user))
        return Action(kind="finish", content="No further actions.")


def _last_user(messages: list[dict[str, Any]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return str(m.get("content") or "")
    return ""


def _system(messages: list[dict[str, Any]]) -> str:
    parts = [str(m.get("content") or "") for m in messages if m.get("role") == "system"]
    return "\n".join(parts)


def _summary(user: str) -> str:
    goal = user
    if "Goal:" in user:
        goal = user.split("Goal:", 1)[1].split("\n", 1)[0].strip()
    return f"Completed work toward: {goal}"


class OpenAICompatLLM:
    """Optional HTTP provider. Works with OpenAI, Azure, or any /v1/chat/completions proxy."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "gpt-4.1-mini",
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("HARNESS_API_KEY")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.model = os.environ.get("HARNESS_MODEL") or model

    def complete(self, messages: list[dict[str, Any]], *, tools: list[str] | None = None) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("No API key set; use HeuristicLLM or export OPENAI_API_KEY")
        payload = {
            "model": self.model,
            "messages": messages
            + [
                {
                    "role": "system",
                    "content": (
                        "Reply as JSON: {\"kind\": \"think|tool|activate_skill|spawn_agent|finish|ask_human\","
                        " \"name\": optional, \"content\": string, \"args\": object}."
                    ),
                }
            ],
            "temperature": 0.2,
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM HTTP error: {exc}") from exc
        text = data["choices"][0]["message"]["content"]
        action = parse_action(text)
        usage = data.get("usage") or {}
        return LLMResponse(text=text, action=action, usage=usage)


def parse_action(text: str) -> Action:
    blob = text.strip()
    if blob.startswith("```"):
        blob = blob.strip("`")
        if blob.startswith("json"):
            blob = blob[4:]
        blob = blob.strip()
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return Action(kind="finish", content=text)
    kind = str(data.get("kind") or "finish")
    return Action(
        kind=kind,
        content=str(data.get("content") or ""),
        name=data.get("name"),
        args=dict(data.get("args") or {}),
    )


def default_llm() -> HeuristicLLM | OpenAICompatLLM:
    if os.environ.get("OPENAI_API_KEY") or os.environ.get("HARNESS_API_KEY"):
        return OpenAICompatLLM()
    return HeuristicLLM()
