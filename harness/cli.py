"""CLI: bots run | bots list | bots install-check."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .catalog import Catalog
from .runtime import Runtime


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bots", description="Droppable bot harness (read-only by default).")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("goal")
    run.add_argument("--bot", default=None)
    run.add_argument("--root", type=Path, default=Path.cwd())
    sub.add_parser("list")
    args = parser.parse_args(argv)
    root = (args.root if hasattr(args, "root") else Path.cwd()).resolve()
    catalog = Catalog(root / ".agents")
    if args.cmd == "list":
        for b in catalog.bots.values():
            print(f"{b.name:12} {b.title:24} read={list(b.tools_read)}")
        for s in catalog.skills.values():
            print(f"  skill {s.name}: {s.description[:70]}")
        return 0
    rt = Runtime(root, catalog)
    result = rt.run(args.goal, bot=args.bot)
    print(json.dumps(
        {
            "status": result.status,
            "bot": result.bot,
            "write": result.gates.write,
            "delete": result.gates.delete,
            "commit": result.gates.commit,
            "tools": list(result.tools),
            "eval": result.eval_scores,
            "output": result.output,
        },
        indent=2,
    ))
    return 0 if result.status == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
