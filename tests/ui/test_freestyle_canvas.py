"""Tests for sticky note graph invalidation (Argument of Specs RD § 2, § 4).

Spec traceability:
    Resolved Design § 2  — sticky notes maintain live graph edges
    Resolved Design § 2  — red warning icon on node deletion
"""

from pathlib import Path

import pytest

from corge.contracts import (
    CanvasSnapshot,
    GraphQuery,
    RepositoryContext,
    StickyNote,
    StickyNoteStatus,
)
from corge.knowledge_graph import KnowledgeGraph


@pytest.fixture()
def repo_with_file(tmp_path: Path) -> Path:
    """Create a minimal repo with one Python file."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "auth_service.py").write_text(
        "class AuthService:\n    pass\n", encoding="utf-8"
    )
    return tmp_path


def _validate_sticky(kg: KnowledgeGraph, note: StickyNote) -> StickyNote:
    """Check if the sticky note's node still exists in the graph."""
    result = kg.query_graph(GraphQuery(expression=f"node:{note.node_id}"))
    if not result.nodes:
        return StickyNote(
            node_id=note.node_id,
            content=note.content,
            status=StickyNoteStatus.INVALID,
        )
    return note


def test_sticky_note_active_when_node_exists(
    repo_with_file: Path, tmp_path: Path
) -> None:
    """Sticky note remains ACTIVE when its graph node exists."""
    db = tmp_path / "test.db"
    kg = KnowledgeGraph(db_path=db)
    kg.build_graph(RepositoryContext(root=repo_with_file))

    note = StickyNote(
        node_id="src/auth_service.py::AuthService",
        content="needs cache invalidation",
    )
    validated = _validate_sticky(kg, note)
    assert validated.status == StickyNoteStatus.ACTIVE


def test_sticky_note_validator_returns_active_for_unknown_node_when_no_validator() -> (
    None
):
    """CanvasScreen defaults to ACTIVE when no validator is provided."""
    from corge.ui.freestyle_canvas import CanvasScreen

    canvas = CanvasScreen(validator=None)
    assert canvas._validate_node("anything") == StickyNoteStatus.ACTIVE


def test_sticky_note_invalid_when_node_deleted(
    repo_with_file: Path, tmp_path: Path
) -> None:
    """Sticky note becomes INVALID (red flag) when its graph node is deleted."""
    db = tmp_path / "test.db"
    kg = KnowledgeGraph(db_path=db)
    kg.build_graph(RepositoryContext(root=repo_with_file))

    note = StickyNote(
        node_id="src/auth_service.py::AuthService",
        content="needs cache invalidation",
    )

    # Delete the file, triggering a graph update
    (repo_with_file / "src" / "auth_service.py").unlink()
    from corge.contracts import GraphUpdate

    kg.update_graph(GraphUpdate(paths=(repo_with_file / "src" / "auth_service.py",)))

    validated = _validate_sticky(kg, note)
    assert validated.status == StickyNoteStatus.INVALID


def test_canvas_snapshot_is_immutable() -> None:
    """Canvas snapshots are frozen dataclasses."""
    snap = CanvasSnapshot(text="brainstorm", timestamp="2026-06-20T12:00:00Z")
    with pytest.raises(AttributeError):
        snap.text = "changed"  # type: ignore[misc]


def test_canvas_snapshot_concretized_ranges() -> None:
    """Canvas tracks which lines the agent concretized."""
    snap = CanvasSnapshot(
        text="line1\nline2\nline3",
        timestamp="2026-06-20T12:00:00Z",
        concretized_ranges=((0, 1),),
    )
    assert snap.concretized_ranges == ((0, 1),)


def test_fuzzy_search_finds_partial_match(repo_with_file: Path, tmp_path: Path) -> None:
    """Discovery mode fuzzy search finds nodes by partial keyword."""
    db = tmp_path / "test.db"
    kg = KnowledgeGraph(db_path=db)
    kg.build_graph(RepositoryContext(root=repo_with_file))

    result = kg.fuzzy_search("auth_serv")
    node_ids = [n.node_id for n in result.nodes]
    assert any("auth_service" in nid for nid in node_ids)


def test_fuzzy_search_empty_keyword_returns_nothing(
    repo_with_file: Path, tmp_path: Path
) -> None:
    """Fuzzy search with empty keyword returns no results."""
    db = tmp_path / "test.db"
    kg = KnowledgeGraph(db_path=db)
    kg.build_graph(RepositoryContext(root=repo_with_file))

    result = kg.fuzzy_search("")
    assert len(result.nodes) == 0
