"""Layered persistence: checkpoints, episodes, evals.

You need persistence. Not one blob — four layers with different lifetimes:

1. Checkpoint  — resume a run after crash / human interrupt (thread_id)
2. Episode     — full traces for error analysis (Ng: evals-driven development)
3. Eval store  — scores so evolution cannot promote untested skills
4. Graph memory — handled by memory.py (cross-run learning)
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .types import RunState


SCHEMA = """
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    step INTEGER NOT NULL,
    state_json TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (thread_id, step)
);
CREATE TABLE IF NOT EXISTS threads (
    thread_id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    status TEXT NOT NULL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS episodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    goal TEXT NOT NULL,
    agent TEXT,
    outcome TEXT NOT NULL,
    trace_json TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS evals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    name TEXT NOT NULL,
    score REAL NOT NULL,
    details_json TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread ON checkpoints(thread_id, step);
CREATE INDEX IF NOT EXISTS idx_episodes_goal ON episodes(goal);
"""


@dataclass
class Episode:
    id: int
    thread_id: str
    goal: str
    agent: str | None
    outcome: str
    trace: list[dict[str, Any]]
    created_at: float


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def save_checkpoint(self, state: RunState) -> None:
        now = time.time()
        self._conn.execute(
            "INSERT OR REPLACE INTO checkpoints(thread_id, step, state_json, created_at) VALUES (?,?,?,?)",
            (state.thread_id, state.step, json.dumps(state.to_json()), now),
        )
        self._conn.execute(
            "INSERT OR REPLACE INTO threads(thread_id, goal, status, updated_at) VALUES (?,?,?,?)",
            (state.thread_id, state.goal, state.status, now),
        )
        self._conn.commit()

    def load_latest(self, thread_id: str) -> RunState | None:
        row = self._conn.execute(
            "SELECT state_json FROM checkpoints WHERE thread_id=? ORDER BY step DESC LIMIT 1",
            (thread_id,),
        ).fetchone()
        if not row:
            return None
        return RunState.from_json(json.loads(row["state_json"]))

    def record_episode(self, state: RunState, outcome: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO episodes(thread_id, goal, agent, outcome, trace_json, created_at) VALUES (?,?,?,?,?,?)",
            (
                state.thread_id,
                state.goal,
                state.active_agent,
                outcome,
                json.dumps(state.trace),
                time.time(),
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def record_eval(self, thread_id: str, name: str, score: float, details: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO evals(thread_id, name, score, details_json, created_at) VALUES (?,?,?,?,?)",
            (thread_id, name, score, json.dumps(details), time.time()),
        )
        self._conn.commit()

    def recent_episodes(self, limit: int = 50) -> list[Episode]:
        rows = self._conn.execute(
            "SELECT * FROM episodes ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            Episode(
                id=r["id"],
                thread_id=r["thread_id"],
                goal=r["goal"],
                agent=r["agent"],
                outcome=r["outcome"],
                trace=json.loads(r["trace_json"]),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def similar_episodes(self, goal: str, limit: int = 8) -> list[Episode]:
        tokens = set(_tokens(goal))
        scored: list[tuple[int, Episode]] = []
        for ep in self.recent_episodes(200):
            overlap = len(tokens & set(_tokens(ep.goal)))
            if overlap:
                scored.append((overlap, ep))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ep for _, ep in scored[:limit]]


def _tokens(text: str) -> list[str]:
    return [t for t in "".join(ch.lower() if ch.isalnum() else " " for ch in text).split() if len(t) > 2]
