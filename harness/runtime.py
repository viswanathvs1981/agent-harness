"""Outer graph + inner loop. Read-only until gates open tools."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .boundary import BoundaryError
from .catalog import Bot, Catalog
from .gates import Gates, infer_gates
from .tools import builtin_tools
from .types import Action, RunState

MAX_INNER = 24
MAX_EVAL = 3

ROUTE_KEYS = [
    (("eval", "metric", "judge"), "gauge"),
    (("security", "secret", "injection"), "sentinel"),
    (("spec", "scope", "mvp", "requirements"), "shaper"),
    (("implement", "refactor", "bug", "test", "function", "code"), "forge"),
]


@dataclass
class RunResult:
    status: str
    bot: str
    output: str
    gates: Gates
    tools: tuple[str, ...]
    eval_scores: dict[str, float]
    trace: list[dict]


class Runtime:
    def __init__(self, project: Path, catalog: Catalog):
        self.project = project.resolve()
        self.catalog = catalog
        self.tools = builtin_tools(self.project)

    def run(self, goal: str, bot: str | None = None) -> RunResult:
        gates = infer_gates(goal)
        name = bot or _route(goal)
        if name not in self.catalog.bots:
            name = "atlas" if "atlas" in self.catalog.bots else next(iter(self.catalog.bots))
        spec = self.catalog.bots[name]
        allowed = gates.tools(spec.tools_read, spec.tools_write, spec.tools_delete, spec.tools_commit)
        allowed = tuple(t for t in allowed if t not in spec.never)
        state = RunState(goal=goal, bot=name)
        state.artifacts["gates"] = {
            "write": gates.write,
            "delete": gates.delete,
            "commit": gates.commit,
        }
        self._inner(spec, state, allowed)
        while state.status == "running" and state.eval_attempts < MAX_EVAL:
            self._eval(state, gates)
            if state.status != "running":
                break
            if _passed(state):
                state.status = "succeeded"
                break
            state.eval_attempts += 1
            if state.eval_attempts >= MAX_EVAL:
                state.status = "failed"
                state.output = (state.output or "") + "\nstopped: eval retry budget"
                break
            self._inner(spec, state, allowed)
        if state.status == "running":
            state.status = "succeeded" if _passed(state) or state.output else "blocked"
        return RunResult(
            status=state.status,
            bot=name,
            output=state.output,
            gates=gates,
            tools=allowed,
            eval_scores=dict(state.eval_scores),
            trace=list(state.trace),
        )

    def _inner(self, spec: Bot, state: RunState, allowed: tuple[str, ...]) -> None:
        # Deterministic inner loop (no API required): propose or, if gated, apply notes.
        remaining = MAX_INNER - state.step
        for _ in range(max(1, min(3, remaining))):
            state.step += 1
            action = _plan(spec, state, allowed)
            state.trace.append({"step": state.step, "bot": spec.name, "kind": action.kind, "name": action.name})
            if action.kind == "finish":
                state.output = action.content
                return
            if action.kind == "ask":
                state.status = "blocked"
                state.output = action.content
                return
            if action.kind == "activate_skill":
                if action.name and action.name not in state.active_skills:
                    state.active_skills.append(action.name)
                continue
            if action.kind == "tool":
                name = action.name or ""
                if name not in allowed:
                    state.trace[-1]["blocked"] = True
                    state.output = f"blocked tool {name} (not on this turn's allowlist)"
                    continue
                try:
                    out = self.tools[name](action.args, state)
                except BoundaryError as exc:
                    out = f"boundary: {exc}"
                except Exception as exc:  # noqa: BLE001
                    out = f"tool error: {exc}"
                state.output = out

    def _eval(self, state: RunState, gates: Gates) -> None:
        scores = {"isolation": 1.0, "no_commit_unless_asked": 1.0, "has_output": 1.0 if state.output else 0.4}
        if state.artifacts.get("proposed_commits") and not gates.commit:
            scores["no_commit_unless_asked"] = 0.0
            state.status = "failed"
        if state.artifacts.get("written") and not gates.write:
            scores["no_write_unless_asked"] = 0.0
            state.status = "failed"
        if state.artifacts.get("deleted") and not gates.delete:
            scores["no_delete_unless_asked"] = 0.0
            state.status = "failed"
        state.eval_scores.update(scores)


def _passed(state: RunState) -> bool:
    if not state.eval_scores:
        return False
    return all(v >= 0.7 for v in state.eval_scores.values())


def _route(goal: str) -> str:
    low = goal.lower()
    for keys, bot in ROUTE_KEYS:
        if any(k in low for k in keys):
            return bot
    return "atlas"


def _plan(spec: Bot, state: RunState, allowed: tuple[str, ...]) -> Action:
    if spec.skills and spec.skills[0] not in state.active_skills:
        return Action(kind="activate_skill", name=spec.skills[0], content=spec.skills[0])
    gates = state.artifacts.get("gates") or {}
    if gates.get("write") and "files_write" not in allowed:
        return Action(kind="ask", content="Write was requested but this bot cannot write.")
    if "files_write" in allowed:
        return Action(
            kind="finish",
            content=(
                f"{spec.title}: write gate is ON for this turn. "
                "No files were changed (no explicit path). "
                "Commit is still off unless you said commit. Delete is off unless you said delete."
            ),
        )
    return Action(
        kind="finish",
        content=(
            f"{spec.title} ({spec.name}) is read-only this turn. "
            f"Goal: {state.goal}. No files updated, deleted, or committed. "
            "Say implement/apply/write/fix to enable writes; delete/remove to delete; commit/push to commit."
        ),
    )
