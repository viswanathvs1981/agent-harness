"""Load droppable bots and skills from .agents/."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .yaml_frontmatter import as_str_tuple, split_frontmatter

FORBIDDEN = ("andrew ng", "deeplearning", "ng_skill", "grok", "cursor")


class CatalogError(ValueError):
    pass


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str
    path: Path

    def catalog_entry(self) -> dict[str, str]:
        return {"name": self.name, "description": self.description}


@dataclass(frozen=True)
class Bot:
    name: str
    title: str
    description: str
    body: str
    path: Path
    tools_read: tuple[str, ...]
    tools_write: tuple[str, ...]
    tools_delete: tuple[str, ...]
    tools_commit: tuple[str, ...]
    never: tuple[str, ...]
    skills: tuple[str, ...]


class Catalog:
    def __init__(self, agents_root: Path):
        self.root = agents_root
        self.bots: dict[str, Bot] = {}
        self.skills: dict[str, Skill] = {}
        self.reload()

    def reload(self) -> None:
        self.bots.clear()
        self.skills.clear()
        for path in _named(self.root / "skills", "SKILL.md"):
            skill = load_skill(path)
            self.skills[skill.name] = skill
        for path in _named(self.root / "bots", "BOT.md"):
            bot = load_bot(path)
            self.bots[bot.name] = bot


def _named(folder: Path, filename: str) -> list[Path]:
    if not folder.is_dir():
        return []
    found = []
    for child in sorted(folder.iterdir()):
        candidate = child / filename
        if child.is_dir() and candidate.is_file():
            found.append(candidate)
    return found


def _assert_clean(text: str, path: Path) -> None:
    low = text.lower()
    for token in FORBIDDEN:
        if token in low:
            raise CatalogError(f"{path}: forbidden token {token!r}")


def load_skill(path: Path) -> Skill:
    text = path.read_text(encoding="utf-8")
    _assert_clean(text, path)
    meta, body = split_frontmatter(text)
    name = str(meta.get("name") or path.parent.name)
    if name != path.parent.name:
        raise CatalogError(f"{path}: name must match directory")
    description = str(meta.get("description") or "").strip()
    if not description:
        raise CatalogError(f"{path}: description required")
    return Skill(name=name, description=description, body=body, path=path)


def load_bot(path: Path) -> Bot:
    text = path.read_text(encoding="utf-8")
    _assert_clean(text, path)
    meta, body = split_frontmatter(text)
    name = str(meta.get("name") or path.parent.name)
    if name != path.parent.name:
        raise CatalogError(f"{path}: name must match directory")
    return Bot(
        name=name,
        title=str(meta.get("title") or name),
        description=str(meta.get("description") or "").strip(),
        body=body,
        path=path,
        tools_read=as_str_tuple(meta.get("tools_read")),
        tools_write=as_str_tuple(meta.get("tools_write")),
        tools_delete=as_str_tuple(meta.get("tools_delete")),
        tools_commit=as_str_tuple(meta.get("tools_commit")),
        never=as_str_tuple(meta.get("never")),
        skills=as_str_tuple(meta.get("skills")),
    )
