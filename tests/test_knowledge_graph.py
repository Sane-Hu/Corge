"""Behavioural tests for the knowledge_graph module.

Spec traceability:
    FRD FR-003  — build_graph() produces nodes for files, dirs, classes,
                  functions and edges for imports
    FRD FR-004  — update_graph() reprocesses only affected paths
    FRD FR-005  — query_graph() is queryable; returns GraphResult

Self-contained: uses only stdlib (tmp_path fixture from pytest) and the
project's own contracts.  No test frameworks beyond pytest.
"""

from pathlib import Path

import pytest

from corge.contracts import (
    GraphNode,
    GraphQuery,
    GraphResult,
    GraphUpdate,
    RepositoryContext,
)
from corge.knowledge_graph import KnowledgeGraph

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repo(tmp_path: Path) -> Path:
    """Write a minimal fake Python repo under tmp_path and return root."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "src").mkdir()
    (root / "tests").mkdir()

    (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n")
    (root / "README.md").write_text("# Demo\n")

    (root / "src" / "service.py").write_text(
        "import os\nimport sys\n\nclass Greeter:\n    pass\n\ndef greet(): pass\n"
    )
    (root / "src" / "util.py").write_text(
        "from src.service import Greeter\n\ndef helper(): pass\n"
    )
    (root / "tests" / "test_service.py").write_text(
        "import pytest\nfrom src.service import Greeter\n\ndef test_greet(): pass\n"
    )
    return root


def _ids(result: GraphResult) -> set[str]:
    return {n.node_id for n in result.nodes}


def _kinds(result: GraphResult) -> dict[str, str]:
    return {n.node_id: n.kind for n in result.nodes}


# ---------------------------------------------------------------------------
# build_graph
# ---------------------------------------------------------------------------


def test_build_graph_creates_db(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))
    assert (root / ".agent" / "repo_graph.db").exists()


def test_build_graph_file_nodes(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))

    result = kg.query_graph(GraphQuery(expression="files"))
    ids = _ids(result)
    assert "src/service.py" in ids
    assert "src/util.py" in ids
    assert "README.md" in ids


def test_build_graph_config_node(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))

    result = kg.query_graph(GraphQuery(expression="*"))
    kinds = _kinds(result)
    assert kinds.get("pyproject.toml") == "config"


def test_build_graph_test_node(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))

    result = kg.query_graph(GraphQuery(expression="*"))
    kinds = _kinds(result)
    assert kinds.get("tests/test_service.py") == "test"


def test_build_graph_directory_nodes(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))

    result = kg.query_graph(GraphQuery(expression="directories"))
    ids = _ids(result)
    assert "src" in ids
    assert "tests" in ids


def test_build_graph_class_and_function_nodes(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))

    classes = kg.query_graph(GraphQuery(expression="classes:src/service.py"))
    fns = kg.query_graph(GraphQuery(expression="functions:src/service.py"))

    assert any(n.name == "Greeter" for n in classes.nodes)
    assert any(n.name == "greet" for n in fns.nodes)


def test_build_graph_imports_edges(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))

    result = kg.query_graph(GraphQuery(expression="imports:src/service.py"))
    # src/service.py: import os; import sys
    # Imported targets are synthesised as kind='module' nodes.
    imported = {n.node_id for n in result.nodes}
    assert "os" in imported
    assert "sys" in imported
    assert all(n.kind == "module" for n in result.nodes)


def test_build_graph_idempotent(tmp_path: Path) -> None:
    """Calling build_graph twice should not duplicate nodes."""
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))
    kg.build_graph(RepositoryContext(root=root))

    result = kg.query_graph(GraphQuery(expression="files"))
    service_nodes = [n for n in result.nodes if n.node_id == "src/service.py"]
    assert len(service_nodes) == 1


# ---------------------------------------------------------------------------
# update_graph
# ---------------------------------------------------------------------------


def test_update_graph_adds_new_file(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))

    new_file = root / "src" / "extra.py"
    new_file.write_text("class Extra:\n    pass\n")

    kg.update_graph(GraphUpdate(paths=(new_file,)))

    result = kg.query_graph(GraphQuery(expression="files"))
    assert "src/extra.py" in _ids(result)

    classes = kg.query_graph(GraphQuery(expression="classes:src/extra.py"))
    assert any(n.name == "Extra" for n in classes.nodes)


def test_update_graph_reflects_edit(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))

    # Edit service.py: replace Greeter with Widget
    service = root / "src" / "service.py"
    service.write_text("class Widget:\n    pass\n")
    kg.update_graph(GraphUpdate(paths=(service,)))

    classes = kg.query_graph(GraphQuery(expression="classes:src/service.py"))
    names = {n.name for n in classes.nodes}
    assert "Widget" in names
    assert "Greeter" not in names


def test_update_graph_does_not_touch_unrelated(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))

    service = root / "src" / "service.py"
    service.write_text("# emptied\n")
    kg.update_graph(GraphUpdate(paths=(service,)))

    # util.py should still be present
    result = kg.query_graph(GraphQuery(expression="files"))
    assert "src/util.py" in _ids(result)


def test_update_graph_empty_paths_is_noop(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))

    before = _ids(kg.query_graph(GraphQuery(expression="files")))
    kg.update_graph(GraphUpdate(paths=()))
    after = _ids(kg.query_graph(GraphQuery(expression="files")))
    assert before == after


# ---------------------------------------------------------------------------
# query_graph — expression variants
# ---------------------------------------------------------------------------


def test_query_all(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))

    result_star = kg.query_graph(GraphQuery(expression="*"))
    result_all = kg.query_graph(GraphQuery(expression="all"))
    assert _ids(result_star) == _ids(result_all)
    assert len(result_star.nodes) > 0


def test_query_imported_by(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))

    # src/util.py does 'from src.service import Greeter' → edge dst = 'src.service'
    result = kg.query_graph(GraphQuery(expression="imported_by:src.service"))
    ids = _ids(result)
    assert "src/util.py" in ids


def test_query_node_exact(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))

    result = kg.query_graph(GraphQuery(expression="node:src/service.py"))
    assert len(result.nodes) == 1
    assert result.nodes[0].node_id == "src/service.py"
    assert result.nodes[0].kind == "file"


def test_query_unknown_expression_returns_empty(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    kg = KnowledgeGraph()
    kg.build_graph(RepositoryContext(root=root))

    result = kg.query_graph(GraphQuery(expression="nonexistent_expression"))
    assert result.nodes == ()


# ---------------------------------------------------------------------------
# GraphResult / GraphNode contract
# ---------------------------------------------------------------------------


def test_graph_result_is_frozen() -> None:
    node = GraphNode(kind="file", node_id="a.py", path="a.py", name="")
    result = GraphResult(nodes=(node,))
    with pytest.raises(AttributeError):
        result.nodes = ()  # type: ignore[misc]


def test_graph_node_defaults() -> None:
    node = GraphNode(kind="directory", node_id="src")
    assert node.path == ""
    assert node.name == ""


# ---------------------------------------------------------------------------
# custom db_path
# ---------------------------------------------------------------------------


def test_custom_db_path(tmp_path: Path) -> None:
    root = _make_repo(tmp_path)
    db = tmp_path / "custom.db"
    kg = KnowledgeGraph(db_path=db)
    kg.build_graph(RepositoryContext(root=root))
    assert db.exists()
    result = kg.query_graph(GraphQuery(expression="files"))
    assert len(result.nodes) > 0
