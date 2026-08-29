from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_harness.catalog import Catalog, load_skill
from agent_harness.packs import export_agent_pack, import_pack, zip_pack


ROOT = Path(__file__).resolve().parents[1]


class PackTests(unittest.TestCase):
    def test_export_import_coding_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "coding-pack"
            export_agent_pack(ROOT / "agent_harness" / "catalog" / "agents" / "coding", dest)
            self.assertTrue((dest / "pack.json").is_file())
            manifest = json.loads((dest / "pack.json").read_text())
            self.assertEqual(manifest["name"], "coding")
            self.assertEqual(manifest["kind"], "agent")
            z = zip_pack(dest, Path(tmp) / "coding.zip")
            install_root = Path(tmp) / "installed"
            installed = import_pack(z, install_root)
            self.assertIn("agent", installed)
            cat = Catalog(roots=[install_root], project_root=Path(tmp))
            self.assertIn("coding", cat.agents)
            self.assertEqual(cat.agents["coding"].isolation, "context")


class MemoryEvolutionShapeTests(unittest.TestCase):
    def test_evolved_skill_is_valid_skill_md(self) -> None:
        from agent_harness.evolution import _draft_skill, _safe_skill_name
        from agent_harness.persistence import Episode
        from agent_harness.types import RunState

        name = _safe_skill_name("coding")
        self.assertEqual(name, "evolved-coding")
        state = RunState(thread_id="t", goal="implement parser", current_node="done")
        state.active_agent = "coding"
        state.route = "coding"
        state.active_skills = ["verifier-first-coding"]
        body = _draft_skill(
            name,
            state,
            [
                Episode(
                    id=1,
                    thread_id="t",
                    goal="implement parser",
                    agent="coding",
                    outcome="succeeded",
                    trace=[],
                    created_at=0,
                )
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / name / "SKILL.md"
            path.parent.mkdir()
            path.write_text(body, encoding="utf-8")
            skill = load_skill(path)
            self.assertEqual(skill.name, name)
            self.assertIn("implement parser", skill.description)


if __name__ == "__main__":
    unittest.main()
