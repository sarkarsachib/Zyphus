"""
Hybrid memory: four storage layers behind one object.

- SQL (sqlite3) for identity rows,
- NoSQL (JSON documents) for the mood map,
- Vector (sqlite3 + a deterministic hashed embedding) for similarity search,
- JSON files for cognition state and the system profile.

The vector layer used to be a pair of `print()` stubs. It is now a real store:
text is embedded into a fixed-dimension vector with `hashlib` (no model call, no
network), vectors are persisted as packed float64 blobs, and search ranks stored
vectors by cosine similarity. It works with numpy when it is installed and falls
back to pure Python when it is not.
"""

import array
import hashlib
import json
import math
import os
import re
import sqlite3
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence

try:  # optional: only used to speed up cosine similarity
    import numpy as _np
except Exception:  # pragma: no cover - exercised when numpy is absent
    _np = None

DEFAULT_DIM = 256
_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN.findall((text or "").lower())


def embed_text(text: str, dim: int = DEFAULT_DIM) -> List[float]:
    """A deterministic hashed embedding: tokens and token bigrams, L2 normalised.

    The same text always yields the same vector, on any machine, with no
    model or network involved. It is a bag-of-features sketch rather than a
    semantic embedding, but it ranks lexically related text correctly.
    """
    if dim <= 0:
        raise ValueError("dim must be positive")
    vector = [0.0] * dim
    tokens = _tokenize(text)
    if not tokens:
        return vector

    features = [(token, 1.0) for token in tokens]
    features += [(f"{first}_{second}", 0.5) for first, second in zip(tokens, tokens[1:])]
    for feature, weight in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=16).digest()
        index = int.from_bytes(digest[:8], "big") % dim
        sign = 1.0 if digest[8] & 1 else -1.0
        vector[index] += sign * weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


def _pack(vector: Sequence[float]) -> bytes:
    return array.array("d", [float(value) for value in vector]).tobytes()


def _unpack(blob: bytes) -> List[float]:
    values = array.array("d")
    values.frombytes(blob)
    return list(values)


def cosine_similarity(first: Sequence[float], second: Sequence[float]) -> float:
    """Cosine similarity of two equal-length vectors; 0.0 when either is empty."""
    if not first or not second or len(first) != len(second):
        return 0.0
    if _np is not None:
        left = _np.asarray(first, dtype=float)
        right = _np.asarray(second, dtype=float)
        denominator = float(_np.linalg.norm(left) * _np.linalg.norm(right))
        return float(_np.dot(left, right) / denominator) if denominator else 0.0

    dot = sum(a * b for a, b in zip(first, second))
    left_norm = math.sqrt(sum(a * a for a in first))
    right_norm = math.sqrt(sum(b * b for b in second))
    denominator = left_norm * right_norm
    return dot / denominator if denominator else 0.0


class HybridMemorySystem:
    def __init__(self, base_path: str = "devmind_memory"):
        self.base_path = base_path
        self.sql_path = os.path.join(self.base_path, "sql")
        self.nosql_path = os.path.join(self.base_path, "nosql")
        self.vector_path = os.path.join(self.base_path, "vector")
        self.json_path = os.path.join(self.base_path, "json")

        self._ensure_directories()

    def _ensure_directories(self):
        os.makedirs(self.sql_path, exist_ok=True)
        os.makedirs(self.nosql_path, exist_ok=True)
        os.makedirs(self.vector_path, exist_ok=True)
        os.makedirs(self.json_path, exist_ok=True)

    # SQL Layer Operations
    def _get_sql_connection(self, db_name: str):
        return sqlite3.connect(os.path.join(self.sql_path, db_name))

    def sql_insert_identity(self, fusion_id: str, creator_key: str, self_awareness_logs: str):
        conn = self._get_sql_connection("identity.db")
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS identity "
            "(fusion_id TEXT PRIMARY KEY, creator_key TEXT, self_awareness_logs TEXT)")
        cursor.execute(
            "INSERT OR REPLACE INTO identity (fusion_id, creator_key, self_awareness_logs) "
            "VALUES (?, ?, ?)", (fusion_id, creator_key, self_awareness_logs))
        conn.commit()
        conn.close()

    def sql_get_identity(self, fusion_id: str) -> Dict[str, Any]:
        conn = self._get_sql_connection("identity.db")
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM identity WHERE fusion_id = ?", (fusion_id,))
            row = cursor.fetchone()
        except sqlite3.OperationalError:
            row = None
        conn.close()
        if row:
            return {"fusion_id": row[0], "creator_key": row[1], "self_awareness_logs": row[2]}
        return {}

    # NoSQL Layer Operations (documents held as JSON)
    def nosql_save_moodmap(self, data: Dict[str, Any]):
        with open(os.path.join(self.nosql_path, "moodmap.json"), "w") as f:
            json.dump(data, f, indent=4)

    def nosql_load_moodmap(self) -> Dict[str, Any]:
        try:
            with open(os.path.join(self.nosql_path, "moodmap.json"), "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    # Vector Layer Operations
    def _get_vector_connection(self):
        return sqlite3.connect(os.path.join(self.vector_path, "embeddings.db"))

    def _ensure_vector_schema(self, conn) -> None:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS embeddings ("
            "id TEXT PRIMARY KEY, label TEXT, namespace TEXT, dim INTEGER NOT NULL, "
            "vector BLOB NOT NULL, text TEXT, metadata TEXT, created REAL NOT NULL)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_embeddings_namespace ON embeddings(namespace)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_embeddings_label ON embeddings(label)")

    def vector_add_embedding(self, embedding_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store one vector. `embedding_data` holds text and/or an embedding.

        Recognised keys: `text`, `embedding`, `label`, `namespace`, `metadata`,
        `id`. A deterministic id is derived from namespace/label/text, so
        re-adding the same entry replaces it instead of duplicating it.
        """
        text = (embedding_data.get("text") or "").strip()
        embedding = embedding_data.get("embedding")
        namespace = str(embedding_data.get("namespace") or "default")
        label = str(embedding_data.get("label") or "")
        metadata = embedding_data.get("metadata") or {}

        if embedding is None:
            if not text:
                raise ValueError("store either text or an explicit embedding")
            embedding = embed_text(text)
        if not isinstance(embedding, (list, tuple)) or not embedding:
            raise ValueError("embedding must be a non-empty list of numbers")
        vector = [float(value) for value in embedding]

        item_id = str(embedding_data.get("id") or self._vector_id(namespace, label, text, vector))
        conn = self._get_vector_connection()
        try:
            self._ensure_vector_schema(conn)
            conn.execute(
                "INSERT OR REPLACE INTO embeddings "
                "(id, label, namespace, dim, vector, text, metadata, created) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (item_id, label, namespace, len(vector), _pack(vector), text,
                 json.dumps(metadata, default=str), time.time()))
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, "id": item_id, "namespace": namespace, "label": label,
                "dim": len(vector), "embedded_text": bool(text)}

    def vector_add_text(self, text: str, label: str = "", namespace: str = "default",
                        metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Embed a piece of text and store it."""
        return self.vector_add_embedding({"text": text, "label": label,
                                          "namespace": namespace, "metadata": metadata})

    @staticmethod
    def _vector_id(namespace: str, label: str, text: str, vector: Sequence[float]) -> str:
        if label or text:
            seed = f"{namespace}|{label}|{text}"
        else:  # an opaque vector with no label: content-addressed
            seed = f"{namespace}|" + ",".join(f"{value:.6f}" for value in vector)
        return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:20]

    def _load_vectors(self, conn, namespace: Optional[str]) -> Iterable[tuple]:
        if namespace:
            return conn.execute(
                "SELECT id, label, namespace, dim, vector, text, metadata, created "
                "FROM embeddings WHERE namespace = ?", (namespace,)).fetchall()
        return conn.execute(
            "SELECT id, label, namespace, dim, vector, text, metadata, created "
            "FROM embeddings").fetchall()

    def vector_search_embeddings(self, query_embedding: Sequence[float], top_k: int = 5,
                                 namespace: Optional[str] = None,
                                 min_score: float = 0.0) -> List[Dict[str, Any]]:
        """Rank stored vectors by cosine similarity to `query_embedding`."""
        if not query_embedding:
            raise ValueError("query_embedding must be a non-empty list of numbers")
        top_k = max(1, int(top_k))
        db_file = os.path.join(self.vector_path, "embeddings.db")
        if not os.path.exists(db_file):
            return []

        conn = self._get_vector_connection()
        try:
            self._ensure_vector_schema(conn)
            rows = self._load_vectors(conn, namespace)
        finally:
            conn.close()

        query = [float(value) for value in query_embedding]
        scored: List[Dict[str, Any]] = []
        for item_id, label, item_namespace, dim, blob, text, metadata, created in rows:
            vector = _unpack(blob)
            if len(vector) != len(query):
                continue
            score = cosine_similarity(query, vector)
            if score < min_score:
                continue
            scored.append({
                "id": item_id,
                "label": label,
                "namespace": item_namespace,
                "text": text or "",
                "score": round(score, 6),
                "metadata": json.loads(metadata) if metadata else {},
                "created": created,
            })
        scored.sort(key=lambda hit: hit["score"], reverse=True)
        return scored[:top_k]

    def vector_search_text(self, text: str, top_k: int = 5,
                           namespace: Optional[str] = None,
                           min_score: float = 0.0) -> List[Dict[str, Any]]:
        """Embed a query and search by it."""
        return self.vector_search_embeddings(embed_text(text), top_k=top_k,
                                             namespace=namespace, min_score=min_score)

    def vector_get(self, item_id: str) -> Dict[str, Any]:
        conn = self._get_vector_connection()
        try:
            self._ensure_vector_schema(conn)
            row = conn.execute(
                "SELECT id, label, namespace, dim, text, metadata, created FROM embeddings "
                "WHERE id = ?", (item_id,)).fetchone()
        finally:
            conn.close()
        if not row:
            return {}
        return {"id": row[0], "label": row[1], "namespace": row[2], "dim": row[3],
                "text": row[4] or "", "metadata": json.loads(row[5]) if row[5] else {},
                "created": row[6]}

    def vector_delete(self, item_id: Optional[str] = None, namespace: Optional[str] = None,
                      label: Optional[str] = None) -> Dict[str, Any]:
        """Delete by id, or every vector matching namespace/label."""
        clauses, params = [], []
        if item_id:
            clauses.append("id = ?")
            params.append(item_id)
        if namespace:
            clauses.append("namespace = ?")
            params.append(namespace)
        if label:
            clauses.append("label = ?")
            params.append(label)
        if not clauses:
            raise ValueError("pass an id, a namespace or a label to delete")

        conn = self._get_vector_connection()
        try:
            self._ensure_vector_schema(conn)
            cursor = conn.execute(
                f"DELETE FROM embeddings WHERE {' AND '.join(clauses)}", params)
            conn.commit()
            removed = cursor.rowcount
        finally:
            conn.close()
        return {"ok": True, "removed": removed}

    def vector_stats(self) -> Dict[str, Any]:
        db_file = os.path.join(self.vector_path, "embeddings.db")
        if not os.path.exists(db_file):
            return {"ok": True, "items": 0, "namespaces": {}, "dimensions": 0,
                    "database": db_file}
        conn = self._get_vector_connection()
        try:
            self._ensure_vector_schema(conn)
            items = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
            rows = conn.execute(
                "SELECT namespace, COUNT(*), MAX(dim) FROM embeddings GROUP BY namespace"
            ).fetchall()
        finally:
            conn.close()
        return {
            "ok": True,
            "items": items,
            "namespaces": {name: count for name, count, _ in rows},
            "dimensions": max((dim for _, _, dim in rows), default=0),
            "database": db_file,
        }

    # JSON Layer Operations
    def json_save_cognition_state(self, data: Dict[str, Any]):
        with open(os.path.join(self.json_path, "cognition_state.json"), "w") as f:
            json.dump(data, f, indent=4)

    def json_load_cognition_state(self) -> Dict[str, Any]:
        try:
            with open(os.path.join(self.json_path, "cognition_state.json"), "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def json_save_system_profile(self, data: Dict[str, Any]):
        with open(os.path.join(self.json_path, "system_profile.json"), "w") as f:
            json.dump(data, f, indent=4)

    def json_load_system_profile(self) -> Dict[str, Any]:
        try:
            with open(os.path.join(self.json_path, "system_profile.json"), "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}


if __name__ == "__main__":
    memory_system = HybridMemorySystem()

    memory_system.sql_insert_identity("devmind_core", "creator_alpha",
                                      "Initial self-awareness logs.")
    print(f"SQL Identity: {memory_system.sql_get_identity('devmind_core')}")

    memory_system.nosql_save_moodmap({"joy": 0.7, "anger": 0.2})
    print(f"NoSQL Mood: {memory_system.nosql_load_moodmap()}")

    memory_system.vector_add_text("the heartbeat engine models neural rhythms", label="rhythm")
    memory_system.vector_add_text("the retrieval index searches its own source", label="rag")
    print(f"Vector store: {memory_system.vector_stats()}")
    print(f"Search 'neural heartbeat': "
          f"{memory_system.vector_search_text('neural heartbeat', top_k=1)}")
