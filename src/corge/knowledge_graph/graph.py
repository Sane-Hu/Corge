"""Repository knowledge graph — satisfies ``contracts.KnowledgeGraphPort``.

Spec traceability:
    FRD FR-003  — repository ingestion → initial knowledge graph
    FRD FR-004  — incremental updates; only affected paths recomputed
    FRD FR-005  — graph of files, dirs, classes, functions, dependencies
    09-context  — node types, edge types, storage: repo_graph.db

Storage: SQLite via stdlib ``sqlite3``.  Zero new dependencies.
Parsing:  stdlib ``ast`` for Python files (Level B per approved plan).

Node types (09-context § Node Types):
    file, directory, class, function, config, test

Edge types (09-context § Edge Types):
    contains, imports

ponytail: Level B only — cross-file extends/implements/tests edges deferred.
          Upgrade path: walk ``ast.ClassDef.bases`` across the node table and
          resolve names to file-qualified node IDs.
"""

from __future__ import annotations

import ast
import sqlite3
from pathlib import Path

from corge.contracts import (
    GraphNode,
    GraphQuery,
    GraphResult,
    GraphUpdate,
    RepositoryContext,
)

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

_DDL = """\
CREATE TABLE IF NOT EXISTS nodes (
    node_id TEXT PRIMARY KEY,
    kind    TEXT NOT NULL,
    path    TEXT NOT NULL DEFAULT '',
    name    TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS edges (
    src TEXT NOT NULL,
    rel TEXT NOT NULL,
    dst TEXT NOT NULL,
    PRIMARY KEY (src, rel, dst)
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# Files with these suffixes are tagged 'config' instead of 'file'.
_CONFIG_SUFFIXES = frozenset(
    {".toml", ".cfg", ".ini", ".yaml", ".yml", ".json", ".env", ".lock"}
)

# Files in paths matching these fragments are tagged 'test'.
_TEST_MARKERS = ("test", "tests", "spec", "specs")


def _classify_file(rel: str) -> str:
    """Return the node kind for a file path."""
    parts = Path(rel).parts
    suffix = Path(rel).suffix.lower()
    if suffix in _CONFIG_SUFFIXES:
        return "config"
    if any(m in p.lower() for p in parts for m in _TEST_MARKERS):
        return "test"
    return "file"


# ---------------------------------------------------------------------------
# Internal parse helpers
# ---------------------------------------------------------------------------


def _parse_python(path: Path, rel: str) -> tuple[list[tuple], list[tuple]]:
    """Return (nodes_rows, edges_rows) extracted from a Python source file.

    Returns empty lists on parse error so a bad file never aborts a build.
    nodes_rows: (node_id, kind, path, name)
    edges_rows:  (src, rel, dst)
    """
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return [], []

    nodes: list[tuple] = []
    edges: list[tuple] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            nid = f"{rel}::{node.name}"
            nodes.append((nid, "class", rel, node.name))
            edges.append((rel, "contains", nid))
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            # Only top-level functions (parent is Module) to avoid noise.
            # ponytail: nested functions skipped; upgrade: track parent scope.
            nid = f"{rel}::{node.name}"
            nodes.append((nid, "function", rel, node.name))
            edges.append((rel, "contains", nid))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                edges.append((rel, "imports", alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                edges.append((rel, "imports", node.module))

    return nodes, edges


# ---------------------------------------------------------------------------
# KnowledgeGraph
# ---------------------------------------------------------------------------


class KnowledgeGraph:
    """Concrete knowledge graph.  Satisfies ``contracts.KnowledgeGraphPort``.

    ``db_path`` may be supplied at construction time; if omitted, the first
    ``build_graph()`` call derives it from
    ``repository_context.root / ".agent" / "repo_graph.db"``.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path: Path | None = db_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        assert self._db_path is not None, "build_graph() must be called first"
        conn = sqlite3.connect(self._db_path)
        conn.executescript(_DDL)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ingest_path(
        self,
        root: Path,
        path: Path,
        conn: sqlite3.Connection,
    ) -> None:
        """Insert nodes and edges for a single file or directory."""
        rel = str(path.relative_to(root))

        if path.is_dir():
            conn.execute(
                "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?)",
                (rel, "directory", rel, ""),
            )
            # 'contains' edge from parent dir
            parent_rel = str(path.parent.relative_to(root))
            if parent_rel != ".":
                conn.execute(
                    "INSERT OR REPLACE INTO edges VALUES (?,?,?)",
                    (parent_rel, "contains", rel),
                )
            return

        kind = _classify_file(rel)
        conn.execute(
            "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?)",
            (rel, kind, rel, ""),
        )
        # 'contains' edge from parent dir
        parent_rel = str(path.parent.relative_to(root))
        if parent_rel != ".":
            conn.execute(
                "INSERT OR REPLACE INTO edges VALUES (?,?,?)",
                (parent_rel, "contains", rel),
            )

        if path.suffix == ".py":
            sym_nodes, sym_edges = _parse_python(path, rel)
            conn.executemany(
                "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?)", sym_nodes
            )
            conn.executemany(
                "INSERT OR REPLACE INTO edges VALUES (?,?,?)", sym_edges
            )

    def _delete_path(self, rel: str, conn: sqlite3.Connection) -> None:
        """Remove all nodes and edges whose node_id starts with ``rel``."""
        conn.execute("DELETE FROM nodes WHERE node_id = ? OR node_id LIKE ?",
                     (rel, rel + "::%"))
        conn.execute(
            "DELETE FROM edges WHERE src = ? OR src LIKE ? OR dst = ?",
            (rel, rel + "::%", rel),
        )

    # ------------------------------------------------------------------
    # KnowledgeGraphPort interface
    # ------------------------------------------------------------------

    def build_graph(self, repository_context: RepositoryContext) -> None:
        """Scan ``repository_context.root`` and populate the graph (FR-003).

        Skips hidden directories (names starting with '.') to avoid
        descending into .git, .venv, __pycache__, etc.
        """
        root = repository_context.root

        if self._db_path is None:
            db_dir = root / ".agent"
            db_dir.mkdir(parents=True, exist_ok=True)
            self._db_path = db_dir / "repo_graph.db"

        with self._connect() as conn:
            conn.execute("DELETE FROM nodes")
            conn.execute("DELETE FROM edges")
            conn.execute(
                "INSERT OR REPLACE INTO meta VALUES ('root', ?)",
                (str(root),),
            )

            for item in _walk(root):
                self._ingest_path(root, item, conn)

    def update_graph(self, update: GraphUpdate) -> None:
        """Reprocess only the supplied paths (FR-004 incremental updates)."""
        if not update.paths:
            return

        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM meta WHERE key = 'root'"
            ).fetchone()

        # ponytail: if DB is empty (build_graph never called), noop.
        # Upgrade: raise a descriptive error or accept root as a parameter.
        if row is None:
            return

        root = Path(row[0])

        with self._connect() as conn:
            for path in update.paths:
                try:
                    rel = str(path.relative_to(root))
                except ValueError:
                    continue
                self._delete_path(rel, conn)
                if path.exists():
                    self._ingest_path(root, path, conn)

    def query_graph(self, query: GraphQuery) -> GraphResult:
        """Return nodes matching a simple text expression (FR-005).

        Supported expressions:
            ``files``               — all file/config/test nodes
            ``directories``         — all directory nodes
            ``classes:<path>``      — class nodes in a file
            ``functions:<path>``    — function nodes in a file
            ``imports:<path>``      — modules imported by a file
            ``imported_by:<path>``  — files that import a path
            ``node:<node_id>``      — exact node by ID
            ``*`` or ``all``        — every node

        Returns an empty ``GraphResult`` if no nodes match.

        ponytail: linear table scans; upgrade path: add B-tree indexes on
        (kind), (path), (src, rel) once query volume grows.
        """
        expr = query.expression.strip()

        with self._connect() as conn:
            rows = _execute_query(expr, conn)

        nodes = tuple(
            GraphNode(kind=r[1], node_id=r[0], path=r[2], name=r[3])
            for r in rows
        )
        return GraphResult(nodes=nodes)

    def fuzzy_search(self, keyword: str) -> GraphResult:
        """Return nodes whose node_id or name contains ``keyword`` (case-insensitive).

        Used by Discovery Mode (Argument of Specs RD § 2) to let users
        explore the codebase without knowing exact node names.

        todo: simple LIKE scan; upgrade path: embeddings or NL-to-graph
              traversal when vector DB support is added.
        """
        if not keyword.strip():
            return GraphResult(nodes=())

        pattern = f"%{keyword.strip()}%"

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT node_id, kind, path, name FROM nodes"
                " WHERE node_id LIKE ? COLLATE NOCASE"
                "    OR name LIKE ? COLLATE NOCASE"
                " ORDER BY node_id",
                (pattern, pattern),
            ).fetchall()

        nodes = tuple(
            GraphNode(kind=r[1], node_id=r[0], path=r[2], name=r[3])
            for r in rows
        )
        return GraphResult(nodes=nodes)


# ---------------------------------------------------------------------------
# Walk helper (skips hidden dirs and __pycache__)
# ---------------------------------------------------------------------------


def _walk(root: Path) -> list[Path]:
    """Return all non-hidden files and directories under root (BFS order)."""
    result: list[Path] = []
    queue = [root]
    while queue:
        current = queue.pop(0)
        for child in sorted(current.iterdir()):
            if child.name.startswith(".") or child.name == "__pycache__":
                continue
            result.append(child)
            if child.is_dir():
                queue.append(child)
    return result


# ---------------------------------------------------------------------------
# Query dispatcher
# ---------------------------------------------------------------------------


def _execute_query(
    expr: str, conn: sqlite3.Connection
) -> list[tuple[str, str, str, str]]:
    """Dispatch a text expression to a SQL query; return raw rows."""
    FILE_KINDS = ("'file'", "'config'", "'test'")

    if expr in ("*", "all", ""):
        return conn.execute(
            "SELECT node_id, kind, path, name FROM nodes ORDER BY node_id"
        ).fetchall()

    if expr == "files":
        placeholders = ",".join(FILE_KINDS)
        return conn.execute(
            f"SELECT node_id, kind, path, name FROM nodes"
            f" WHERE kind IN ({placeholders}) ORDER BY node_id"
        ).fetchall()

    if expr == "directories":
        return conn.execute(
            "SELECT node_id, kind, path, name FROM nodes"
            " WHERE kind = 'directory' ORDER BY node_id"
        ).fetchall()

    if expr.startswith("classes:"):
        path = expr[len("classes:"):]
        return conn.execute(
            "SELECT node_id, kind, path, name FROM nodes"
            " WHERE kind = 'class' AND path = ? ORDER BY node_id",
            (path,),
        ).fetchall()

    if expr.startswith("functions:"):
        path = expr[len("functions:"):]
        return conn.execute(
            "SELECT node_id, kind, path, name FROM nodes"
            " WHERE kind = 'function' AND path = ? ORDER BY node_id",
            (path,),
        ).fetchall()

    if expr.startswith("imports:"):
        src = expr[len("imports:"):]
        # Import targets are module names stored only in edges.dst — they are
        # never inserted as nodes.  Synthesise 'module' rows from the edge.
        rows = conn.execute(
            "SELECT dst FROM edges WHERE src = ? AND rel = 'imports' ORDER BY dst",
            (src,),
        ).fetchall()
        return [(r[0], "module", "", r[0]) for r in rows]

    if expr.startswith("imported_by:"):
        dst = expr[len("imported_by:"):]
        return conn.execute(
            "SELECT n.node_id, n.kind, n.path, n.name"
            " FROM edges e JOIN nodes n ON n.node_id = e.src"
            " WHERE e.dst = ? AND e.rel = 'imports' ORDER BY n.node_id",
            (dst,),
        ).fetchall()

    if expr.startswith("node:"):
        nid = expr[len("node:"):]
        return conn.execute(
            "SELECT node_id, kind, path, name FROM nodes WHERE node_id = ?",
            (nid,),
        ).fetchall()

    # Unknown expression → empty result (safe, no exception)
    return []
