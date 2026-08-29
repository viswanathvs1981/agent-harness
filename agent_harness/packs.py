"""Droppable packs: zip/directory bundles anyone can share.

A pack is the unit of distribution. It can contain an agent, skills, and a
graph. Skills stay Agent Skills compatible (SKILL.md). Agents are AGENT.md.
The pack.json manifest is ours — small enough to copy by hand.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .catalog import load_agent, load_skill


PACK_FILENAME = "pack.json"


@dataclass
class PackManifest:
    name: str
    version: str
    kind: str  # agent | skills | graph | mix
    description: str = ""
    license: str = "Apache-2.0"
    exports: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "kind": self.kind,
            "description": self.description,
            "license": self.license,
            "exports": self.exports or {},
        }


def read_manifest(pack_dir: Path) -> PackManifest:
    data = json.loads((pack_dir / PACK_FILENAME).read_text(encoding="utf-8"))
    return PackManifest(
        name=data["name"],
        version=str(data.get("version") or "0.0.0"),
        kind=str(data.get("kind") or "mix"),
        description=str(data.get("description") or ""),
        license=str(data.get("license") or "Apache-2.0"),
        exports=dict(data.get("exports") or {}),
    )


def export_agent_pack(agent_dir: Path, dest: Path) -> Path:
    agent = load_agent(agent_dir / "AGENT.md")
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(agent_dir / "AGENT.md", dest / "AGENT.md")
    skills_src = agent_dir / "skills"
    exported_skills = []
    if skills_src.is_dir():
        shutil.copytree(skills_src, dest / "skills", dirs_exist_ok=True)
        exported_skills = [p.name for p in (dest / "skills").iterdir() if p.is_dir()]
    graph = agent_dir / "graph.json"
    exports: dict[str, Any] = {"agent": "AGENT.md", "skills": exported_skills}
    if graph.is_file():
        shutil.copy2(graph, dest / "graph.json")
        exports["graph"] = "graph.json"
    manifest = PackManifest(
        name=agent.name,
        version=agent.metadata.get("version", "0.1.0"),
        kind="agent",
        description=agent.description,
        exports=exports,
    )
    (dest / PACK_FILENAME).write_text(json.dumps(manifest.to_json(), indent=2) + "\n", encoding="utf-8")
    return dest


def zip_pack(pack_dir: Path, zip_path: Path) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in pack_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(pack_dir))
    return zip_path


def import_pack(src: Path, dest_root: Path) -> dict[str, Path]:
    """Install a pack directory or zip into dest_root/{agents,skills,graphs}."""
    tmp = None
    pack_dir = src
    if src.is_file() and src.suffix == ".zip":
        tmp = dest_root / ".import-tmp" / src.stem
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        with zipfile.ZipFile(src) as zf:
            zf.extractall(tmp)
        pack_dir = tmp
    manifest = read_manifest(pack_dir)
    installed: dict[str, Path] = {}
    agent_md = pack_dir / "AGENT.md"
    if agent_md.is_file():
        agent = load_agent(agent_md)
        target = dest_root / "agents" / agent.name
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(agent_md, target / "AGENT.md")
        installed["agent"] = target
    skills_dir = pack_dir / "skills"
    if skills_dir.is_dir():
        for child in skills_dir.iterdir():
            skill_md = child / "SKILL.md" if child.is_dir() else None
            if skill_md and skill_md.is_file():
                skill = load_skill(skill_md)
                target = dest_root / "skills" / skill.name
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(child, target)
                installed[f"skill:{skill.name}"] = target
    graph = pack_dir / "graph.json"
    if graph.is_file():
        graphs = dest_root / "graphs"
        graphs.mkdir(parents=True, exist_ok=True)
        target = graphs / f"{manifest.name}.json"
        shutil.copy2(graph, target)
        installed["graph"] = target
    if tmp and tmp.exists():
        shutil.rmtree(tmp.parent)
    return installed
