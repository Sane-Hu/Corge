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
        ("ctrl+s", "approve", "Approve"),
        ("ctrl+t", "toggle_diff", "Toggle Diff"),
        ("ctrl+g", "copy_right", "Copy Proposed"),
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
        override_diff_text: str | None = None,
        right_read_only: bool = False,
        diff_title: str = "Diff vs Original Draft",
        start_showing_diff: bool = False,
    ) -> None:
        super().__init__()
        self._left_title = left_title
        self._left_text = left_text
        self._right_title = right_title
        self._right_text = right_text
        self._prompt_text = prompt_text
        self._approve_text = approve_text
        self._reject_text = reject_text
        self._override_diff_text = override_diff_text
        self._original_right_text = right_text
        self._showing_diff = start_showing_diff
        self._diff_title = diff_title

        self.left_area = TextArea(self._left_text, id="left_area", read_only=True)
        self.diff_log = RichLog(id="diff_log", highlight=True, markup=True)
        self.diff_log.styles.display = "none"
        self.right_area = TextArea(self._right_text, id="right_area", read_only=right_read_only)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="panes"):
            with Vertical(classes="pane"):
                self.left_title_widget = Static(self._left_title, classes="pane-title")
                yield self.left_title_widget
                yield self.left_area
                yield self.diff_log
            with Vertical(classes="pane"):
                yield Static(self._right_title, classes="pane-title")
                yield self.right_area
        with Vertical(classes="footer"):
            yield Static(self._prompt_text, classes="footer-prompt")
            with Horizontal(classes="footer-buttons"):
                yield Button(
                    f"{self._approve_text} (ctrl+s)",
                    id="approve",
                    variant="success",
                )
                yield Button(
                    "Toggle Diff (ctrl+t)",
                    id="toggle_diff",
                    variant="default",
                )
                yield Button(
                    f"{self._reject_text} (esc)",
                    id="reject",
                    variant="error",
                )
        yield Footer()

    def action_approve(self) -> None:
        self.dismiss(self.right_area.text)

    def action_reject(self) -> None:
        self.dismiss(None)

    def action_copy_right(self) -> None:
        self.app.copy_to_clipboard(self.right_area.text)
        self.notify("Copied proposed content to clipboard!")

    def action_toggle_diff(self) -> None:
        self._showing_diff = not self._showing_diff
        if self._showing_diff:
            self.left_area.styles.display = "none"
            self.diff_log.styles.display = "block"
            self.left_title_widget.update(
                f"{self._diff_title} [dim](ctrl+t to hide diff)[/dim]"
            )
            self.update_diff()
        else:
            self.diff_log.styles.display = "none"
            self.left_area.styles.display = "block"
            self.left_title_widget.update(self._left_title)

    def on_mount(self) -> None:
        self._bindings.bind("escape", "reject", self._reject_text)
        if self._showing_diff:
            self.left_area.styles.display = "none"
            self.diff_log.styles.display = "block"
            self.left_title_widget.update(
                f"{self._diff_title} [dim](ctrl+t to hide diff)[/dim]"
            )
        self.update_diff()
        if not self.right_area.read_only:
            self.right_area.focus()
        else:
            if self._showing_diff:
                self.diff_log.focus()
            else:
                self.left_area.focus()

    @on(TextArea.Changed, "#right_area")
    def update_diff(self) -> None:
        if not self._showing_diff:
            return

        if self._override_diff_text is not None:
            self.diff_log.clear()
            self.diff_log.write(
                Syntax(
                    self._override_diff_text, "diff", theme="monokai", word_wrap=True
                )
            )
            return

        left_lines = self.left_area.text.splitlines(keepends=True)
        right_lines = self.right_area.text.splitlines(keepends=True)
        diff = "".join(
            difflib.unified_diff(
                left_lines,
                right_lines,
                fromfile=self._left_title,
                tofile=self._right_title,
                n=3,
            )
        )
        self.diff_log.clear()
        if not diff.strip():
            self.diff_log.write("No differences.")
        else:
            self.diff_log.write(Syntax(diff, "diff", theme="monokai", word_wrap=True))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "approve":
            self.dismiss(self.right_area.text)
        elif event.button.id == "reject":
            self.dismiss(None)
        elif event.button.id == "toggle_diff":
            self.action_toggle_diff()
