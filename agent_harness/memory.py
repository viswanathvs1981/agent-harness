"""Knowledge-graph memory for self-evolution.

Grounding is not only RAG. Ng's map lists vector indexes, knowledge graphs,
and semantic layers. The harness memory is a typed graph:

  episode --distilled--> lesson --promoted--> skill
  agent   --used-->      skill  --failed_on--> pattern
  lesson  --caused_by--> pattern

Retrieval walks neighbors + keyword overlap. Embeddings can plug in later
without changing the schema. Lessons are pruned by usefulness, not dumped
append-only (ReMe / Metis: refine, don't hoard).
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    label TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    usefulness REAL NOT NULL DEFAULT 1.0,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS edges (
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    rel TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    payload_json TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);
CREATE INDEX IF NOT EXISTS idx_edges_rel ON edges(rel);
"""


@dataclass
class MemoryNode:
    id: str
    type: str
    label: str
    payload: dict[str, Any]
    usefulness: float = 1.0


@dataclass
class MemoryEdge:
    src: str
    dst: str
    rel: str
    weight: float = 1.0
    payload: dict[str, Any] | None = None


class MemoryGraph:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def upsert_node(
        self,
        type: str,
        label: str,
        payload: dict[str, Any] | None = None,
        node_id: str | None = None,
        usefulness: float = 1.0,
    ) -> str:
        existing = self.find_by_label(type, label)
        nid = existing.id if existing else (node_id or uuid.uuid4().hex)
        now = time.time()
        self._conn.execute(
            """
            INSERT INTO nodes(id, type, label, payload_json, usefulness, created_at)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                payload_json=excluded.payload_json,
                usefulness=excluded.usefulness
            """,
            (nid, type, label, json.dumps(payload or {}), usefulness, now),
        )
        self._conn.commit()
        return nid

    def add_edge(self, src: str, dst: str, rel: str, weight: float = 1.0, payload: dict | None = None) -> None:
        self._conn.execute(
            "INSERT INTO edges(src, dst, rel, weight, payload_json, created_at) VALUES (?,?,?,?,?,?)",
            (src, dst, rel, weight, json.dumps(payload or {}), time.time()),
        )
        self._conn.commit()

    def bump(self, node_id: str, delta: float) -> None:
        self._conn.execute(
            "UPDATE nodes SET usefulness = MAX(0.05, usefulness + ?) WHERE id=?",
            (delta, node_id),
        )
        self._conn.commit()

    def find_by_label(self, type: str, label: str) -> MemoryNode | None:
        row = self._conn.execute(
            "SELECT * FROM nodes WHERE type=? AND label=? LIMIT 1",
            (type, label),
        ).fetchone()
        return _row_node(row) if row else None

    def get(self, node_id: str) -> MemoryNode | None:
        row = self._conn.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
        return _row_node(row) if row else None

    def neighbors(self, node_id: str, rel: str | None = None) -> list[tuple[MemoryEdge, MemoryNode]]:
        sql = "SELECT e.*, n.id AS nid, n.type, n.label, n.payload_json, n.usefulness FROM edges e JOIN nodes n ON n.id=e.dst WHERE e.src=?"
        args: list[Any] = [node_id]
        if rel:
            sql += " AND e.rel=?"
            args.append(rel)
        rows = self._conn.execute(sql, args).fetchall()
        out = []
        for r in rows:
            edge = MemoryEdge(src=r["src"], dst=r["dst"], rel=r["rel"], weight=r["weight"], payload=json.loads(r["payload_json"]))
            node = MemoryNode(
                id=r["nid"],
                type=r["type"],
                label=r["label"],
                payload=json.loads(r["payload_json"]),
                usefulness=r["usefulness"],
            )
            out.append((edge, node))
        return out

    def retrieve(self, query: str, types: Iterable[str] | None = None, k: int = 6) -> list[MemoryNode]:
        tokens = set(_tokens(query))
        type_filter = tuple(types) if types else None
        if type_filter:
            placeholders = ",".join("?" * len(type_filter))
            rows = self._conn.execute(
                f"SELECT * FROM nodes WHERE type IN ({placeholders})",
                type_filter,
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM nodes").fetchall()
        scored: list[tuple[float, MemoryNode]] = []
        for row in rows:
            node = _row_node(row)
            overlap = len(tokens & set(_tokens(node.label + " " + json.dumps(node.payload))))
            if overlap == 0:
                continue
            score = overlap * node.usefulness
            scored.append((score, node))
        scored.sort(key=lambda x: x[0], reverse=True)
        hits = [n for _, n in scored[:k]]
        # one-hop expansion for graph grounding
        extra: list[MemoryNode] = []
        for hit in hits:
            for _, neigh in self.neighbors(hit.id):
                extra.append(neigh)
        merged: dict[str, MemoryNode] = {n.id: n for n in hits}
        for n in extra:
            merged.setdefault(n.id, n)
        return list(merged.values())[: k + 4]

    def lessons(self, min_usefulness: float = 0.2) -> list[MemoryNode]:
        rows = self._conn.execute(
            "SELECT * FROM nodes WHERE type='lesson' AND usefulness >= ? ORDER BY usefulness DESC",
            (min_usefulness,),
        ).fetchall()
        return [_row_node(r) for r in rows]

    def prune(self, floor: float = 0.1) -> int:
        cur = self._conn.execute("DELETE FROM nodes WHERE usefulness < ?", (floor,))
        self._conn.execute(
            "DELETE FROM edges WHERE src NOT IN (SELECT id FROM nodes) OR dst NOT IN (SELECT id FROM nodes)"
        )
        self._conn.commit()
        return cur.rowcount


def _row_node(row: sqlite3.Row) -> MemoryNode:
    return MemoryNode(
        id=row["id"],
        type=row["type"],
        label=row["label"],
        payload=json.loads(row["payload_json"]),
        usefulness=row["usefulness"],
    )


def _tokens(text: str) -> list[str]:
    return [t for t in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if len(t) > 2]
