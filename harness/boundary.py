"""Project-root sandbox. Fail closed."""

from __future__ import annotations

from pathlib import Path

DENIED_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
}
DENIED_SUFFIXES = {".pem", ".p12", ".key"}
DENIED_PARTS = {".git/credentials", ".ssh"}


class BoundaryError(PermissionError):
    pass


def resolve_in_project(root: Path, rel: str) -> Path:
    root = root.resolve()
    if not rel or rel.strip() in {".", "./"}:
        return root
    candidate = (root / rel).resolve()
    if candidate != root and root not in candidate.parents:
        raise BoundaryError(f"path escapes project: {rel}")
    rel_posix = candidate.relative_to(root).as_posix()
    name = candidate.name
    if name in DENIED_NAMES or any(name.endswith(s) for s in DENIED_SUFFIXES):
        raise BoundaryError(f"denied file: {rel}")
    if any(part in rel_posix for part in DENIED_PARTS):
        raise BoundaryError(f"denied path: {rel}")
    return candidate
