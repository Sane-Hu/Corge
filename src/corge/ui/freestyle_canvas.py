"""Freestyle canvas component for the Textual UI.

Spec traceability:
    Tech-spec §5 §CanvasScreen — TextArea + Submit, CANVAS_FREESTYLE sub-state
    FR-018 — sticky notes with live graph validation, semantic gap blocking
    Review finding 8.4 — ghost/placeholder guidance text
    Review finding 8.8 — sticky note support with KG node validation
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static, TextArea

from corge.contracts import (
    GraphQuery,
    KnowledgeGraphPort,
    StickyNote,
    StickyNoteStatus,
)

# Ghost text shown in the canvas before the user starts typing.
# Per review finding 8.4: guides brainstorming without being prescriptive.
_GHOST_TEXT = """\
# Freestyle Canvas — Brainstorming Space
# (Replace this text with your own — nothing is too rough here)
#
# Think about:
#   • What is the feature or change you need?          (business goal)
#   • Who benefits from it and how?                    (user story)
#   • What must the system do differently?             (functional requirements)
#   • What should NOT be changed or broken?            (constraints)
#   • How will you know it works?                      (acceptance criteria)
#   • What tests are required?                         (testing expectations)
#
# You can also anchor sticky notes to Knowledge Graph nodes:
#   @node:<node_id>  your note text here
#   e.g. @node:src/corge/agent/coding_agent.py  needs to handle EDIT actions
"""


class CanvasScreen(Screen[str]):
    """Freestyle brainstorming canvas (CANVAS_FREESTYLE sub-state).

    Provides:
    - Ghost text guidance for first-time users (finding 8.4)
    - TextArea for raw free-form brainstorming
    - Sticky note parsing with live KG node validation (FR-018)
    - Submit button that dismisses with the canvas text
    """

    CSS = """
    CanvasScreen {
        layout: vertical;
    }
    .canvas-container {
        width: 100%;
        height: 1fr;
        border: round $accent;
        padding: 1 2;
        margin: 1 2;
    }
    .canvas-header {
        text-align: center;
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }
    .sticky-panel {
        height: 8;
        border: round $warning;
        padding: 0 1;
        margin: 0 2;
        overflow-y: auto;
    }
    .sticky-title {
        color: $warning;
        text-style: bold;
    }
    .sticky-valid {
        color: $success;
    }
    .sticky-invalid {
        color: $error;
    }
    .footer {
        height: 3;
        align: center middle;
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        knowledge_graph: KnowledgeGraphPort | None = None,
        initial_text: str = "",
    ) -> None:
        super().__init__()
        self._kg = knowledge_graph
        self._initial_text = initial_text or _GHOST_TEXT
        self._sticky_notes: list[StickyNote] = []

    def compose(self) -> ComposeResult:
        with Vertical(classes="canvas-container"):
            yield Static("Freestyle Canvas — Brainstorming", classes="canvas-header")
            self._text_area = TextArea(self._initial_text)
            yield self._text_area
        with Vertical(classes="sticky-panel"):
            yield Static(
                "Anchored Sticky Notes (@node:<id> ...)", classes="sticky-title"
            )
            self._sticky_label = Label("None detected yet.", id="sticky-status")
            yield self._sticky_label
        with Horizontal(classes="footer"):
            yield Button("Submit to Concretization", id="submit", variant="primary")

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Re-parse sticky notes and validate them against the KG on every edit."""
        self._sticky_notes = self._parse_sticky_notes(event.text_area.text)
        self._refresh_sticky_display()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            self.dismiss(self._text_area.text)

    # ------------------------------------------------------------------
    # Sticky note parsing and KG validation (FR-018)
    # ------------------------------------------------------------------

    def _parse_sticky_notes(self, text: str) -> list[StickyNote]:
        """Extract @node:<id> sticky notes from canvas text.

        Format: @node:<node_id>  <note text>
        The node_id is the graph node's stable identifier
        (e.g. "src/corge/agent/coding_agent.py" or
        "src/corge/agent/coding_agent.py::CodingAgent").
        """
        notes: list[StickyNote] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("@node:"):
                continue
            rest = stripped[len("@node:"):]
            # node_id ends at the first double-space or tab
            parts = rest.split(None, 1)
            if not parts:
                continue
            node_id = parts[0]
            content = parts[1].strip() if len(parts) > 1 else ""
            status = self._validate_node(node_id)
            notes.append(StickyNote(node_id=node_id, content=content, status=status))
        return notes

    def _validate_node(self, node_id: str) -> StickyNoteStatus:
        """Check if a node_id exists in the Knowledge Graph."""
        if self._kg is None:
            return StickyNoteStatus.ACTIVE  # no KG available — optimistic
        try:
            result = self._kg.query_graph(GraphQuery(expression=f"node:{node_id}"))
            return (
                StickyNoteStatus.ACTIVE if result.nodes else StickyNoteStatus.INVALID
            )
        except Exception:
            return StickyNoteStatus.ACTIVE  # fail open

    def _refresh_sticky_display(self) -> None:
        """Update the sticky note status panel."""
        if not self._sticky_notes:
            self._sticky_label.update("None detected yet.")
            return

        lines: list[str] = []
        for note in self._sticky_notes:
            icon = "✓" if note.status == StickyNoteStatus.ACTIVE else "✗ INVALID"
            lines.append(f"[{icon}] @node:{note.node_id}  {note.content[:60]}")
        self._sticky_label.update("\n".join(lines))

    @property
    def sticky_notes(self) -> tuple[StickyNote, ...]:
        """Return the current set of parsed and validated sticky notes."""
        return tuple(self._sticky_notes)
