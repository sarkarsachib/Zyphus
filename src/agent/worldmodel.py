"""
Memory as a generative world, not a filing cabinet.

Facts are not the point here. What is stored is the *relationship* between
concepts, actions, failures and outcomes - how often `import-cycle` came with
`config-mismatch`, which procedures actually finished a debugging task, which
prediction turned out right. Relations carry an evidence count, so a
relationship the repository keeps confirming gets stronger and one that never
appears stays weak.

The model is then used to *generate* rather than to recall: `generate_hypotheses`
turns a concept's strongest relations into testable claims. Every claim comes
back marked `verified: False` and has to be confirmed against a real observation
(`confirm`), because an association is a guess about what tends to happen, not
knowledge of what is happening now.

SQLite in devmind/agent/world.db. The database is opened on first *use*, so
merely reading the world (the dashboard does) never creates a file in the repo.
Stdlib only, deterministic, no model calls.
"""

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.path.join(REPO_ROOT, "devmind", "agent", "world.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS concepts (
    name        TEXT PRIMARY KEY,
    kind        TEXT NOT NULL DEFAULT 'concept',
    mentions    INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS relations (
    src         TEXT NOT NULL,
    dst         TEXT NOT NULL,
    kind        TEXT NOT NULL,
    evidence    INTEGER NOT NULL DEFAULT 1,
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (src, dst, kind)
);
CREATE TABLE IF NOT EXISTS observations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    klass       TEXT,
    concepts    TEXT NOT NULL,
    outcome     TEXT NOT NULL,
    strategy    TEXT,
    context     TEXT,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS strategies (
    klass       TEXT NOT NULL,
    strategy    TEXT NOT NULL,
    attempts    INTEGER NOT NULL DEFAULT 0,
    successes   INTEGER NOT NULL DEFAULT 0,
    cost        REAL NOT NULL DEFAULT 0,
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (klass, strategy)
);
CREATE TABLE IF NOT EXISTS predictions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    subject     TEXT,
    claim       TEXT NOT NULL,
    basis       TEXT,
    confidence  REAL NOT NULL DEFAULT 0,
    verified    INTEGER NOT NULL DEFAULT 0,
    outcome     TEXT,
    created_at  TEXT NOT NULL,
    verified_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_relations_src ON relations(src, kind);
CREATE INDEX IF NOT EXISTS idx_relations_dst ON relations(dst, kind);
"""

# Outcomes that count as the procedure having worked. Two of these are the
# substrate's own reading of a run, not a verdict on the code under test:
#   "observed" - a real command ran and its result was recorded
#   "decisive" - the run produced an experiment that separated its candidates
# A debugging run that ends "the test still fails" has still done its job; it is
# the run that said nothing that should count against the procedure.
POSITIVE = ("ok", "success", "succeeded", "resolved", "confirmed", "pass", "passed",
            "observed", "decisive")

EMPTY_STATS: Dict[str, Any] = {"exists": False, "concepts": 0, "relations": 0, "observations": 0,
                               "strategies": 0, "predictions": 0, "verified": 0,
                               "top_relations": [], "top_strategies": []}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _is_positive(outcome: str) -> bool:
    return (outcome or "").strip().lower() in POSITIVE


class WorldModel:
    """Relationships between concepts, actions, failures and outcomes."""

    def __init__(self, path: Optional[str] = None):
        self.path = path or DEFAULT_DB_PATH
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None

    def _db(self) -> sqlite3.Connection:
        """Open the database on first real use - reading must not create it."""
        if self._conn is None:
            parent = os.path.dirname(self.path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            self._conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()
        return self._conn

    # --- learning ------------------------------------------------------------

    def _concept(self, db: sqlite3.Connection, name: str, kind: str = "concept") -> None:
        name = (name or "").strip()
        if not name:
            return
        db.execute(
            "INSERT INTO concepts (name, kind, mentions, updated_at) VALUES (?,?,1,?)"
            " ON CONFLICT(name) DO UPDATE SET mentions=mentions+1, updated_at=excluded.updated_at",
            (name, kind, now_iso()),
        )

    def _relation(self, db: sqlite3.Connection, src: str, dst: str, kind: str) -> None:
        if not src or not dst or src == dst:
            return
        db.execute(
            "INSERT INTO relations (src, dst, kind, evidence, updated_at) VALUES (?,?,?,1,?)"
            " ON CONFLICT(src, dst, kind) DO UPDATE SET evidence=evidence+1,"
            " updated_at=excluded.updated_at",
            (src, dst, kind, now_iso()),
        )

    def observe(self, concepts: Iterable[str], outcome: str, klass: str = "unknown",
                strategy: str = "", context: str = "", cost: float = 0.0,
                extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Record one real result and let it reshape the relationships.

        Every concept is linked to the outcome, and the leading concept is linked
        to the ones that came with it - those co-occurrence edges are what later
        hypotheses are generated from. A procedure that finished positive gets a
        success against its name, which is what `strategies()` ranks.
        """
        names = [str(concept).strip() for concept in concepts if str(concept).strip()]
        outcome_label = (outcome or "unknown").strip().lower()
        with self._lock:
            db = self._db()
            for index, name in enumerate(names):
                self._concept(db, name, "leading" if index == 0 else "concept")
                self._relation(db, name, outcome_label, "leads_to")
            for index, first in enumerate(names):
                for second in names[index + 1:]:
                    self._relation(db, first, second, "co_occurs")
            if strategy:
                db.execute(
                    "INSERT INTO strategies (klass, strategy, attempts, successes, cost, updated_at)"
                    " VALUES (?,?,1,?,?,?) ON CONFLICT(klass, strategy) DO UPDATE SET"
                    " attempts=attempts+1, successes=successes+excluded.successes,"
                    " cost=cost+excluded.cost, updated_at=excluded.updated_at",
                    (klass, strategy, 1 if _is_positive(outcome_label) else 0,
                     float(cost or 0.0), now_iso()),
                )
            db.execute(
                "INSERT INTO observations (klass, concepts, outcome, strategy, context, created_at)"
                " VALUES (?,?,?,?,?,?)",
                (klass, json.dumps(names), outcome_label, strategy,
                 json.dumps(extra or {"context": context})[:4000], now_iso()),
            )
            db.commit()
        return {"concepts": names, "outcome": outcome_label, "strategy": strategy}

    def associate(self, src: str, dst: str, kind: str = "relates_to") -> Dict[str, Any]:
        """Add one relation by hand (or from an inspected artifact)."""
        with self._lock:
            db = self._db()
            self._concept(db, src)
            self._concept(db, dst)
            self._relation(db, src, dst, kind)
            db.commit()
        return self.relation(src, dst, kind) or {"src": src, "dst": dst, "kind": kind}

    # --- reading the world ---------------------------------------------------

    def relation(self, src: str, dst: str, kind: str = "") -> Optional[Dict[str, Any]]:
        if not os.path.isfile(self.path):
            return None
        row = self._db().execute(
            "SELECT * FROM relations WHERE src=? AND dst=?" + (" AND kind=?" if kind else ""),
            (src, dst, kind) if kind else (src, dst),
        ).fetchone()
        return self._shape(row) if row else None

    def neighbors(self, concept: str, limit: int = 10) -> List[Dict[str, Any]]:
        if not os.path.isfile(self.path):
            return []
        rows = self._db().execute(
            "SELECT * FROM relations WHERE src=? OR dst=?"
            " ORDER BY evidence DESC, updated_at DESC LIMIT ?",
            (concept, concept, limit),
        ).fetchall()
        return [self._shape(row) for row in rows]

    def _shape(self, row: sqlite3.Row) -> Dict[str, Any]:
        src, dst = row["src"], row["dst"]
        mentions = self._db().execute(
            "SELECT mentions FROM concepts WHERE name=?", (src,)
        ).fetchone()
        base = mentions["mentions"] if mentions else row["evidence"]
        evidence = row["evidence"]
        denominator = max(1, base if row["kind"] != "leads_to" else evidence + 1)
        return {
            "src": src,
            "dst": dst,
            "kind": row["kind"],
            "evidence": evidence,
            "confidence": round(min(1.0, evidence / denominator), 3),
            "observation": f"{evidence} observation(s) link {src!r} to {dst!r} ({row['kind']})",
            "updated_at": row["updated_at"],
        }

    def strategies(self, klass: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Measured procedures: attempts, successes and the resulting success rate."""
        if not os.path.isfile(self.path):
            return []
        rows = self._db().execute(
            "SELECT * FROM strategies" + (" WHERE klass=?" if klass else "")
            + " ORDER BY attempts DESC LIMIT ?",
            (klass, limit) if klass else (limit,),
        ).fetchall()
        shaped = []
        for row in rows:
            attempts = max(1, row["attempts"])
            shaped.append({
                "klass": row["klass"],
                "strategy": row["strategy"],
                "attempts": row["attempts"],
                "successes": row["successes"],
                "success_rate": round(row["successes"] / attempts, 3),
                "cost": round(row["cost"] or 0.0, 2),
            })
        return sorted(shaped, key=lambda entry: (-entry["success_rate"], -entry["attempts"]))

    def prefer_strategy(self, klass: str, minimum_success: float = 0.6) -> Optional[Dict[str, Any]]:
        """The procedure this class has actually done well with, if any."""
        for entry in self.strategies(klass):
            if entry["attempts"] >= 2 and entry["success_rate"] >= minimum_success:
                return entry
        return None

    # --- generative use ------------------------------------------------------

    def generate_hypotheses(self, concept: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Turn the concept's strongest relations into testable claims.

        A relation is a tendency, so the claim is a prediction about what is
        likely happening now. It is stored as an unverified prediction: the
        substrate uses it to choose a test, and only an observation (`confirm`)
        turns it into knowledge.
        """
        claims: List[Dict[str, Any]] = []
        for relation in self.neighbors(concept, limit=limit * 2):
            other = relation["dst"] if relation["src"] == concept else relation["src"]
            strength = min(1.0, relation["evidence"] / 5.0)
            claim = (f"{concept} tends to come with {other} "
                     f"({relation['kind']}, {relation['evidence']} prior observation(s))")
            with self._lock:
                db = self._db()
                cursor = db.execute(
                    "INSERT INTO predictions (subject, claim, basis, confidence, verified,"
                    " created_at) VALUES (?,?,?,?,0,?)",
                    (concept, claim,
                     f"relation:{relation['src']}->{relation['dst']}({relation['kind']})",
                     round(strength, 3), now_iso()),
                )
                db.commit()
                prediction_id = cursor.lastrowid
            claims.append({
                "id": prediction_id,
                "claim": claim,
                "predicts": other,
                "basis": relation["kind"],
                "confidence": round(strength, 3),
                "verified": False,
                "test": f"look for {other} and check whether {concept} is present",
            })
            if len(claims) >= limit:
                break
        return claims

    def confirm(self, prediction_id: int, outcome: str, evidence: str = "") -> Dict[str, Any]:
        """An observation that settles a generated prediction."""
        if not os.path.isfile(self.path):
            return {"confirmed": False, "error": f"no prediction {prediction_id}"}
        with self._lock:
            db = self._db()
            row = db.execute("SELECT * FROM predictions WHERE id=?", (prediction_id,)).fetchone()
            if row is None:
                return {"confirmed": False, "error": f"no prediction {prediction_id}"}
            db.execute("UPDATE predictions SET verified=1, outcome=?, verified_at=? WHERE id=?",
                       (outcome, now_iso(), prediction_id))
            db.commit()
        return {"confirmed": True, "id": prediction_id, "claim": row["claim"],
                "outcome": outcome, "evidence": evidence,
                "was_confirmed_by_observation": _is_positive(outcome)}

    def predictions(self, verified: Optional[bool] = None, limit: int = 20) -> List[Dict[str, Any]]:
        if not os.path.isfile(self.path):
            return []
        clause = "" if verified is None else f" WHERE verified={1 if verified else 0}"
        rows = self._db().execute(
            "SELECT * FROM predictions" + clause + " ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [{"id": row["id"], "subject": row["subject"], "claim": row["claim"],
                 "basis": row["basis"], "confidence": row["confidence"],
                 "verified": bool(row["verified"]), "outcome": row["outcome"],
                 "created_at": row["created_at"]} for row in rows]

    # --- housekeeping --------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Counts. Reading never creates the database."""
        if not os.path.isfile(self.path):
            return {"database": self.path, **EMPTY_STATS}

        def fetch(sql: str) -> int:
            return self._db().execute(sql).fetchone()[0]

        return {
            "database": self.path,
            "exists": True,
            "concepts": fetch("SELECT COUNT(*) FROM concepts"),
            "relations": fetch("SELECT COUNT(*) FROM relations"),
            "observations": fetch("SELECT COUNT(*) FROM observations"),
            "strategies": fetch("SELECT COUNT(*) FROM strategies"),
            "predictions": fetch("SELECT COUNT(*) FROM predictions"),
            "verified": fetch("SELECT COUNT(*) FROM predictions WHERE verified=1"),
            "top_relations": [self._shape(row) for row in self._db().execute(
                "SELECT * FROM relations ORDER BY evidence DESC, src LIMIT 8").fetchall()],
            "top_strategies": self.strategies(limit=6),
        }

    def forget(self, concept: Optional[str] = None) -> Dict[str, Any]:
        """Drop one concept's relations, or reset the world entirely."""
        if not os.path.isfile(self.path):
            return {"forgotten": concept or "everything"}
        with self._lock:
            db = self._db()
            if concept:
                db.execute("DELETE FROM relations WHERE src=? OR dst=?", (concept, concept))
                db.execute("DELETE FROM concepts WHERE name=?", (concept,))
            else:
                for table in ("concepts", "relations", "observations", "strategies", "predictions"):
                    db.execute(f"DELETE FROM {table}")
            db.commit()
        return {"forgotten": concept or "everything"}
