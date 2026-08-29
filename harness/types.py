from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Status = Literal["running", "succeeded", "failed", "blocked"]


@dataclass
class Action:
    kind: str  # think | tool | activate_skill | finish | ask
    content: str = ""
    name: str | None = None
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunState:
    goal: str
    bot: str
    step: int = 0
    eval_attempts: int = 0
    eval_scores: dict[str, float] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)
    active_skills: list[str] = field(default_factory=list)
    status: Status = "running"
    output: str = ""
