"""Interactive side-by-side diff component for textual UI."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Static, TextArea


class InteractiveDiffScreen(Screen):
    """Side-by-side diff for review and override."""
    
    CSS = """
    InteractiveDiffScreen {
        layout: vertical;
    }
    .panes {
        height: 1fr;
    }
    .pane {
        width: 1fr;
        height: 1fr;
        border: solid green;
        margin: 1;
    }
    .pane-title {
        text-align: center;
        background: $boost;
        color: $text;
        text-style: bold;
    }
    .footer {
        height: 3;
        align: center middle;
    }
    """

    def __init__(
        self,
        left_title: str,
        left_text: str,
        right_title: str,
        right_text: str,
        prompt_text: str = "Review and edit if needed. Click Approve to continue.",
    ) -> None:
        super().__init__()
        self._left_title = left_title
        self._left_text = left_text
        self._right_title = right_title
        self._right_text = right_text
        self._prompt_text = prompt_text

    def compose(self) -> ComposeResult:
        with Horizontal(classes="panes"):
            with Vertical(classes="pane"):
                yield Static(self._left_title, classes="pane-title")
                yield TextArea(self._left_text, read_only=True)
            with Vertical(classes="pane"):
                yield Static(self._right_title, classes="pane-title")
                self.right_area = TextArea(self._right_text)
                yield self.right_area
        with Horizontal(classes="footer"):
            yield Static(self._prompt_text + "  ")
            yield Button("Approve", id="approve", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "approve":
            self.dismiss(self.right_area.text)
