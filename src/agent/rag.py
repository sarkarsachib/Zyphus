"""
Retrieval over everything the agent has indexed.

A self-contained RAG index: text is chunked by lines, embedded with a
deterministic hashing vectorizer (stdlib `hashlib`, no model call, no network),
and searched by cosine similarity plus a light lexical boost out of SQLite
(`devmind/agent/rag.db`). Embeddings are reproducible, so the same text always
scores the same - the index can be rebuilt at any time.

Importable everywhere the agent runs: stdlib only.
"""

import hashlib
import json
import math
import os
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(REPO_ROOT, "devmind", "agent", "rag.db")

DIM = 384
CHUNK_LINES = 40
OVERLAP = 8
MAX_FILE_BYTES = 400_000
MAX_CHUNK_CHARS = 4000

SUFFIXES = (".py", ".js", ".mjs", ".ts", ".tsx", ".md", ".txt", ".json", ".yml", ".yaml",
            ".toml", ".html", ".css", ".sh", ".cfg", ".ini", ".sql", ".rst")
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", ".mypy_cache",
             "venv", ".venv", "dist", "build", "egg-info"}

TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}")


def _tokens(text: str) -> List[str]:
    return TOKEN.findall((text or "").lower())


def _embed(text: str) -> List[float]:
    """Hash each token into a fixed-width vector: no training, no download."""
    vector = [0.0] * DIM
    counts: Dict[str, int] = {}
    for token in _tokens(text):
        counts[token] = counts.get(token, 0) + 1
    for token, count in counts.items():
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign * (1.0 + math.log(count))
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


def _cosine(left: List[float], right: List[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.execute("CREATE TABLE IF NOT EXISTS chunks ("
                 "id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, chunk_index INTEGER, "
                 "start_line INTEGER, text TEXT, vector TEXT)")
    conn.execute("CREATE INDEX IF NOT EXISTS chunks_source ON chunks (source)")
    conn.commit()
    return conn


def _chunk(text: str) -> List[Tuple[int, str]]:
    """Line-window chunks with a little overlap, so a hit reads in context."""
    lines = text.splitlines()
    chunks: List[Tuple[int, str]] = []
    step = max(1, CHUNK_LINES - OVERLAP)
    for start in range(0, max(1, len(lines)), step):
        window = lines[start:start + CHUNK_LINES]
        body = "\n".join(window).strip()
        if body:
            chunks.append((start + 1, body[:MAX_CHUNK_CHARS]))
        if start + CHUNK_LINES >= len(lines):
            break
    return chunks


def _iter_files(path: str) -> List[str]:
    if os.path.isfile(path):
        return [path]
    found: List[str] = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.endswith(".egg-info")]
        for name in sorted(files):
            if name.lower().endswith(SUFFIXES):
                found.append(os.path.join(root, name))
    return found


def index(path: str = ".", tag: str = "", db_path: Optional[str] = None) -> Dict[str, Any]:
    """Index a file or a directory tree. Re-indexing a path replaces its chunks."""
    full = path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)
    if not os.path.exists(full):
        return {"error": f"no such path: {path}"}

    conn = _connect(db_path)
    files = _iter_files(full)
    added = skipped = 0
    for name in files:
        try:
            if os.path.getsize(name) > MAX_FILE_BYTES:
                skipped += 1
                continue
            with open(name, "r", encoding="utf-8", errors="replace") as handle:
                body = handle.read()
        except OSError:
            skipped += 1
            continue
        source = os.path.relpath(name, REPO_ROOT).replace(os.sep, "/")
        if tag:
            source = f"{tag}:{source}"
        conn.execute("DELETE FROM chunks WHERE source = ?", (source,))
        rows = []
        for position, (start_line, chunk) in enumerate(_chunk(body)):
            rows.append((source, position, start_line, chunk, json.dumps(_embed(chunk))))
        if rows:
            conn.executemany("INSERT INTO chunks (source, chunk_index, start_line, text, vector) "
                             "VALUES (?,?,?,?,?)", rows)
            added += 1
    conn.commit()
    conn.close()
    return {"indexed_files": added, "skipped": skipped, "path": path, **stats(db_path)}


def search(text: str, top_k: int = 5, db_path: Optional[str] = None) -> Dict[str, Any]:
    """The best-matching chunks for a query, most similar first."""
    query = (text or "").strip()
    if not query:
        return {"error": "nothing to search for", "hits": []}
    conn = _connect(db_path)
    rows = conn.execute("SELECT source, chunk_index, start_line, text, vector FROM chunks").fetchall()
    conn.close()
    if not rows:
        return {"hits": [], "note": "the index is empty - index a path first"}

    query_vector = _embed(query)
    wanted = set(_tokens(query))
    scored = []
    for source, chunk_index, start_line, body, vector_json in rows:
        stored = json.loads(vector_json)
        score = _cosine(query_vector, stored)
        overlap = len(wanted & set(_tokens(body))) / max(1, len(wanted))
        scored.append((score + 0.15 * overlap, {
            "source": source,
            "chunk": chunk_index,
            "line": start_line,
            "score": round(score + 0.15 * overlap, 4),
            "text": body,
        }))
    scored.sort(key=lambda item: item[0], reverse=True)
    hits = [entry for _, entry in scored[:max(1, int(top_k))]]
    return {"query": query, "hits": hits, "searched": len(rows)}


def sources(db_path: Optional[str] = None) -> List[str]:
    path = db_path or DB_PATH
    if not os.path.isfile(path):
        return []
    conn = _connect(db_path)
    rows = conn.execute("SELECT DISTINCT source FROM chunks ORDER BY source").fetchall()
    conn.close()
    return [row[0] for row in rows]


def _display_path(path: str) -> str:
    return os.path.relpath(path, REPO_ROOT) if path.startswith(REPO_ROOT) else path


def stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    path = db_path or DB_PATH
    if not os.path.isfile(path):
        # Reported without creating the database, so a read never writes.
        return {"documents": 0, "chunks": 0, "dimensions": DIM,
                "database": _display_path(path), "empty": True}
    conn = _connect(db_path)
    chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    files = conn.execute("SELECT COUNT(DISTINCT source) FROM chunks").fetchone()[0]
    conn.close()
    return {"documents": files, "chunks": chunks, "dimensions": DIM,
            "database": _display_path(path)}


def forget(source: str = "", db_path: Optional[str] = None) -> Dict[str, Any]:
    """Drop one indexed source, or the whole index when no source is given."""
    conn = _connect(db_path)
    if source:
        cursor = conn.execute("DELETE FROM chunks WHERE source = ? OR source LIKE ?",
                              (source, f"%{source}%"))
        removed = cursor.rowcount
    else:
        cursor = conn.execute("DELETE FROM chunks")
        removed = cursor.rowcount
    conn.commit()
    conn.close()
    return {"removed_chunks": removed, **stats(db_path)}
