from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.boundary import BoundaryError, resolve_in_project
from harness.catalog import Catalog
from harness.gates import infer_gates
from harness.runtime import Runtime

ROOT = Path(__file__).resolve().parents[1]


class GateTests(unittest.TestCase):
    def test_default_read_only(self) -> None:
        g = infer_gates("How does auth work in this project?")
        self.assertFalse(g.write)
        self.assertFalse(g.delete)
        self.assertFalse(g.commit)

    def test_implement_is_write_not_commit(self) -> None:
        g = infer_gates("implement a reverse helper")
        self.assertTrue(g.write)
        self.assertFalse(g.commit)
        self.assertFalse(g.delete)

    def test_commit_is_separate(self) -> None:
        g = infer_gates("implement the fix and commit")
        self.assertTrue(g.write)
        self.assertTrue(g.commit)


class CatalogTests(unittest.TestCase):
    def test_loads_pack(self) -> None:
        cat = Catalog(ROOT / ".agents")
        self.assertIn("forge", cat.bots)
        self.assertIn("atlas", cat.bots)
        self.assertGreaterEqual(len(cat.bots), 14)
        self.assertIn("read-only-default", cat.skills)
        self.assertNotIn("prod_db", cat.bots["forge"].tools_write)
        self.assertIn("prod_db", cat.bots["forge"].never)


class BoundaryTests(unittest.TestCase):
    def test_escape_and_env_denied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok.txt").write_text("x")
            resolve_in_project(root, "ok.txt")
            with self.assertRaises(BoundaryError):
                resolve_in_project(root, "../secret")
            (root / ".env").write_text("K=1")
            with self.assertRaises(BoundaryError):
                resolve_in_project(root, ".env")


class RuntimeTests(unittest.TestCase):
    def test_read_only_does_not_write(self) -> None:
        rt = Runtime(ROOT, Catalog(ROOT / ".agents"))
        result = rt.run("How is the roster structured?")
        self.assertFalse(result.gates.write)
        self.assertNotIn("files_write", result.tools)
        self.assertNotIn("git_commit", result.tools)

    def test_forge_implement_no_commit_tool(self) -> None:
        rt = Runtime(ROOT, Catalog(ROOT / ".agents"))
        result = rt.run("implement a helper function", bot="forge")
        self.assertTrue(result.gates.write)
        self.assertIn("files_write", result.tools)
        self.assertNotIn("git_commit", result.tools)
        self.assertFalse(any(t.get("name") == "files_write" for t in result.trace))


if __name__ == "__main__":
    unittest.main()
