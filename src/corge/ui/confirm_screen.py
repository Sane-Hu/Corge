"""Confirmation dialog screen for Textual TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static, TextArea


class ConfirmScreen(Screen[bool]):
    """Generic confirmation dialog returning True (Yes) or False (No)."""

    BINDINGS = [
        ("y", "yes", "Yes"),
        ("n", "no", "No"),
        ("escape", "no", "No"),
    ]

    CSS = """
    ConfirmScreen {
        align: center middle;
    }
    ConfirmScreen > Vertical {
        width: 80%;
        height: auto;
        border: round $primary;
        padding: 1 2;
        background: #2b0630;
    }
    .title {
        text-align: center;
        text-style: bold;
        color: #e886fa;
        margin-bottom: 1;
    }
    .footer-buttons {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    .footer-buttons Button {
        margin: 0 2;
    }
    """

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static(self._title, classes="title")
            yield TextArea(self._message, read_only=True)
            with Horizontal(classes="footer-buttons"):
                yield Button("Yes (y)", id="yes", variant="success")
                yield Button("No (n/esc)", id="no", variant="error")
        yield Footer()

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        elif event.button.id == "no":
            self.dismiss(False)
