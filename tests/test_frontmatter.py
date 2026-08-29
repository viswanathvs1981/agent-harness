from __future__ import annotations

import unittest
from pathlib import Path

from agent_harness.yaml_frontmatter import as_str_list, parse_simple_yaml, split_frontmatter


class FrontmatterTests(unittest.TestCase):
    def test_skill_frontmatter(self) -> None:
        text = """---
name: eval-driven-development
description: Design evals. Use when measuring quality.
license: Apache-2.0
metadata:
  version: "0.1.0"
  ng_skill: evaluation-driven-development
allowed-tools: files git
---

# Body

Hello.
"""
        meta, body = split_frontmatter(text)
        self.assertEqual(meta["name"], "eval-driven-development")
        self.assertEqual(meta["metadata"]["ng_skill"], "evaluation-driven-development")
        self.assertEqual(as_str_list(meta["allowed-tools"]), ("files", "git"))
        self.assertIn("# Body", body)

    def test_lists_and_bools(self) -> None:
        data = parse_simple_yaml(
            """
tools:
  - files
  - shell
sandbox: true
empty: []
""".strip()
        )
        self.assertEqual(data["tools"], ["files", "shell"])
        self.assertTrue(data["sandbox"])
        self.assertEqual(data["empty"], [])


if __name__ == "__main__":
    unittest.main()
