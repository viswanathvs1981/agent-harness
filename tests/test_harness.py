from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agent_harness.catalog import Catalog
from agent_harness.harness import Harness
from agent_harness.llm import HeuristicLLM
from agent_harness.loop import AgentLoop
from agent_harness.persistence import Store
from agent_harness.tools import builtin_tools
from agent_harness.types import Action, AgentSpec, RunState


BUNDLED = Path(__file__).resolve().parents[1] / "agent_harness" / "catalog"


def _harness(root: Path) -> Harness:
    return Harness(
        project_root=root,
        data_dir=root / "state",
        llm=HeuristicLLM(),
        catalog=Catalog(roots=[BUNDLED], project_root=root),
    )


class IsolationTests(unittest.TestCase):
    def test_coding_cannot_call_unknown_prod_tool(self) -> None:
        llm = HeuristicLLM(
            script=[
                Action(kind="tool", name="prod_db", args={"sql": "drop table users"}),
                Action(kind="finish", content="stopped"),
            ]
        )
        agent = AgentSpec(
            name="coding",
            description="coder",
            body="isolated",
            path=Path("."),
            tools=("files", "shell", "git"),
            skills=(),
            isolation="context",
        )
        state = RunState(thread_id="t", goal="hack prod", current_node="code")
        loop = AgentLoop(llm, builtin_tools(Path(".")), skills={})
        loop.run(agent, state)
        joined = str(state.trace)
        self.assertIn("not permitted", joined + str(state.messages))


class PersistenceTests(unittest.TestCase):
    def test_checkpoint_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "h.db")
            state = RunState(thread_id="abc", goal="g", current_node="route", step=3)
            state.artifacts["has_spec"] = True
            store.save_checkpoint(state)
            loaded = store.load_latest("abc")
            assert loaded is not None
            self.assertEqual(loaded.step, 3)
            self.assertTrue(loaded.artifacts["has_spec"])
            store.close()


class HarnessRunTests(unittest.TestCase):
    def test_end_to_end_coding_goal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            h = _harness(root)
            result = h.run("implement a function to reverse a string")
            h.close()
            self.assertEqual(result.status, "succeeded")
            self.assertEqual(result.state.route, "coding")
            self.assertGreaterEqual(result.eval_scores.get("task", 0), 0.7)
            self.assertTrue(result.state.artifacts.get("has_spec"))

    def test_resume_thread(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            h = _harness(root)
            first = h.run("architecture tradeoffs for a notes app")
            resumed = h.run(
                "architecture tradeoffs for a notes app",
                thread_id=first.thread_id,
                resume=True,
            )
            h.close()
            self.assertEqual(resumed.thread_id, first.thread_id)
            self.assertGreaterEqual(resumed.state.step, first.state.step)

    def test_evolution_promotes_after_repeated_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            h = _harness(root)
            h.run("implement a function to parse csv rows")
            second = h.run("implement a function to parse csv rows")
            evolved = list((root / "state" / "evolved-skills").glob("*/SKILL.md"))
            h.close()
            self.assertTrue(second.promoted_skills or evolved)


if __name__ == "__main__":
    unittest.main()
