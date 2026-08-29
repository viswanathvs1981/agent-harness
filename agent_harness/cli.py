"""Command line: harness run | agents | skills | pack | eval | evolve."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .catalog import Catalog
from .graph import summarize_graph, validate_graph
from .harness import Harness
from .packs import export_agent_pack, import_pack, zip_pack


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="harness",
        description="Generic AI engineering harness (graph + loop + skills + evolution).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Run a goal through the graph")
    run.add_argument("goal")
    run.add_argument("--agent", default=None)
    run.add_argument("--graph", default="default")
    run.add_argument("--thread", default=None)
    run.add_argument("--resume", action="store_true")
    run.add_argument("--root", type=Path, default=None)

    sub.add_parser("agents", help="List droppable agents")
    sub.add_parser("skills", help="List Agent Skills (SKILL.md)")
    g = sub.add_parser("graph", help="Show a graph")
    g.add_argument("name", nargs="?", default="default")

    p = sub.add_parser("pack", help="Export or import a shareable pack")
    p.add_argument("action", choices=["export", "import"])
    p.add_argument("path")
    p.add_argument("--dest", default=None)
    p.add_argument("--zip", action="store_true")

    sub.add_parser("evolve", help="Show evolved skills and lessons")
    sub.add_parser("eval", help="Describe the default eval suite")

    args = parser.parse_args(argv)
    root = Path(args.root) if getattr(args, "root", None) else Path.cwd()

    if args.cmd == "run":
        h = Harness(project_root=root)
        try:
            result = h.run(
                args.goal,
                agent=args.agent,
                graph=args.graph,
                thread_id=args.thread,
                resume=args.resume,
            )
        finally:
            h.close()
        print(json.dumps(
            {
                "thread_id": result.thread_id,
                "status": result.status,
                "route": result.state.route,
                "eval_scores": result.eval_scores,
                "promoted_skills": result.promoted_skills,
                "output": result.output,
                "trace_steps": len(result.state.trace),
            },
            indent=2,
        ))
        return 0 if result.status == "succeeded" else 1

    catalog = Catalog(project_root=root)
    if args.cmd == "agents":
        for a in catalog.agent_index():
            print(f"{a['name']:12} {a['role']:14} isolation={a['isolation']:8} {a['description'][:90]}")
        return 0
    if args.cmd == "skills":
        for s in catalog.skill_index():
            print(f"{s['name']:28} {s['description'][:90]}")
        return 0
    if args.cmd == "graph":
        spec = catalog.graphs[args.name]
        errors = validate_graph(spec)
        print(json.dumps({"errors": errors, **summarize_graph(spec)}, indent=2))
        return 0 if not errors else 1
    if args.cmd == "pack":
        src = Path(args.path)
        dest = Path(args.dest) if args.dest else Path("dist") / src.name
        if args.action == "export":
            exported = export_agent_pack(src, dest)
            print(f"exported pack to {exported}")
            if args.zip:
                z = zip_pack(exported, exported.with_suffix(".zip"))
                print(f"zipped {z}")
            return 0
        installed = import_pack(src, dest)
        print(json.dumps({k: str(v) for k, v in installed.items()}, indent=2))
        return 0
    if args.cmd == "evolve":
        h = Harness(project_root=root)
        try:
            lessons = h.memory.lessons()
            print(f"lessons={len(lessons)} evolved_dir={h.evolved_dir}")
            for n in lessons[:20]:
                print(f"  {n.label} u={n.usefulness:.2f}")
        finally:
            h.close()
        return 0
    if args.cmd == "eval":
        from .evals import default_suite

        suite = default_suite()
        print(suite.name)
        for c in suite.cases:
            print(f"  {c.name:20} {c.kind}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
