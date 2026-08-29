from __future__ import annotations

import unittest
from pathlib import Path

from agent_harness.yaml_frontmatter import split_frontmatter

ROOT = Path(__file__).resolve().parents[1] / "design" / "bots"
REQUIRED = ("name", "slug", "title", "description")


class BotRosterTests(unittest.TestCase):
    def test_each_bot_has_grok_style_profile(self) -> None:
        bots = sorted(p for p in ROOT.iterdir() if p.is_dir())
        slugs = []
        self.assertGreaterEqual(len(bots), 14)
        for folder in bots:
            path = folder / "BOT.md"
            self.assertTrue(path.is_file(), folder.name)
            meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
            for key in REQUIRED:
                self.assertTrue(meta.get(key), f"{folder.name} missing {key}")
            self.assertEqual(meta["slug"], folder.name)
            slugs.append(meta["slug"])
            self.assertTrue(body.strip())
        self.assertIn("forge", slugs)
        self.assertIn("atlas", slugs)

    def test_forge_is_fenced_from_prod(self) -> None:
        meta, _ = split_frontmatter((ROOT / "forge" / "BOT.md").read_text(encoding="utf-8"))
        policy = meta.get("tool_policy") or []
        self.assertNotIn("deploy", policy)
        self.assertNotIn("prod_db", policy)
        self.assertEqual(meta["approval"], "never-prod-db-or-deploy")
