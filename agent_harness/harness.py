"""Generic harness: catalog + graph + loop + persistence + evolution."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from .catalog import Catalog, load_graph
from .evals import EvalSuite, default_suite
from .evolution import EvolutionEngine, load_evolved_skills
from .graph import GraphRuntime, default_predicates, validate_graph
from .llm import HeuristicLLM, default_llm
from .loop import AgentLoop, LoopConfig
from .memory import MemoryGraph
from .persistence import Store
from .tools import builtin_tools
from .types import AgentSpec, GraphSpec, RunResult, RunState


class Harness:
    def __init__(
        self,
        project_root: Path | None = None,
        data_dir: Path | None = None,
        llm: Any | None = None,
        catalog: Catalog | None = None,
        eval_suite: EvalSuite | None = None,
    ):
        self.project_root = (project_root or Path.cwd()).resolve()
        self.data_dir = data_dir or (self.project_root / ".harness" / "state")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.catalog = catalog or Catalog(project_root=self.project_root)
        self.store = Store(self.data_dir / "harness.db")
        self.memory = MemoryGraph(self.data_dir / "memory.db")
        self.llm = llm or default_llm()
        self.eval_suite = eval_suite or default_suite()
        self.evolved_dir = self.data_dir / "evolved-skills"
        self.evolution = EvolutionEngine(self.memory, self.store, self.evolved_dir)
        self._merge_evolved_skills()
        self.tools = builtin_tools(self.project_root)
        self.loop = AgentLoop(self.llm, self.tools, self.catalog.skills, spawn=self._spawn)

    def close(self) -> None:
        self.store.close()
        self.memory.close()

    def run(
        self,
        goal: str,
        *,
        agent: str | None = None,
        graph: str = "default",
        thread_id: str | None = None,
        resume: bool = False,
    ) -> RunResult:
        thread_id = thread_id or uuid.uuid4().hex
        state = None
        if resume:
            state = self.store.load_latest(thread_id)
        if state is None:
            spec = self._graph(graph)
            state = RunState(thread_id=thread_id, goal=goal, current_node=spec.entry)
            if agent:
                state.active_agent = agent
                state.route = agent
                state.artifacts["has_spec"] = agent != "spec"
        else:
            spec = self._graph(graph)
        runtime = GraphRuntime(spec, default_predicates())
        errors = validate_graph(spec)
        if errors:
            raise RuntimeError(f"invalid graph {graph}: {errors}")

        hits = self.evolution.recall(goal)
        if hits:
            state.artifacts["memory_hits"] = hits

        safety = 64
        while state.status == "running" and safety > 0:
            safety -= 1
            node = spec.nodes.get(state.current_node)
            if node is None or node.type == "end":
                state.status = "succeeded"
                break
            self._execute_node(node.id, node.type, node.config, state, spec)
            self.store.save_checkpoint(state)
            if state.status in {"waiting_human", "failed"}:
                break
            nxt = runtime.next_node(state)
            if nxt is None:
                if state.status == "running":
                    state.status = "succeeded"
                break
            state.current_node = nxt

        outcome = "succeeded" if state.status == "succeeded" else state.status
        report = self.evolution.after_run(state, outcome)
        self._merge_evolved_skills()
        output = _final_output(state)
        return RunResult(
            thread_id=state.thread_id,
            status=state.status,
            output=output,
            state=state,
            promoted_skills=report.promoted,
            eval_scores=dict(state.eval_scores),
        )

    def _graph(self, name: str) -> GraphSpec:
        if name in self.catalog.graphs:
            return self.catalog.graphs[name]
        bundled = Path(__file__).resolve().parent / "catalog" / "graphs" / f"{name}.json"
        if bundled.is_file():
            return load_graph(bundled)
        raise KeyError(f"Unknown graph {name}")

    def _execute_node(self, node_id: str, ntype: str, config: dict, state: RunState, spec: GraphSpec) -> None:
        if ntype == "router":
            self._route(state, config)
            return
        if ntype == "agent":
            name = str(config.get("name") or state.route or "conductor")
            self._run_agent(name, state)
            return
        if ntype == "loop":
            name = str(config.get("agent") or state.route or "coding")
            max_iters = int(config.get("max_iters") or 4)
            key = node_id
            state.loop_iters[key] = state.loop_iters.get(key, 0) + 1
            self._run_agent(name, state)
            if state.loop_iters[key] >= max_iters:
                state.artifacts["loop_exhausted"] = True
            return
        if ntype == "skill":
            skill = str(config.get("name") or "")
            if skill and skill not in state.active_skills:
                state.active_skills.append(skill)
            return
        if ntype == "eval":
            result = self.eval_suite.run(state)
            self.store.record_eval(state.thread_id, result["suite"], float(result["overall"]), result)
            state.artifacts["last_eval"] = result
            attempts = int(state.artifacts.get("eval_attempts") or 0) + 1
            state.artifacts["eval_attempts"] = attempts
            if float(result["overall"]) < 0.7 and attempts >= 3:
                state.status = "failed"
            return
        if ntype == "evolve":
            # Evolution always runs after_run; this node records intent in the graph.
            state.artifacts["evolve"] = True
            return
        if ntype == "human":
            state.status = "waiting_human"
            return
        if ntype == "tool":
            name = str(config.get("name") or "")
            fn = self.tools.get(name)
            if fn:
                fn(dict(config.get("args") or {}), state)
            return
        if ntype == "parallel":
            for name in config.get("agents") or []:
                self._run_agent(str(name), state)
            return

    def _route(self, state: RunState, config: dict) -> None:
        if state.route:
            return
        goal = state.goal.lower()
        mapping = [
            (("eval", "metric", "judge", "error analysis"), "eval"),
            (("security", "auth", "vulnerability", "injection"), "security"),
            (("deploy", "observability", "latency", "production"), "ops"),
            (("rag", "retrieve", "grounding", "vector", "knowledge graph"), "grounding"),
            (("schema", "database", "migration", "etl"), "data"),
            (("train", "fine-tune", "bias", "variance"), "ml"),
            (("architecture", "microservice", "monolith", "tradeoff"), "architect"),
            (("frontend", "backend", "full-stack", "ui"), "fullstack"),
            (("spec", "mvp", "roadmap", "customer", "scope"), "spec"),
            (("review", "pull request", "diff"), "reviewer"),
            (("code", "implement", "refactor", "test", "bug", "function", "api"), "coding"),
            (("token", "context window", "tool calling", "sampling"), "llm"),
        ]
        for keys, route in mapping:
            if any(k in goal for k in keys):
                state.route = route
                break
        else:
            state.route = str(config.get("default") or "conductor")
        state.artifacts["route"] = state.route

    def _run_agent(self, name: str, state: RunState) -> None:
        agent = self.catalog.agents.get(name)
        if agent is None:
            raise KeyError(f"Unknown agent {name}. Available: {sorted(self.catalog.agents)}")
        # Isolation: coding agent gets a fresh active-skill copy and cannot inherit ops skills
        if agent.isolation in {"context", "process"}:
            state.active_agent = agent.name
            if agent.name == "coding":
                state.active_skills = [s for s in state.active_skills if s in agent.skills]
        else:
            state.active_agent = agent.name
        if agent.name == "spec":
            state.artifacts["has_spec"] = True
            state.artifacts.setdefault("spec", state.goal)
        self.loop.run(agent, state, LoopConfig(max_steps=agent.max_steps))

    def _spawn(self, name: str, state: RunState) -> str:
        if name not in self.catalog.agents:
            return f"unknown agent {name}"
        parent_agent = state.active_agent
        parent_skills = list(state.active_skills)
        child = RunState(
            thread_id=f"{state.thread_id}:{name}",
            goal=state.goal,
            current_node=state.current_node,
            artifacts=dict(state.artifacts),
        )
        self._run_agent(name, child)
        state.artifacts.setdefault("child_outputs", {})
        state.artifacts["child_outputs"][name] = (child.artifacts.get("outputs") or {}).get(name)
        state.trace.extend(child.trace)
        state.active_agent = parent_agent
        state.active_skills = parent_skills
        return f"spawned {name}"

    def _merge_evolved_skills(self) -> None:
        for skill in load_evolved_skills(self.evolved_dir):
            self.catalog.skills[skill.name] = skill


def _final_output(state: RunState) -> str:
    outputs = state.artifacts.get("outputs") or {}
    if outputs:
        parts = [f"[{k}] {v}" for k, v in outputs.items()]
        return "\n".join(parts)
    if state.artifacts.get("memory_hits"):
        return "Recalled prior lessons:\n" + "\n".join(state.artifacts["memory_hits"])
    return f"status={state.status} route={state.route}"
