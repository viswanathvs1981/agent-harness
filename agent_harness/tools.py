"""Harness tools. Agents only see the names listed in their AGENT.md."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .types import RunState


class ToolError(RuntimeError):
    pass


def builtin_tools(workspace: Path) -> dict:
    workspace = workspace.resolve()

    def files(args: dict[str, Any], state: RunState) -> str:
        op = str(args.get("op") or "read")
        rel = str(args.get("path") or "")
        if op == "note":
            notes = state.artifacts.setdefault("notes", [])
            notes.append(args.get("content") or "")
            return "noted"
        path = _safe(workspace, rel)
        if op == "read":
            if not path.is_file():
                return f"missing {rel}"
            return path.read_text(encoding="utf-8")[:8000]
        if op == "write":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(args.get("content") or ""), encoding="utf-8")
            written = state.artifacts.setdefault("written", [])
            written.append(rel)
            return f"wrote {rel}"
        if op == "list":
            target = path if rel else workspace
            if not target.exists():
                return "missing"
            names = sorted(p.name for p in target.iterdir())[:80]
            return "\n".join(names)
        return f"unknown files op {op}"

    def memory_search(args: dict[str, Any], state: RunState) -> str:
        hits = state.artifacts.get("memory_hits") or []
        q = str(args.get("query") or state.goal)
        return f"query={q} hits={hits}"

    def record_eval(args: dict[str, Any], state: RunState) -> str:
        name = str(args.get("name") or "task")
        score = float(args.get("score") or 0)
        state.eval_scores[name] = score
        return f"{name}={score}"

    def shell(args: dict[str, Any], state: RunState) -> str:
        # Intentionally not executing arbitrary commands in the default harness.
        # Coding agents should use verifiers (tests) via the eval node, not raw shell.
        cmd = str(args.get("cmd") or "")
        blocked = ("rm -rf", "drop table", "shutdown", "mkfs", "sudo")
        if any(b in cmd.lower() for b in blocked):
            raise ToolError(f"blocked command: {cmd}")
        notes = state.artifacts.setdefault("proposed_commands", [])
        notes.append(cmd)
        return f"queued (not executed): {cmd}"

    def git_status(args: dict[str, Any], state: RunState) -> str:
        git = workspace / ".git"
        return "git repo" if git.exists() else "not a git repo"

    return {
        "files": files,
        "memory": memory_search,
        "record_eval": record_eval,
        "shell": shell,
        "git": git_status,
    }


def _safe(root: Path, rel: str) -> Path:
    if not rel:
        return root
    candidate = (root / rel).resolve()
    if root not in candidate.parents and candidate != root:
        raise ToolError(f"path escapes workspace: {rel}")
    return candidate
