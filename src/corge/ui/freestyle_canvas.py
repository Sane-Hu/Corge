"""Freestyle canvas component for the Textual UI.

Spec traceability:
    Tech-spec §5 §CanvasScreen — TextArea + Submit, CANVAS_FREESTYLE sub-state
    FR-018 — sticky notes with live graph validation, semantic gap blocking
    Review finding 8.4 — ghost/placeholder guidance text
    Review finding 8.8 — sticky note support with KG node validation
"""

from __future__ import annotations

import json
from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
    TextArea,
)

from corge.contracts import (
    StickyNote,
    StickyNoteStatus,
    StickyNoteValidatorPort,
)
from corge.ui.confirm_screen import ConfirmScreen

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
#
# Or add notes for later (backlog):
#   @later  refactor this method when database is migrated
"""


class SearchResultItem(ListItem):
    """Custom list item for search results to hold node metadata."""

    def __init__(self, node_id: str, label_text: str) -> None:
        super().__init__(Label(label_text))
        self.node_id = node_id


class BacklogItem(ListItem):
    """Custom list item for persistent backlog notes."""

    def __init__(self, note_dict: dict[str, str], label_text: str) -> None:
        super().__init__(Label(label_text))
        self.note_dict = note_dict


class CanvasScreen(Screen[str]):
    """Freestyle brainstorming canvas (CANVAS_FREESTYLE sub-state).

    Provides:
    - Ghost text guidance for first-time users (finding 8.4)
    - TextArea for raw free-form brainstorming
    - Sticky note parsing with live KG node validation (FR-018)
    - Codebase Knowledge Graph fuzzy search sidebar to prevent blind inputs
    - Persistent backlog/sticky notes loaded/saved to `.agent/sticky_notes.json`
    - Submit button that dismisses with the canvas text
    """

    BINDINGS = [
        ("ctrl+s", "submit", "Submit Canvas"),
        ("escape", "cancel", "Cancel"),
    ]

    CSS = """
    CanvasScreen {
        layout: vertical;
    }
    .main-layout {
        layout: horizontal;
        height: 1fr;
        width: 100%;
    }
    .left-column {
        width: 70%;
        height: 100%;
        border: round $accent;
        padding: 1 2;
        margin: 0 1;
    }
    .right-column {
        width: 30%;
        height: 100%;
        border: round $warning;
        padding: 1 2;
        margin: 0 1;
        overflow-y: auto;
    }
    .ghost-text {
        color: $text-muted;
        margin-bottom: 1;
    }
    .canvas-header {
        text-align: center;
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }
    .sidebar-title {
        color: $warning;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }
    .search-input {
        margin-bottom: 1;
    }
    .search-results-list {
        height: 6;
        border: solid $accent;
        background: $boost;
        margin-bottom: 1;
    }
    .draft-notes-list {
        height: 6;
        border: solid $success;
        background: $boost;
        margin-bottom: 1;
    }
    .backlog-list {
        height: 8;
        border: solid $warning;
        background: $boost;
        margin-bottom: 1;
    }
    .footer {
        height: 3;
        align: center middle;
        margin-top: 1;
        margin-bottom: 1;
    }
    .error-label {
        color: $error;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        validator: StickyNoteValidatorPort | None = None,
        initial_text: str = "",
    ) -> None:
        super().__init__()
        self._validator = validator
        self._initial_text = initial_text
        self._sticky_notes: list[StickyNote] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="main-layout"):
            with Vertical(classes="left-column"):
                yield Static("Freestyle Canvas — Brainstorming", classes="canvas-header")
                self._ghost_static = Static(_GHOST_TEXT, classes="ghost-text")
                if not self._initial_text:
                    yield self._ghost_static
                self._text_area = TextArea(self._initial_text)
                yield self._text_area
                self._error_label = Label("", id="error-message", classes="error-label")
                self._error_label.styles.display = "none"
                yield self._error_label

            with Vertical(classes="right-column"):
                yield Static("Search Codebase (KG)", classes="sidebar-title")
                self._search_input = Input(
                    placeholder="Type to search files, classes...",
                    classes="search-input",
                    id="search-input"
                )
                yield self._search_input
                self._search_results = ListView(classes="search-results-list", id="search-results")
                yield self._search_results

                yield Static("Current Draft Notes", classes="sidebar-title")
                self._draft_notes_list = ListView(classes="draft-notes-list", id="draft-notes")
                yield self._draft_notes_list

                yield Static("Persistent Notes & Backlog", classes="sidebar-title")
                self._backlog_list = ListView(classes="backlog-list", id="backlog-list")
                yield self._backlog_list

                with Horizontal():
                    yield Button("Delete/Resolve Note", id="delete-note", variant="error")
                    yield Button("Clear All Notes", id="clear-all-notes", variant="error")

        with Horizontal(classes="footer"):
            yield Button("Submit to Concretization", id="submit", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_backlog_display()
        self._refresh_draft_notes_display()

    def action_submit(self) -> None:
        text = self._text_area.text
        self._sticky_notes = self._parse_sticky_notes(text)

        # Validation block (FR-018)
        invalid_notes = [
            n for n in self._sticky_notes if n.status == StickyNoteStatus.INVALID
        ]
        if invalid_notes and not self._is_repo_empty():
            self._error_label.update(
                f"Submission blocked: Canvas contains {len(invalid_notes)} invalid/unresolved @node tag(s)."
            )
            self._error_label.styles.display = "block"
            return

        # Save new notes to persistent store
        self._save_draft_notes_to_persistent()

        self.dismiss(text)

    def action_cancel(self) -> None:
        self.dismiss("")

    @on(Button.Pressed)
    def handle_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "delete-note":
            selected_item = self._backlog_list.highlighted_child
            if isinstance(selected_item, BacklogItem):
                self._delete_persistent_note(selected_item.note_dict)
        elif event.button.id == "clear-all-notes":
            def confirm_callback(confirmed: bool) -> None:
                if confirmed:
                    self._save_persistent_notes([])
                    self._refresh_backlog_display()
            self.app.push_screen(
                ConfirmScreen(
                    "Clear All Notes",
                    "Are you sure you want to permanently delete all persistent backlog notes? This action cannot be undone."
                ),
                confirm_callback
            )
        elif event.button.id == "submit":
            self.action_submit()

    @on(TextArea.Changed)
    def handle_text_changed(self) -> None:
        text = self._text_area.text
        if (
            text.strip()
            and hasattr(self, "_ghost_static")
            and self._ghost_static.styles.display != "none"
        ):
            self._ghost_static.styles.display = "none"
        elif not text.strip() and hasattr(self, "_ghost_static"):
            self._ghost_static.styles.display = "block"

        self._sticky_notes = self._parse_sticky_notes(text)
        self._refresh_draft_notes_display()

    @on(Input.Changed)
    def handle_search_changed(self, event: Input.Changed) -> None:
        query = event.value.strip()
        self._search_results.clear()
        if not query or not self._validator:
            return

        try:
            result = self._validator.fuzzy_search(query)
            if not result.nodes:
                if self._is_repo_empty():
                    self._search_results.append(ListItem(Label("No matches found (directory is empty).")))
                else:
                    self._search_results.append(ListItem(Label("No matches found.")))
            else:
                for node in result.nodes:
                    label = f"[{node.kind.upper()}] {node.node_id}"
                    self._search_results.append(SearchResultItem(node.node_id, label))
        except Exception:
            pass

    @on(Input.Submitted, "#search-input")
    def handle_search_submitted(self) -> None:
        if self._search_results.children:
            self._search_results.focus()

    @on(ListView.Selected)
    def handle_list_selected(self, event: ListView.Selected) -> None:
        if event.list_view == self._search_results:
            item = event.item
            if isinstance(item, SearchResultItem):
                node_tag = f"\n@node:{item.node_id} "
                self._text_area.insert_text(node_tag)
                self._text_area.focus()

    # ------------------------------------------------------------------
    # Persistence Helpers
    # ------------------------------------------------------------------

    def _is_repo_empty(self) -> bool:
        try:
            app = self.app
            repo_root = getattr(app, "target_repo", Path.cwd())
        except RuntimeError:
            repo_root = Path.cwd()

        if not repo_root.exists():
            return True
        for child in repo_root.iterdir():
            if child.name not in (".git", ".agent"):
                return False
        return True

    def _get_sticky_notes_file(self) -> Path:
        try:
            app = self.app
            repo_root = getattr(app, "target_repo", Path.cwd())
        except RuntimeError:
            repo_root = Path.cwd()
        return repo_root / ".agent" / "sticky_notes.json"

    def _load_persistent_notes(self) -> list[dict[str, str]]:
        file_path = self._get_sticky_notes_file()
        if not file_path.exists():
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        return []

    def _save_persistent_notes(self, notes: list[dict[str, str]]) -> None:
        file_path = self._get_sticky_notes_file()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(notes, f, indent=2)
        except Exception:
            pass

    def _delete_persistent_note(self, note_dict: dict[str, str]) -> None:
        notes = self._load_persistent_notes()
        updated_notes = []
        for n in notes:
            if (
                n.get("node_id") == note_dict.get("node_id")
                and n.get("content") == note_dict.get("content")
                and n.get("type") == note_dict.get("type")
            ):
                continue
            updated_notes.append(n)
        self._save_persistent_notes(updated_notes)
        self._refresh_backlog_display()

    def _save_draft_notes_to_persistent(self) -> None:
        notes = self._load_persistent_notes()
        for note in self._sticky_notes:
            note_type = "later" if not note.node_id else "active"
            exists = False
            for n in notes:
                if (
                    n.get("node_id") == note.node_id
                    and n.get("content") == note.content
                    and n.get("type") == note_type
                ):
                    exists = True
                    break
            if not exists:
                notes.append(
                    {
                        "node_id": note.node_id,
                        "content": note.content,
                        "type": note_type,
                    }
                )
        self._save_persistent_notes(notes)

    # ------------------------------------------------------------------
    # Sticky note parsing and KG validation (FR-018)
    # ------------------------------------------------------------------

    def _parse_sticky_notes(self, text: str) -> list[StickyNote]:
        """Extract sticky notes from canvas text.

        Format:
          @node:<node_id>  <note text>
          @later  <note text>
        """
        notes: list[StickyNote] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("@node:"):
                rest = stripped[len("@node:") :]
                parts = rest.split(None, 1)
                if not parts:
                    continue
                node_id = parts[0]
                content = parts[1].strip() if len(parts) > 1 else ""

                is_later = False
                if content.startswith("@later"):
                    content = content[len("@later") :].strip()
                elif content.startswith("@todo"):
                    content = content[len("@todo") :].strip()

                status = self._validate_node(node_id)
                notes.append(
                    StickyNote(node_id=node_id, content=content, status=status)
                )
            elif stripped.startswith("@later"):
                content = stripped[len("@later") :].strip()
                notes.append(
                    StickyNote(
                        node_id="", content=content, status=StickyNoteStatus.ACTIVE
                    )
                )
            elif stripped.startswith("@todo"):
                content = stripped[len("@todo") :].strip()
                notes.append(
                    StickyNote(
                        node_id="", content=content, status=StickyNoteStatus.ACTIVE
                    )
                )
        return notes

    def _validate_node(self, node_id: str) -> StickyNoteStatus:
        """Check if a node_id is valid."""
        if self._validator is None:
            return StickyNoteStatus.ACTIVE  # no validator available — optimistic
        return self._validator.validate_node(node_id)

    def _refresh_draft_notes_display(self) -> None:
        """Update the draft notes list view."""
        self._draft_notes_list.clear()
        if not self._sticky_notes:
            self._draft_notes_list.append(
                ListItem(Label("No notes in draft canvas text."))
            )
            return

        for note in self._sticky_notes:
            icon = "✓" if note.status == StickyNoteStatus.ACTIVE else "✗ INVALID"
            if note.node_id:
                label = f"[{icon}] @node:{note.node_id}  {note.content[:40]}"
            else:
                label = f"[{icon}] @later  {note.content[:40]}"
            self._draft_notes_list.append(ListItem(Label(label)))

    def _refresh_backlog_display(self) -> None:
        """Update the persistent backlog list view."""
        self._backlog_list.clear()
        persistent_notes = self._load_persistent_notes()
        if not persistent_notes:
            self._backlog_list.append(
                ListItem(Label("No persistent notes/backlog."))
            )
            return

        for note in persistent_notes:
            node_id = note.get("node_id", "")
            content = note.get("content", "")
            note_type = note.get("type", "active")

            if node_id:
                status = self._validate_node(node_id)
                status_str = (
                    "ACTIVE" if status == StickyNoteStatus.ACTIVE else "INVALID"
                )
                label = f"[{status_str}] @node:{node_id}  {content}"
            else:
                label = f"[LATER]  {content}"

            self._backlog_list.append(BacklogItem(note, label))

    @property
    def sticky_notes(self) -> tuple[StickyNote, ...]:
        """Return the current set of parsed and validated sticky notes."""
        return tuple(self._sticky_notes)
