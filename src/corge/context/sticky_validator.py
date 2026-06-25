"""Sticky note validator service (FR-018)."""

from __future__ import annotations

from corge.contracts import GraphQuery, GraphResult, KnowledgeGraphPort, StickyNoteStatus


class StickyNoteValidator:
    """Satisfies StickyNoteValidatorPort. Delegates KG queries for node validation."""

    def __init__(self, knowledge_graph: KnowledgeGraphPort) -> None:
        self._kg = knowledge_graph

    def validate_node(self, node_id: str) -> StickyNoteStatus:
        """Check if a node_id exists in the Knowledge Graph."""
        try:
            result = self._kg.query_graph(GraphQuery(expression=f"node:{node_id}"))
            return StickyNoteStatus.ACTIVE if result.nodes else StickyNoteStatus.INVALID
        except Exception:
            return StickyNoteStatus.ACTIVE  # fail open

    def fuzzy_search(self, keyword: str) -> GraphResult:
        """Query the codebase/knowledge graph with a keyword search."""
        if hasattr(self._kg, "fuzzy_search"):
            return self._kg.fuzzy_search(keyword)
        return GraphResult(nodes=())

