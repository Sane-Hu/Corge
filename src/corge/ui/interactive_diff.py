"""Interactive side-by-side diff component for textual UI."""

import difflib

from rich.syntax import Syntax
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, RichLog, Static, TextArea


class InteractiveDiffScreen(Screen[str | None]):
    """Side-by-side diff for review and override."""

    BINDINGS = [
        ("ctrl+a", "approve", "Approve"),
        ("escape", "reject", "Reject"),
    ]

    CSS = """
    InteractiveDiffScreen {
        layout: vertical;
    }
    .panes {
        height: 1fr;
        margin: 1 2;
    }
    .pane {
        width: 1fr;
        height: 1fr;
        border: round $primary;
        padding: 1;
        margin: 0 1;
    }
    .pane-title {
        text-align: center;
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }
    .footer {
        height: auto;
        min-height: 4;
        align: center middle;
        margin-bottom: 1;
    }
    .footer-buttons {
        height: auto;
        align: center middle;
    }
    .footer-prompt {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        left_title: str,
        left_text: str,
        right_title: str,
        right_text: str,
        prompt_text: str = "Review and edit if needed. Click Approve to continue.",
        approve_text: str = "Approve",
        reject_text: str = "Reject",
    ) -> None:
        super().__init__()
        self._left_title = left_title
        self._left_text = left_text
        self._right_title = right_title
        self._right_text = right_text
        self._prompt_text = prompt_text
        self._approve_text = approve_text
        self._reject_text = reject_text
        self.left_log = RichLog(id="left_log", highlight=True, markup=True)
        self.right_area = TextArea(self._right_text, id="right_area")

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="panes"):
            with Vertical(classes="pane"):
                yield Static(f"Diff vs {self._left_title}", classes="pane-title")
                yield self.left_log
            with Vertical(classes="pane"):
                yield Static(self._right_title, classes="pane-title")
                yield self.right_area
        with Vertical(classes="footer"):
            yield Static(self._prompt_text, classes="footer-prompt")
            with Horizontal(classes="footer-buttons"):
                yield Button(self._approve_text, id="approve", variant="success")
                yield Button(self._reject_text, id="reject", variant="error")
        yield Footer()

    def action_approve(self) -> None:
        self.dismiss(self.right_area.text)

    def action_reject(self) -> None:
        self.dismiss(None)

    def on_mount(self) -> None:
        self.update_diff()

    @on(TextArea.Changed, "#right_area")
    def update_diff(self) -> None:
        left_lines = self._left_text.splitlines(keepends=True)
        right_lines = self.right_area.text.splitlines(keepends=True)
        diff = "".join(
            difflib.unified_diff(
                left_lines,
                right_lines,
                fromfile="Original",
                tofile="Proposed",
                n=3,
            )
        )
        self.left_log.clear()
        if not diff.strip():
            self.left_log.write("No differences.")
        else:
            self.left_log.write(Syntax(diff, "diff", theme="monokai", word_wrap=True))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "approve":
            self.dismiss(self.right_area.text)
        elif event.button.id == "reject":
            self.dismiss(None)
