"""Graph engine: deterministic control flow with LLM-driven nodes inside.

Andrew Ng's skills map draws a spectrum from predefined workflows to a
harness that lets the model pick the next step. Production systems sit in
the middle: a graph for structure, loops for autonomy, evals as gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .types import GraphEdge, GraphSpec, RunState


class GraphError(RuntimeError):
    pass


Predicate = Callable[[RunState], bool]


@dataclass
class Transition:
    target: str
    when: str | None
    kind: str


class GraphRuntime:
    def __init__(self, spec: GraphSpec, predicates: dict[str, Predicate] | None = None):
        self.spec = spec
        self.predicates = predicates or {}
        if spec.entry not in spec.nodes:
            raise GraphError(f"Entry node {spec.entry!r} missing from graph {spec.id}")

    def neighbors(self, node_id: str) -> list[Transition]:
        return [
            Transition(target=e.target, when=e.when, kind=e.kind)
            for e in self.spec.edges
            if e.source == node_id
        ]

    def next_node(self, state: RunState) -> str | None:
        node = self.spec.nodes.get(state.current_node)
        if node is None:
            raise GraphError(f"Unknown node {state.current_node}")
        if node.type == "end":
            return None
        options = self.neighbors(state.current_node)
        if not options:
            return None
        unmatched: list[Transition] = []
        for opt in options:
            if opt.when is None:
                unmatched.append(opt)
                continue
            if self._matches(opt.when, state):
                return opt.target
        if unmatched:
            return unmatched[0].target
        return None

    def _matches(self, when: str, state: RunState) -> bool:
        if when in self.predicates:
            return self.predicates[when](state)
        if when == "pass":
            return _eval_passed(state)
        if when == "fail":
            return not _eval_passed(state)
        if when == "give_up":
            return int(state.artifacts.get("eval_attempts") or 0) >= 3 and not _eval_passed(state)
        if when.startswith("route:"):
            return state.route == when.split(":", 1)[1]
        if when.startswith("agent:"):
            return state.active_agent == when.split(":", 1)[1]
        # Treat as artifact / route equality
        if state.route == when:
            return True
        if state.artifacts.get("route") == when:
            return True
        if state.artifacts.get(when) is True:
            return True
        return False


def _eval_passed(state: RunState) -> bool:
    if not state.eval_scores:
        return False
    return all(score >= 0.7 for score in state.eval_scores.values())


def default_predicates() -> dict[str, Predicate]:
    return {
        "needs_spec": lambda s: s.artifacts.get("has_spec") is not True,
        "has_spec": lambda s: s.artifacts.get("has_spec") is True,
        "is_code": lambda s: s.route in {"coding", "fullstack", "reviewer"} or "code" in s.goal.lower(),
        "is_data": lambda s: s.route in {"data", "grounding", "ml"},
        "is_ops": lambda s: s.route in {"ops", "security"},
        "eval_pass": _eval_passed,
        "eval_fail": lambda s: not _eval_passed(s),
        "give_up": lambda s: int(s.artifacts.get("eval_attempts") or 0) >= 3 and not _eval_passed(s),
        "always": lambda s: True,
    }


def summarize_graph(spec: GraphSpec) -> dict[str, Any]:
    return {
        "id": spec.id,
        "entry": spec.entry,
        "nodes": [
            {"id": n.id, "type": n.type, "config": n.config} for n in spec.nodes.values()
        ],
        "edges": [
            {"from": e.source, "to": e.target, "when": e.when, "kind": e.kind}
            for e in spec.edges
        ],
    }


def validate_graph(spec: GraphSpec) -> list[str]:
    errors: list[str] = []
    if spec.entry not in spec.nodes:
        errors.append(f"missing entry {spec.entry}")
    for edge in spec.edges:
        if edge.source not in spec.nodes:
            errors.append(f"edge from unknown node {edge.source}")
        if edge.target not in spec.nodes:
            errors.append(f"edge to unknown node {edge.target}")
    reachable = set()
    stack = [spec.entry]
    while stack:
        nid = stack.pop()
        if nid in reachable:
            continue
        reachable.add(nid)
        for e in spec.edges:
            if e.source == nid:
                stack.append(e.target)
    orphaned = set(spec.nodes) - reachable
    if orphaned:
        errors.append(f"unreachable nodes: {sorted(orphaned)}")
    return errors
