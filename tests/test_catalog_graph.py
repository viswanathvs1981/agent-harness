from __future__ import annotations

import unittest
from pathlib import Path

from agent_harness.catalog import Catalog, validate_skill_name
from agent_harness.graph import GraphRuntime, default_predicates, validate_graph
from agent_harness.types import RunState


ROOT = Path(__file__).resolve().parents[1]


class CatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = Catalog(roots=[ROOT / "agent_harness" / "catalog"], project_root=ROOT)

    def test_loads_agents_and_skills(self) -> None:
        self.assertIn("coding", self.catalog.agents)
        self.assertIn("conductor", self.catalog.agents)
        self.assertGreaterEqual(len(self.catalog.agents), 12)
        self.assertIn("eval-driven-development", self.catalog.skills)
        self.assertGreaterEqual(len(self.catalog.skills), 12)

    def test_progressive_disclosure(self) -> None:
        skill = self.catalog.skills["verifier-first-coding"]
        entry = skill.catalog_entry()
        self.assertEqual(set(entry), {"name", "description"})
        self.assertNotIn("Write or update", entry["description"])
        self.assertIn("fail for the right reason", skill.body)

    def test_coding_agent_is_isolated(self) -> None:
        coding = self.catalog.agents["coding"]
        self.assertEqual(coding.isolation, "context")
        self.assertTrue(coding.sandbox)
        self.assertNotIn("deploy", coding.tools)
        self.assertIn("files", coding.tools)
        ops = self.catalog.agents["ops"]
        self.assertNotEqual(set(coding.tools), set(ops.skills))

    def test_skill_name_rules(self) -> None:
        with self.assertRaises(Exception):
            validate_skill_name("PDF-Processing", "PDF-Processing")
        validate_skill_name("code-review", "code-review")

    def test_graphs_valid(self) -> None:
        for spec in self.catalog.graphs.values():
            self.assertEqual(validate_graph(spec), [])


class GraphLoopTests(unittest.TestCase):
    def test_eval_retry_then_give_up(self) -> None:
        catalog = Catalog(roots=[ROOT / "agent_harness" / "catalog"], project_root=ROOT)
        spec = catalog.graphs["default"]
        runtime = GraphRuntime(spec, default_predicates())
        state = RunState(thread_id="t", goal="x", current_node="eval")
        state.eval_scores = {"task": 0.2}
        state.artifacts["eval_attempts"] = 1
        self.assertEqual(runtime.next_node(state), "work")
        state.artifacts["eval_attempts"] = 3
        self.assertEqual(runtime.next_node(state), "evolve")

    def test_pass_goes_to_review(self) -> None:
        catalog = Catalog(roots=[ROOT / "agent_harness" / "catalog"], project_root=ROOT)
        runtime = GraphRuntime(catalog.graphs["default"], default_predicates())
        state = RunState(thread_id="t", goal="x", current_node="eval")
        state.eval_scores = {"task": 0.95}
        self.assertEqual(runtime.next_node(state), "review")


if __name__ == "__main__":
    unittest.main()
