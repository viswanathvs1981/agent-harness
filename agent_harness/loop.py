"""Inner agent loop: the harness that lets a model pick the next step.

This is Ng's "agent harness" half of the spectrum. The outer graph decides
*which* specialist runs; this loop decides *what that specialist does*
until a verifier fires, a budget is hit, or it yields.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .types import Action, AgentSpec, LLMResponse, RunState, Skill


class LLM(Protocol):
    def complete(self, messages: list[dict[str, Any]], *, tools: list[str] | None = None) -> LLMResponse:
        ...


ToolFn = Callable[[dict[str, Any], RunState], str]


@dataclass
class LoopConfig:
    max_steps: int = 8
    require_verifier: bool = False


class AgentLoop:
    def __init__(
        self,
        llm: LLM,
        tools: dict[str, ToolFn],
        skills: dict[str, Skill],
        spawn: Callable[[str, RunState], str] | None = None,
    ):
        self.llm = llm
        self.tools = tools
        self.skills = skills
        self.spawn = spawn

    def run(self, agent: AgentSpec, state: RunState, config: LoopConfig | None = None) -> RunState:
        cfg = config or LoopConfig(max_steps=agent.max_steps)
        allowed = set(agent.tools)
        messages = self._seed_messages(agent, state)
        for _ in range(cfg.max_steps):
            state.step += 1
            response = self.llm.complete(messages, tools=list(allowed))
            action = response.action or Action(kind="finish", content=response.text)
            state.trace.append(
                {
                    "step": state.step,
                    "agent": agent.name,
                    "kind": action.kind,
                    "name": action.name,
                    "content": action.content[:500],
                }
            )
            result, done = self._apply(action, agent, state, allowed)
            messages.append({"role": "assistant", "content": response.text or action.content})
            messages.append({"role": "user", "content": result})
            state.messages = messages[-24:]
            if done:
                break
        return state

    def _seed_messages(self, agent: AgentSpec, state: RunState) -> list[dict[str, Any]]:
        skill_catalog = [
            {"name": n, "description": self.skills[n].description}
            for n in agent.skills
            if n in self.skills
        ]
        loaded = []
        for name in state.active_skills:
            if name in self.skills:
                loaded.append(f"## Skill: {name}\n{self.skills[name].body}")
        system = (
            f"You are the '{agent.name}' agent ({agent.role}).\n"
            f"{agent.body}\n\n"
            f"Available skills (progressive disclosure — metadata only unless activated):\n"
            f"{skill_catalog}\n"
        )
        if loaded:
            system += "\nLoaded skill instructions:\n" + "\n\n".join(loaded)
        return [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": (
                    f"Goal: {state.goal}\n"
                    f"Artifacts: {state.artifacts}\n"
                    f"Eval scores: {state.eval_scores}\n"
                    "Decide the next action."
                ),
            },
        ]

    def _apply(
        self,
        action: Action,
        agent: AgentSpec,
        state: RunState,
        allowed: set[str],
    ) -> tuple[str, bool]:
        if action.kind == "finish":
            state.artifacts.setdefault("outputs", {})
            state.artifacts["outputs"][agent.name] = action.content
            return action.content or "done", True
        if action.kind == "ask_human":
            state.status = "waiting_human"
            state.artifacts["human_question"] = action.content
            return action.content, True
        if action.kind == "activate_skill":
            name = action.name or ""
            if name not in agent.skills and name not in self.skills:
                return f"unknown skill {name}", False
            if name not in state.active_skills:
                state.active_skills.append(name)
            skill = self.skills.get(name)
            body = skill.body if skill else ""
            return f"activated skill {name}\n{body[:4000]}", False
        if action.kind == "spawn_agent":
            if self.spawn is None:
                return "spawn not available", False
            name = action.name or ""
            result = self.spawn(name, state)
            return result, False
        if action.kind == "tool":
            name = action.name or ""
            if name not in allowed:
                return f"tool {name} is not permitted for agent {agent.name}", False
            fn = self.tools.get(name)
            if fn is None:
                return f"unknown tool {name}", False
            try:
                out = fn(action.args, state)
            except Exception as exc:  # noqa: BLE001 — tools must not kill the loop
                out = f"tool error: {exc}"
            return out, False
        if action.kind == "think":
            return f"noted: {action.content}", False
        return f"unsupported action {action.kind}", False
