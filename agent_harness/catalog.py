"""Load droppable agents, skills, and graphs from disk.

Discovery order (later overrides earlier):
1. Bundled catalog shipped inside this package
2. `$HARNESS_HOME` (default `~/.harness`)
3. Project `.harness/` and vendor-neutral `.agents/`
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterable

from .types import AgentSpec, GraphEdge, GraphNode, GraphSpec, NodeType, Skill
from .yaml_frontmatter import as_str_list, as_str_map, split_frontmatter

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class CatalogError(ValueError):
    pass


def default_catalog_roots(project_root: Path | None = None) -> list[Path]:
    roots: list[Path] = []
    bundled = Path(__file__).resolve().parent / "catalog"
    if bundled.is_dir():
        roots.append(bundled)
    home = Path(os.environ.get("HARNESS_HOME", Path.home() / ".harness"))
    if home.is_dir():
        roots.append(home)
    if project_root is None:
        project_root = Path.cwd()
    for rel in (".harness", ".agents"):
        candidate = project_root / rel
        if candidate.is_dir():
            roots.append(candidate)
    return roots


class Catalog:
    def __init__(self, roots: Iterable[Path] | None = None, project_root: Path | None = None):
        self.roots = list(roots) if roots is not None else default_catalog_roots(project_root)
        self.skills: dict[str, Skill] = {}
        self.agents: dict[str, AgentSpec] = {}
        self.graphs: dict[str, GraphSpec] = {}
        self.reload()

    def reload(self) -> None:
        self.skills.clear()
        self.agents.clear()
        self.graphs.clear()
        for root in self.roots:
            self._load_root(root)

    def skill_index(self) -> list[dict[str, str]]:
        return [s.catalog_entry() for s in self.skills.values()]

    def agent_index(self) -> list[dict]:
        return [a.catalog_entry() for a in self.agents.values()]

    def _load_root(self, root: Path) -> None:
        for skill_md in _iter_named(root, "skills", "SKILL.md"):
            skill = load_skill(skill_md)
            self.skills[skill.name] = skill
        for agent_md in _iter_named(root, "agents", "AGENT.md"):
            agent = load_agent(agent_md)
            self.agents[agent.name] = agent
        graphs_dir = root / "graphs"
        if graphs_dir.is_dir():
            for path in sorted(graphs_dir.glob("*.json")):
                graph = load_graph(path)
                self.graphs[graph.id] = graph


def _iter_named(root: Path, folder: str, filename: str) -> list[Path]:
    base = root / folder
    if not base.is_dir():
        return []
    found: list[Path] = []
    for child in sorted(base.iterdir()):
        candidate = child / filename if child.is_dir() else None
        if candidate and candidate.is_file():
            found.append(candidate)
    return found


def load_skill(path: Path) -> Skill:
    text = path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(text)
    name = str(meta.get("name") or path.parent.name)
    description = str(meta.get("description") or "").strip()
    validate_skill_name(name, path.parent.name)
    if not description:
        raise CatalogError(f"{path}: description is required")
    if len(description) > 1024:
        raise CatalogError(f"{path}: description exceeds 1024 characters")
    return Skill(
        name=name,
        description=description,
        body=body,
        path=path,
        license=str(meta["license"]) if meta.get("license") else None,
        compatibility=str(meta["compatibility"]) if meta.get("compatibility") else None,
        metadata=as_str_map(meta.get("metadata")),
        allowed_tools=as_str_list(meta.get("allowed-tools") or meta.get("allowed_tools")),
    )


def load_agent(path: Path) -> AgentSpec:
    text = path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(text)
    name = str(meta.get("name") or path.parent.name)
    description = str(meta.get("description") or "").strip()
    if not description:
        raise CatalogError(f"{path}: description is required")
    isolation = str(meta.get("isolation") or "context")
    if isolation not in ("none", "context", "process"):
        raise CatalogError(f"{path}: invalid isolation {isolation}")
    return AgentSpec(
        name=name,
        description=description,
        body=body,
        path=path,
        role=str(meta.get("role") or "specialist"),
        isolation=isolation,  # type: ignore[arg-type]
        sandbox=bool(meta.get("sandbox", True)),
        tools=as_str_list(meta.get("tools")),
        skills=as_str_list(meta.get("skills")),
        model=str(meta.get("model") or "inherit"),
        max_steps=int(meta.get("max_steps") or 16),
        graph=str(meta["graph"]) if meta.get("graph") else None,
        metadata=as_str_map(meta.get("metadata")),
    )


def load_graph(path: Path) -> GraphSpec:
    data = json.loads(path.read_text(encoding="utf-8"))
    nodes = {
        n["id"]: GraphNode(id=n["id"], type=_node_type(n["type"]), config=dict(n.get("config") or {}))
        for n in data["nodes"]
    }
    edges = [
        GraphEdge(
            source=e["from"],
            target=e["to"],
            when=e.get("when"),
            kind=e.get("kind", "normal"),
        )
        for e in data.get("edges", [])
    ]
    return GraphSpec(
        id=str(data.get("id") or path.stem),
        entry=str(data["entry"]),
        nodes=nodes,
        edges=edges,
        description=str(data.get("description") or ""),
    )


def _node_type(value: str) -> NodeType:
    allowed = {
        "router",
        "agent",
        "skill",
        "loop",
        "eval",
        "tool",
        "parallel",
        "human",
        "evolve",
        "end",
    }
    if value not in allowed:
        raise CatalogError(f"Unknown node type: {value}")
    return value  # type: ignore[return-value]


def validate_skill_name(name: str, directory: str) -> None:
    if not SKILL_NAME_RE.fullmatch(name):
        raise CatalogError(
            f"Invalid skill name {name!r}: use lowercase letters, numbers, single hyphens"
        )
    if name != directory:
        raise CatalogError(f"Skill name {name!r} must match directory {directory!r}")
    if len(name) > 64:
        raise CatalogError(f"Skill name {name!r} exceeds 64 characters")
