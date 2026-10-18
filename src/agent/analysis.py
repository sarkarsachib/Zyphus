"""
Real static analysis, shared by the cognitive substrate.

Everything here reads the repository from disk with the standard library's
`ast` module: nothing is imported by executing it, no model is called and no
file is written. The results are plain dicts, so a substrate node can consume
them, a tool can print them and a test can assert on them.

These are the measurements the rest of the substrate reasons over - how the
repository is shaped, which module imports which, where the symbols live, and
what a proposed change would actually touch.
"""

import ast
import os
from typing import Any, Dict, List, Optional, Set, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", ".mypy_cache",
             "venv", ".venv", "dist", "build", "egg-info", "devmind", ".claude"}
PY_SUFFIX = ".py"


def _iter_py_files(root: str) -> List[str]:
    found: List[str] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in sorted(files):
            if name.endswith(PY_SUFFIX):
                found.append(os.path.join(base, name))
    return found


def module_name(path: str, root: Optional[str] = None) -> str:
    """`src/agent/brain.py` -> `src.agent.brain` (relative to the repo root)."""
    root = root or REPO_ROOT
    rel = os.path.relpath(os.path.abspath(path), os.path.abspath(root))
    rel = rel[:-len(PY_SUFFIX)] if rel.endswith(PY_SUFFIX) else rel
    rel = rel.replace(os.sep, ".")
    if rel.endswith(".__init__"):
        rel = rel[: -len(".__init__")]
    return rel


def scan_repo(root: Optional[str] = None, hints: Optional[List[str]] = None) -> Dict[str, Any]:
    """Shape of the tree: counts by suffix, total size, and which hinted paths exist.

    `hints` are file or directory names the goal mentioned; only the ones that
    really exist come back in `candidates`, so a plan never assumes an artifact
    that is not there.
    """
    root = root or REPO_ROOT
    by_suffix: Dict[str, int] = {}
    total_bytes = 0
    entries = 0
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            entries += 1
            suffix = os.path.splitext(name)[1].lower() or "(none)"
            by_suffix[suffix] = by_suffix.get(suffix, 0) + 1
            try:
                total_bytes += os.path.getsize(os.path.join(base, name))
            except OSError:
                pass

    candidates: List[Dict[str, str]] = []
    for hint in hints or []:
        candidate = hint if os.path.isabs(hint) else os.path.join(root, hint)
        if os.path.isfile(candidate):
            candidates.append({"path": hint, "kind": "file"})
        elif os.path.isdir(candidate):
            candidates.append({"path": hint, "kind": "directory"})

    python_files = _iter_py_files(root)
    return {
        "root": root,
        "entries": entries,
        "total_bytes": total_bytes,
        "by_suffix": dict(sorted(by_suffix.items(), key=lambda kv: -kv[1])[:12]),
        "python_files": len(python_files),
        "candidates": candidates,
    }


def _imports(tree: ast.AST, module: str) -> List[Tuple[str, str]]:
    """(target module, kind) for every import statement in one parsed file."""
    out: List[Tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append((alias.name, "import"))
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = module.split(".")
                up = parts[: max(0, len(parts) - node.level)]
                base = ".".join([p for p in up if p] + ([base] if base else []))
            if base:
                # the module itself is a dependency too: `from pkg.base import helper`
                # means this file depends on pkg.base, not only on the symbol
                out.append((base, "from"))
            for alias in node.names:
                target = f"{base}.{alias.name}" if base else alias.name
                out.append((target, "from"))
    return out


def import_graph(root: Optional[str] = None) -> Dict[str, Any]:
    """Which module imports which, from the real import statements.

    Both the direct target (`src.agent.brain`) and its root package (`src`) are
    recorded, so `blast_radius` can count the modules that depend on a file even
    when the import is written as `from src.agent import brain`.
    """
    root = root or REPO_ROOT
    edges: Set[Tuple[str, str, str]] = set()
    nodes: Set[str] = set()
    own_modules: Set[str] = set()
    unparsed: List[str] = []
    for path in _iter_py_files(root):
        module = module_name(path, root)
        nodes.add(module)
        own_modules.add(module)
        try:
            with open(path, encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
        except (OSError, SyntaxError, ValueError):
            unparsed.append(module)
            continue
        for target, kind in _imports(tree, module):
            if target.startswith("."):
                continue
            nodes.add(target)
            edges.add((module, target, kind))
            root_pkg = target.split(".")[0]
            if root_pkg != target:
                edges.add((module, root_pkg, "root-of"))

    ordered = sorted(edges)
    fan_in: Dict[str, int] = {}
    for _, target, kind in ordered:
        if kind == "root-of":
            continue
        fan_in[target] = fan_in.get(target, 0) + 1
    return {
        "nodes": sorted(nodes),
        "module_count": len(own_modules),   # modules that really live in this root
        "edges": [list(edge) for edge in ordered],
        "fan_in": dict(sorted(fan_in.items(), key=lambda kv: -kv[1])[:20]),
        "cycles": _cycles(ordered),
        "unparsed": unparsed,
    }


def _cycles(edges: List[Tuple[str, str, str]], limit: int = 5) -> List[List[str]]:
    """Import cycles among the repository's own modules (depth-first, bounded)."""
    adjacency: Dict[str, List[str]] = {}
    for src, dst, kind in edges:
        if kind == "root-of":
            continue
        adjacency.setdefault(src, []).append(dst)

    found: List[List[str]] = []
    seen: Set[Tuple[str, ...]] = set()
    stack: List[str] = []
    state: Dict[str, int] = {}

    def walk(node: str) -> None:
        if len(found) >= limit:
            return
        state[node] = 1
        stack.append(node)
        for nxt in adjacency.get(node, []):
            if state.get(nxt) == 1:
                cycle = stack[stack.index(nxt):]
                key = tuple(cycle)
                if len(cycle) > 1 and key not in seen:
                    seen.add(key)
                    found.append(list(cycle))
            elif state.get(nxt, 0) == 0:
                walk(nxt)
        stack.pop()
        state[node] = 2

    for node in sorted(adjacency):
        if state.get(node, 0) == 0:
            walk(node)
    return found


def symbol_index(root: Optional[str] = None, limit: int = 1500) -> Dict[str, Any]:
    """Every top-level and class-level definition, with the line it starts on."""
    root = root or REPO_ROOT
    symbols: List[Dict[str, Any]] = []
    by_module: Dict[str, List[str]] = {}
    for path in _iter_py_files(root):
        module = module_name(path, root)
        try:
            with open(path, encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                kind = "class" if isinstance(node, ast.ClassDef) else "function"
                if len(symbols) < limit:
                    symbols.append({"module": module, "name": node.name,
                                    "kind": kind, "line": node.lineno})
                by_module.setdefault(module, []).append(node.name)
    return {"symbols": symbols, "by_module": by_module, "count": len(symbols)}


_IDENTIFIER = ast.Name


def touched_symbols(source: str) -> List[str]:
    """Names a block of Python source defines or calls - parses, never executes."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    names: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, _IDENTIFIER):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return sorted(names)


def diff_touch(patch: str) -> Dict[str, Any]:
    """What a proposed patch would touch, read straight out of the diff text.

    Added and removed lines are parsed as Python where they parse; anything else
    contributes the dotted names it mentions. Nothing is applied - this is how the
    counterfactual engine predicts a change's footprint before running it.
    """
    added: List[str] = []
    removed: List[str] = []
    files: List[str] = []
    for line in (patch or "").splitlines():
        if line.startswith("+++") or line.startswith("---"):
            # `--- a/pkg/x.py` / `+++ b/pkg/x.py`: the a/ b/ prefixes are the diff's,
            # not the repository's, so they are stripped before the path is resolved.
            target = line[3:].strip().split("\t", 1)[0]
            if target.startswith(("a/", "b/")):
                target = target[2:]
            if target and target != "/dev/null" and target not in files:
                files.append(target)
        elif line.startswith("+"):
            added.append(line[1:])
        elif line.startswith("-"):
            removed.append(line[1:])

    changed = "\n".join(added + removed)
    names = touched_symbols(changed)
    if not names:
        for token in changed.replace("(", " ").replace(")", " ").split():
            cleaned = token.strip(":,.=\"'")
            if cleaned and (cleaned.isidentifier() or "." in cleaned):
                names.append(cleaned.split(".")[-1])
    return {
        "files": files,
        "added_lines": len(added),
        "removed_lines": len(removed),
        "touched": sorted(set(names))[:60],
    }


def blast_radius(modules: List[str], graph: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """How many modules depend on the given ones, directly or transitively."""
    graph = graph or import_graph()
    dependents: Set[str] = set()
    frontier = set(modules)
    for _ in range(len(graph["nodes"]) + 1):
        grown: Set[str] = set()
        for src, dst, kind in graph["edges"]:
            if kind == "root-of":
                continue
            if dst in frontier and src not in frontier:
                grown.add(src)
        if not grown:
            break
        frontier |= grown
        dependents |= grown
    return {"dependents": sorted(dependents), "count": len(dependents)}


def python_source_of(path: str) -> str:
    """The file's text, or "" when it is missing or not readable."""
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""
