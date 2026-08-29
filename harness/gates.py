"""Turn-level permission gates. Default is read-only."""

from __future__ import annotations

import re
from dataclasses import dataclass

WRITE_RE = re.compile(
    r"\b(implement|apply|write|fix|refactor|patch|edit|create|add file|go ahead|make the change)\b",
    re.I,
)
DELETE_RE = re.compile(r"\b(delete|remove)\b", re.I)
COMMIT_RE = re.compile(r"\b(commit|push)\b", re.I)
INSTALL_RE = re.compile(r"\b(install the bots|drop this skill|install agents)\b", re.I)


@dataclass(frozen=True)
class Gates:
    write: bool = False
    delete: bool = False
    commit: bool = False
    install: bool = False

    def tools(self, bot_read: tuple[str, ...], bot_write: tuple[str, ...],
              bot_delete: tuple[str, ...], bot_commit: tuple[str, ...]) -> tuple[str, ...]:
        allowed = list(bot_read)
        if self.write:
            allowed.extend(bot_write)
        if self.delete:
            allowed.extend(bot_delete)
        if self.commit:
            allowed.extend(bot_commit)
        return tuple(dict.fromkeys(allowed))


def infer_gates(message: str) -> Gates:
    return Gates(
        write=bool(WRITE_RE.search(message)),
        delete=bool(DELETE_RE.search(message)),
        commit=bool(COMMIT_RE.search(message)),
        install=bool(INSTALL_RE.search(message)),
    )
