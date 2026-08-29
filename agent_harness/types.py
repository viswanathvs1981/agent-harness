"""Shared types for the harness, catalogs, graphs, and run state."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


Isolation = Literal["none", "context", "process"]
NodeType = Literal[
    "router",
    "agent",
    "skill",
    "loop",
    "eval",
    "tool",
    "parallel",
    "human",
    "evolve",
    "end",
]
RunStatus = Literal["running", "waiting_human", "succeeded", "failed"]


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str
    path: Path
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    allowed_tools: tuple[str, ...] = ()

    def catalog_entry(self) -> dict[str, str]:
        """Progressive disclosure stage 1: metadata only."""
        return {"name": self.name, "description": self.description}


@dataclass(frozen=True)
class AgentSpec:
    name: str
    description: str
    body: str
    path: Path
    role: str = "specialist"
    isolation: Isolation = "context"
    sandbox: bool = True
    tools: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    model: str = "inherit"
    max_steps: int = 16
    graph: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def catalog_entry(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "role": self.role,
            "isolation": self.isolation,
            "tools": list(self.tools),
            "skills": list(self.skills),
        }


@dataclass
class GraphNode:
    id: str
    type: NodeType
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    when: str | None = None
    kind: str = "normal"  # normal | loop


@dataclass
class GraphSpec:
    id: str
    entry: str
    nodes: dict[str, GraphNode]
    edges: list[GraphEdge]
    description: str = ""


@dataclass
class Action:
    kind: str  # think | tool | activate_skill | spawn_agent | finish | ask_human
    content: str = ""
    name: str | None = None
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    text: str
    action: Action | None = None
    usage: dict[str, int] = field(default_factory=dict)


@dataclass
class RunState:
    thread_id: str
    goal: str
    current_node: str
    step: int = 0
    messages: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    active_agent: str | None = None
    active_skills: list[str] = field(default_factory=list)
    eval_scores: dict[str, float] = field(default_factory=dict)
    status: RunStatus = "running"
    route: str | None = None
    trace: list[dict[str, Any]] = field(default_factory=list)
    loop_iters: dict[str, int] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "thread_id": self.thread_id,
            "goal": self.goal,
            "current_node": self.current_node,
            "step": self.step,
            "messages": self.messages,
            "artifacts": self.artifacts,
            "active_agent": self.active_agent,
            "active_skills": self.active_skills,
            "eval_scores": self.eval_scores,
            "status": self.status,
            "route": self.route,
            "trace": self.trace,
            "loop_iters": self.loop_iters,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> RunState:
        return cls(
            thread_id=data["thread_id"],
            goal=data["goal"],
            current_node=data["current_node"],
            step=data.get("step", 0),
            messages=list(data.get("messages", [])),
            artifacts=dict(data.get("artifacts", {})),
            active_agent=data.get("active_agent"),
            active_skills=list(data.get("active_skills", [])),
            eval_scores=dict(data.get("eval_scores", {})),
            status=data.get("status", "running"),
            route=data.get("route"),
            trace=list(data.get("trace", [])),
            loop_iters=dict(data.get("loop_iters", {})),
        )


@dataclass
class RunResult:
    thread_id: str
    status: RunStatus
    output: str
    state: RunState
    promoted_skills: list[str] = field(default_factory=list)
    eval_scores: dict[str, float] = field(default_factory=dict)
