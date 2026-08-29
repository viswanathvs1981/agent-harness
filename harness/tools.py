"""File and git tools. Callers pass only the gated allowlist."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .boundary import BoundaryError, resolve_in_project
from .types import RunState

ToolFn = Callable[[dict[str, Any], RunState], str]


def builtin_tools(project: Path) -> dict[str, ToolFn]:
    def files_read(args: dict[str, Any], state: RunState) -> str:
        rel = str(args.get("path") or "")
        path = resolve_in_project(project, rel)
        if path.is_dir():
            names = sorted(p.name for p in path.iterdir())[:80]
            return "\n".join(names) or "(empty)"
        if not path.is_file():
            return f"missing {rel}"
        return path.read_text(encoding="utf-8")[:8000]

    def files_write(args: dict[str, Any], state: RunState) -> str:
        rel = str(args.get("path") or "")
        path = resolve_in_project(project, rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(args.get("content") or ""), encoding="utf-8")
        state.artifacts.setdefault("written", []).append(rel)
        return f"wrote {rel}"

    def files_delete(args: dict[str, Any], state: RunState) -> str:
        rel = str(args.get("path") or "")
        path = resolve_in_project(project, rel)
        if not path.exists():
            return f"missing {rel}"
        if path.is_dir():
            raise BoundaryError("refusing to delete a directory")
        path.unlink()
        state.artifacts.setdefault("deleted", []).append(rel)
        return f"deleted {rel}"

    def git_status(args: dict[str, Any], state: RunState) -> str:
        return "git repo" if (project / ".git").exists() else "not a git repo"

    def git_commit(args: dict[str, Any], state: RunState) -> str:
        msg = str(args.get("message") or "").strip()
        if not msg:
            return "commit blocked: empty message"
        state.artifacts.setdefault("proposed_commits", []).append(msg)
        return f"queued commit (not executed): {msg}"

    def record_eval(args: dict[str, Any], state: RunState) -> str:
        name = str(args.get("name") or "task")
        score = float(args.get("score") or 0)
        state.eval_scores[name] = score
        return f"{name}={score}"

    return {
        "files_read": files_read,
        "search": files_read,
        "files_write": files_write,
        "files_delete": files_delete,
        "git_status": git_status,
        "git_commit": git_commit,
        "record_eval": record_eval,
    }
