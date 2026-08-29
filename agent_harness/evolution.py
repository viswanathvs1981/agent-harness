"""Self-evolution: observe → reflect → distill → promote → eval-gate.

Best-practice synthesis (Metis, ReMe, Mem2Evolve, Ng evals loop):

- Dual memory: experience (lessons) + assets (skills/tools/agents)
- Distill successes AND failures; prune stale lessons
- Promote a skill only after repeated reuse AND an eval pass
- Never rewrite the generic harness from a single lucky run
- Graph edges record which agent→skill paths actually worked
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .memory import MemoryGraph
from .persistence import Store
from .types import RunState, Skill


PROMOTE_THRESHOLD = 2


@dataclass
class EvolutionReport:
    lessons: list[str]
    promoted: list[str]
    pruned: int


class EvolutionEngine:
    def __init__(self, memory: MemoryGraph, store: Store, evolved_dir: Path):
        self.memory = memory
        self.store = store
        self.evolved_dir = evolved_dir
        evolved_dir.mkdir(parents=True, exist_ok=True)

    def after_run(self, state: RunState, outcome: str) -> EvolutionReport:
        episode_id = self.store.record_episode(state, outcome)
        ep_node = self.memory.upsert_node(
            "episode",
            f"episode:{episode_id}",
            {
                "goal": state.goal,
                "outcome": outcome,
                "agent": state.active_agent,
                "route": state.route,
                "scores": state.eval_scores,
            },
        )
        lessons = self._distill(state, outcome, ep_node)
        promoted: list[str] = []
        if outcome == "succeeded" and _passed(state):
            promoted = self._maybe_promote(state, ep_node)
        pruned = self.memory.prune(floor=0.08)
        return EvolutionReport(lessons=lessons, promoted=promoted, pruned=pruned)

    def _distill(self, state: RunState, outcome: str, ep_node: str) -> list[str]:
        labels: list[str] = []
        if outcome != "succeeded":
            label = f"failure:{state.route or state.active_agent or 'unknown'}"
            payload = {
                "goal": state.goal,
                "hint": "Inspect traces, add a deterministic eval, then retry the same graph node.",
            }
            nid = self.memory.upsert_node("lesson", label, payload)
            self.memory.add_edge(ep_node, nid, "distilled")
            labels.append(label)
        if state.active_skills:
            for skill in state.active_skills:
                label = f"used-skill:{skill}"
                nid = self.memory.upsert_node(
                    "lesson",
                    label,
                    {"skill": skill, "goal": state.goal, "agent": state.active_agent},
                )
                self.memory.bump(nid, 0.25 if outcome == "succeeded" else -0.15)
                self.memory.add_edge(ep_node, nid, "used")
                agent_id = self.memory.upsert_node("agent", state.active_agent or "unknown")
                skill_id = self.memory.upsert_node("skill", skill, {"name": skill})
                self.memory.add_edge(agent_id, skill_id, "used", weight=1.0 if outcome == "succeeded" else 0.2)
                labels.append(label)
        if state.artifacts.get("outputs"):
            label = f"pattern:{state.route or 'general'}"
            nid = self.memory.upsert_node(
                "pattern",
                label,
                {"route": state.route, "goal_tokens": state.goal[:200]},
            )
            self.memory.bump(nid, 0.2)
            self.memory.add_edge(ep_node, nid, "produced")
            labels.append(label)
        return labels

    def _maybe_promote(self, state: RunState, ep_node: str) -> list[str]:
        promoted: list[str] = []
        similar = self.store.similar_episodes(state.goal, limit=12)
        successes = [e for e in similar if e.outcome == "succeeded"]
        if len(successes) < PROMOTE_THRESHOLD:
            return promoted
        # Promote a procedural skill capturing the repeated route/skill combo.
        skill_name = _safe_skill_name(state.route or state.active_agent or "general")
        if not skill_name:
            return promoted
        body = _draft_skill(skill_name, state, successes)
        dest = self.evolved_dir / skill_name
        dest.mkdir(parents=True, exist_ok=True)
        skill_path = dest / "SKILL.md"
        skill_path.write_text(body, encoding="utf-8")
        skill_id = self.memory.upsert_node("skill", skill_name, {"path": str(skill_path), "evolved": True})
        self.memory.add_edge(ep_node, skill_id, "promoted")
        promoted.append(skill_name)
        return promoted

    def recall(self, goal: str) -> list[str]:
        hits = self.memory.retrieve(goal, types=("lesson", "pattern", "skill"), k=6)
        lines = []
        for h in hits:
            lines.append(f"[{h.type}] {h.label} (u={h.usefulness:.2f})")
        return lines


def _passed(state: RunState) -> bool:
    if not state.eval_scores:
        return False
    core = state.eval_scores.get("task")
    if core is None:
        return all(v >= 0.7 for v in state.eval_scores.values())
    return core >= 0.7


def _safe_skill_name(raw: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in raw).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    if not cleaned:
        return ""
    name = f"evolved-{cleaned}"[:64]
    return name.strip("-")


def _draft_skill(name: str, state: RunState, successes) -> str:
    steps = "\n".join(f"- {e.goal}" for e in successes[:5])
    skills = ", ".join(state.active_skills) or "none"
    return f"""---
name: {name}
description: Auto-promoted procedure for goals like '{state.goal[:180]}'. Use when similar coding or delivery work repeats.
license: Apache-2.0
metadata:
  origin: evolved
  route: {state.route or ""}
---

# {name}

This skill was promoted by the harness evolution loop after repeated successful episodes.

## When to use
Similar goals. Do not apply blindly to unrelated domains.

## Procedure
1. Reuse the `{state.active_agent or "conductor"}` agent.
2. Activate existing skills first: {skills}.
3. Close the loop with deterministic evals before declaring success.
4. Keep the coding agent isolated from production systems.

## Evidence
{steps}
"""


def load_evolved_skills(evolved_dir: Path) -> list[Skill]:
    from .catalog import load_skill

    skills: list[Skill] = []
    if not evolved_dir.is_dir():
        return skills
    for child in evolved_dir.iterdir():
        path = child / "SKILL.md"
        if path.is_file():
            skills.append(load_skill(path))
    return skills
