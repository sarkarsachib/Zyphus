"""
The consolidation phase: experience becoming structure.

Everything up to here is online - the field settles, the substrate composes, the
tools act - and none of it changes what the agent knows afterwards, except the
field's own gains. Consolidation is the offline pass that replays what actually
happened and makes it durable:

  replay      the window of real tool calls with their measured outcome and
              duration, read from the action log the loop already keeps
  accumulate  a per-tool competence record that outlives the log, so
              reliability is a measurement across passes instead of a guess
  promote     a tool whose measured reliability is good enough becomes a
              procedural strategy in the world model (`klass="tool"`), and one
              that keeps failing is recorded as failing - `prefer_strategy` then
              has evidence behind it instead of optimism
  settle      the pass itself is recorded with a watermark, so the next pass
              only consolidates ground it has not already seen

A pass never invents an outcome: with nothing to replay it reports zero and
records a pass that says so. `dry_run` computes the same plan and writes
nothing, neither here nor in the world model.

SQLite in devmind/agent/consolidation.db (`ZYPHUS_CONSOLIDATION_PATH`
overrides). Stdlib only, deterministic, no model calls.
"""

import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.agent.store import AgentStore
from src.agent.worldmodel import WorldModel

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.path.join(REPO_ROOT, "devmind", "agent", "consolidation.db")

DEFAULT_WINDOW = 60          # how many recent tool calls one pass may replay
DEFAULT_EVERY = 20           # unconsolidated calls that make a pass due
PROMOTE_ATTEMPTS = 3         # a measurement, not a first impression
PROMOTE_RATE = 0.8           # reliable enough to become a strategy
WEAK_RATE = 0.5              # failing often enough to be recorded as failing

_SCHEMA = """
CREATE TABLE IF NOT EXISTS passes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ran_at         TEXT NOT NULL,
    window         INTEGER NOT NULL,
    replayed       INTEGER NOT NULL,
    last_action_id INTEGER NOT NULL,
    promoted       TEXT NOT NULL,
    weak           TEXT NOT NULL,
    duration_ms    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS skills (
    tool        TEXT PRIMARY KEY,
    attempts    INTEGER NOT NULL,
    successes   INTEGER NOT NULL,
    total_ms    INTEGER NOT NULL,
    passes      INTEGER NOT NULL,
    promoted_at TEXT,
    updated_at  TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_list(raw: Any) -> List[str]:
    try:
        value = json.loads(raw or "[]")
    except ValueError:
        return []
    return [str(item) for item in value] if isinstance(value, list) else []


class Consolidation:
    """Replay measured experience, keep the competence, forget the rest."""

    def __init__(self, store: Optional[AgentStore] = None,
                 world: Optional[WorldModel] = None,
                 path: Optional[str] = None):
        self.store = store or AgentStore()
        self._world = world
        self.path = path or os.environ.get("ZYPHUS_CONSOLIDATION_PATH") or DEFAULT_DB_PATH
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None

    def _db(self, create: bool = True) -> sqlite3.Connection:
        """Open on first use; a read never creates the database."""
        if self._conn is None:
            if not create and not os.path.isfile(self.path):
                raise FileNotFoundError(self.path)
            parent = os.path.dirname(self.path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            self._conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()
        return self._conn

    def world(self) -> WorldModel:
        if self._world is None:
            self._world = WorldModel()
        return self._world

    # --- reading what has already been consolidated --------------------------

    def passes(self) -> int:
        if not os.path.isfile(self.path):
            return 0
        row = self._db().execute("SELECT COUNT(*) FROM passes").fetchone()
        return int(row[0] or 0)

    def watermark(self) -> int:
        """The last action id already replayed - the boundary of new ground."""
        if not os.path.isfile(self.path):
            return 0
        row = self._db().execute("SELECT COALESCE(MAX(last_action_id), 0) FROM passes").fetchone()
        return int(row[0] or 0)

    def pending_actions(self, limit: int = DEFAULT_EVERY) -> int:
        """How many of the newest actions this pass has never seen."""
        boundary = self.watermark()
        return sum(1 for action in self.store.recent_actions(max(1, limit))
                   if int(action["id"] or 0) > boundary)

    def should_run(self, every: int = DEFAULT_EVERY) -> bool:
        """Enough unconsolidated ground to be worth a pass (one is enough at first)."""
        needed = 1 if self.passes() == 0 else max(1, int(every))
        return self.pending_actions(needed) >= needed

    @staticmethod
    def _shape_skill(row: sqlite3.Row) -> Dict[str, Any]:
        attempts = max(1, int(row["attempts"] or 0))
        return {
            "tool": row["tool"],
            "attempts": int(row["attempts"] or 0),
            "successes": int(row["successes"] or 0),
            "success_rate": round(int(row["successes"] or 0) / attempts, 3),
            "mean_ms": round(float(row["total_ms"] or 0) / attempts, 1),
            "passes": int(row["passes"] or 0),
            "promoted_at": row["promoted_at"],
            "updated_at": row["updated_at"],
        }

    def skills(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Measured competence per tool, strongest first. Reading never creates."""
        if not os.path.isfile(self.path):
            return []
        rows = self._db().execute(
            "SELECT * FROM skills ORDER BY attempts DESC, successes DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._shape_skill(row) for row in rows]

    def skill(self, tool: str) -> Optional[Dict[str, Any]]:
        if not os.path.isfile(self.path):
            return None
        row = self._db().execute("SELECT * FROM skills WHERE tool=?", (tool,)).fetchone()
        return self._shape_skill(row) if row else None

    def latest(self) -> Dict[str, Any]:
        """The last pass and what it left behind, for the dashboard and the CLI."""
        if not os.path.isfile(self.path):
            return {"database": self.path, "passes": 0, "last": None, "skills": []}
        row = self._db().execute("SELECT * FROM passes ORDER BY id DESC LIMIT 1").fetchone()
        last = None
        if row is not None:
            last = {
                "id": row["id"],
                "ran_at": row["ran_at"],
                "window": row["window"],
                "replayed": row["replayed"],
                "last_action_id": row["last_action_id"],
                "promoted": _json_list(row["promoted"]),
                "weak": _json_list(row["weak"]),
                "duration_ms": row["duration_ms"],
            }
        return {"database": self.path, "passes": self.passes(), "last": last,
                "skills": self.skills(limit=6)}

    # --- one pass ------------------------------------------------------------

    def run(self, window: int = DEFAULT_WINDOW, dry_run: bool = False) -> Dict[str, Any]:
        """Replay the unreplayed window and promote what it measured."""
        started = time.time()
        window = max(1, int(window or DEFAULT_WINDOW))
        boundary = self.watermark()
        actions = self.store.recent_actions(window)
        fresh = [action for action in reversed(actions)
                 if int(action["id"] or 0) > boundary]

        gained: Dict[str, Dict[str, int]] = {}
        for action in fresh:
            tool = str(action["tool"])
            entry = gained.setdefault(tool, {"attempts": 0, "successes": 0, "total_ms": 0})
            entry["attempts"] += 1
            entry["successes"] += 1 if action["ok"] else 0
            entry["total_ms"] += int(action["duration_ms"] or 0)

        measured: List[Dict[str, Any]] = []
        for tool in sorted(gained):
            prior = self.skill(tool) or {"attempts": 0, "successes": 0, "mean_ms": 0.0}
            gained_entry = gained[tool]
            attempts = int(prior["attempts"]) + gained_entry["attempts"]
            successes = int(prior["successes"]) + gained_entry["successes"]
            total_ms = gained_entry["total_ms"] + float(prior["mean_ms"]) * int(prior["attempts"])
            measured.append({
                "tool": tool,
                "attempts": attempts,
                "successes": successes,
                "success_rate": round(successes / max(1, attempts), 3),
                "mean_ms": round(total_ms / max(1, attempts), 1),
                "runs": gained_entry["attempts"],
            })

        promoted, weak = [], []
        for record in measured:
            if record["attempts"] < PROMOTE_ATTEMPTS:
                continue
            if record["success_rate"] >= PROMOTE_RATE:
                promoted.append(record)
            elif record["success_rate"] < WEAK_RATE:
                weak.append(record)

        report: Dict[str, Any] = {
            "ran_at": now_iso(),
            "dry_run": bool(dry_run),
            "window": window,
            "replayed": len(fresh),
            "last_action_id": max([boundary] + [int(a["id"]) for a in fresh]),
            "tools": sorted(measured, key=lambda entry: -entry["attempts"]),
            "promoted": [record["tool"] for record in promoted],
            "weak": [record["tool"] for record in weak],
        }

        if dry_run:
            report["promotions"] = promoted
            report["duration_ms"] = int((time.time() - started) * 1000)
            return report

        world = self.world()
        for record in promoted:
            world.observe([record["tool"]], "ok", klass="tool", strategy=record["tool"],
                          context=f"consolidation: {record['attempts']} runs, "
                                  f"rate {record['success_rate']}")
        for record in weak:
            world.observe([record["tool"]], "failed", klass="tool", strategy=record["tool"],
                          context=f"consolidation: {record['attempts']} runs, "
                                  f"rate {record['success_rate']}")

        report["duration_ms"] = int((time.time() - started) * 1000)
        self._record(report, measured)
        return report

    def _record(self, report: Dict[str, Any], measured: List[Dict[str, Any]]) -> None:
        """Write the pass and the competence it measured. Caller has decided to."""
        promoted = set(report["promoted"])
        stamp = now_iso()
        with self._lock:
            db = self._db()
            db.execute(
                "INSERT INTO passes (ran_at, window, replayed, last_action_id, promoted, weak,"
                " duration_ms) VALUES (?,?,?,?,?,?,?)",
                (report["ran_at"], report["window"], report["replayed"],
                 report["last_action_id"], json.dumps(report["promoted"]),
                 json.dumps(report["weak"]), report["duration_ms"]),
            )
            for record in measured:
                db.execute(
                    "INSERT INTO skills (tool, attempts, successes, total_ms, passes, promoted_at,"
                    " updated_at) VALUES (?,?,?,?,1,?,?)"
                    " ON CONFLICT(tool) DO UPDATE SET attempts=excluded.attempts,"
                    " successes=excluded.successes, total_ms=excluded.total_ms,"
                    " passes=passes+1,"
                    " promoted_at=COALESCE(excluded.promoted_at, skills.promoted_at),"
                    " updated_at=excluded.updated_at",
                    (record["tool"], record["attempts"], record["successes"],
                     round(record["mean_ms"] * max(1, record["attempts"])),
                     stamp if record["tool"] in promoted else None, stamp),
                )
            db.commit()
