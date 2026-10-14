"""
Durable state for the agent loop: a task queue and an action log in SQLite.

State lives in devmind/agent/agent.db (bind-mounted, so it survives container
restarts). The loop keeps nothing in memory between runs: a task that was
running when the process died is reclaimed once its lease expires and retried.
"""

import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.path.join(REPO_ROOT, "devmind", "agent", "agent.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id            TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    instructions  TEXT NOT NULL,
    origin        TEXT NOT NULL DEFAULT 'external',
    status        TEXT NOT NULL DEFAULT 'pending',
    priority      INTEGER NOT NULL DEFAULT 5,
    attempts      INTEGER NOT NULL DEFAULT 0,
    max_attempts  INTEGER NOT NULL DEFAULT 3,
    available_at  REAL NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    result        TEXT
);
CREATE TABLE IF NOT EXISTS actions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id      TEXT,
    tool         TEXT NOT NULL,
    arguments    TEXT NOT NULL,
    ok           INTEGER NOT NULL,
    output       TEXT,
    error        TEXT,
    duration_ms  INTEGER,
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_claim ON tasks(status, available_at);
CREATE INDEX IF NOT EXISTS idx_actions_task ON actions(task_id);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AgentStore:
    """Task queue + action log. Safe to share across threads."""

    def __init__(self, path: Optional[str] = None, lease_seconds: float = 600.0):
        self.path = path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.lease_seconds = lease_seconds
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(_SCHEMA)
        self._db.commit()

    # --- tasks ---------------------------------------------------------------

    def enqueue(self, title: str, instructions: str, origin: str = "external",
                priority: int = 5, delay_seconds: float = 0.0,
                task_id: Optional[str] = None) -> str:
        task_id = task_id or uuid.uuid4().hex[:12]
        stamp = now_iso()
        with self._lock:
            self._db.execute(
                "INSERT INTO tasks (id, title, instructions, origin, status, priority,"
                " available_at, created_at, updated_at) VALUES (?,?,?,?,'pending',?,?,?,?)",
                (task_id, title, instructions, origin, priority,
                 time.time() + max(0.0, delay_seconds), stamp, stamp),
            )
            self._db.commit()
        return task_id

    def claim_next(self) -> Optional[Dict[str, Any]]:
        """Take the highest-priority ready task, marking it running."""
        with self._lock:
            self._recover_stale()
            row = self._db.execute(
                "SELECT * FROM tasks WHERE status='pending' AND available_at<=?"
                " ORDER BY priority ASC, created_at ASC LIMIT 1",
                (time.time(),),
            ).fetchone()
            if row is None:
                return None
            self._db.execute(
                "UPDATE tasks SET status='running', attempts=attempts+1, updated_at=? WHERE id=?",
                (now_iso(), row["id"]),
            )
            self._db.commit()
            claimed = dict(row)
        claimed["attempts"] = claimed["attempts"] + 1
        return claimed

    def complete(self, task_id: str, result: str = "") -> None:
        with self._lock:
            self._db.execute(
                "UPDATE tasks SET status='done', result=?, updated_at=? WHERE id=?",
                (result, now_iso(), task_id),
            )
            self._db.commit()

    def fail(self, task_id: str, error: str, retry_delay: float = 60.0) -> str:
        """Retry with backoff until max_attempts, then park the task as failed."""
        with self._lock:
            row = self._db.execute("SELECT attempts, max_attempts FROM tasks WHERE id=?",
                                   (task_id,)).fetchone()
            if row is None:
                return "missing"
            if row["attempts"] >= row["max_attempts"]:
                self._db.execute(
                    "UPDATE tasks SET status='failed', result=?, updated_at=? WHERE id=?",
                    (error, now_iso(), task_id),
                )
                self._db.commit()
                return "failed"
            self._db.execute(
                "UPDATE tasks SET status='pending', available_at=?, result=?, updated_at=? WHERE id=?",
                (time.time() + retry_delay, error, now_iso(), task_id),
            )
            self._db.commit()
            return "retry"

    def _recover_stale(self) -> None:
        """Requeue tasks whose worker died mid-run (caller holds the lock)."""
        cutoff = datetime.now(timezone.utc).timestamp() - self.lease_seconds
        stale = self._db.execute("SELECT id, updated_at FROM tasks WHERE status='running'").fetchall()
        for row in stale:
            try:
                started = datetime.fromisoformat(row["updated_at"]).timestamp()
            except ValueError:
                started = 0.0
            if started < cutoff:
                self._db.execute(
                    "UPDATE tasks SET status='pending', available_at=?, updated_at=? WHERE id=?",
                    (time.time(), now_iso(), row["id"]),
                )

    # --- action log ----------------------------------------------------------

    def log_action(self, task_id: Optional[str], tool: str, arguments: Dict[str, Any],
                   ok: bool, output: str = "", error: str = "",
                   duration_ms: int = 0) -> None:
        import json
        with self._lock:
            self._db.execute(
                "INSERT INTO actions (task_id, tool, arguments, ok, output, error,"
                " duration_ms, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (task_id, tool, json.dumps(arguments, default=str), 1 if ok else 0,
                 output, error, duration_ms, now_iso()),
            )
            self._db.commit()

    # --- reads ---------------------------------------------------------------

    def counts(self) -> Dict[str, int]:
        with self._lock:
            rows = self._db.execute("SELECT status, COUNT(*) n FROM tasks GROUP BY status").fetchall()
        counts = {"pending": 0, "running": 0, "done": 0, "failed": 0}
        for row in rows:
            counts[row["status"]] = row["n"]
        return counts

    def recent_actions(self, limit: int = 25) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM actions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def list_tasks(self, limit: int = 25) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_task(self, task_id: str) -> None:
        """Remove a task and its actions (used to clean up a specific task)."""
        with self._lock:
            self._db.execute("DELETE FROM actions WHERE task_id=?", (task_id,))
            self._db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
            self._db.commit()
