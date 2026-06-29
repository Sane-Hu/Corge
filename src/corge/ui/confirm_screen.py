"""Confirmation dialog screen for Textual TUI."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static


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
    #confirm_message_container {
        height: 10;
        border: solid $secondary;
        background: #1a021d;
        padding: 1 2;
        margin-bottom: 1;
    }
    #confirm_message_text {
        width: 100%;
        height: auto;
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
            with ScrollableContainer(id="confirm_message_container"):
                yield Static(self._message, id="confirm_message_text", markup=False)
            with Horizontal(classes="footer-buttons"):
                yield Button("Yes (y)", id="yes", variant="success")
                yield Button("No (n/esc)", id="no", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#no", Button).focus()

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        elif event.button.id == "no":
            self.dismiss(False)


class SocraticOptInScreen(Screen[str]):
    """Three-option dialog screen for Socratic Wizard opt-in."""

    BINDINGS = [
        ("y", "yes", "Yes"),
        ("n", "no", "No"),
        ("escape", "back", "Back"),
    ]

    CSS = """
    SocraticOptInScreen {
        align: center middle;
    }
    SocraticOptInScreen > Vertical {
        width: 80%;
        height: auto;
        border: round $primary;
        padding: 1 2;
        background: #2b0630;
    }
    #opt_message_container {
        height: 10;
        border: solid $secondary;
        background: #1a021d;
        padding: 1 2;
        margin-bottom: 1;
    }
    #opt_message_text {
        width: 100%;
        height: auto;
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

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("Socratic Spec Wizard", classes="title")
            with ScrollableContainer(id="opt_message_container"):
                yield Static(self._message, id="opt_message_text", markup=False)
            with Horizontal(classes="footer-buttons"):
                yield Button("Yes (y)", id="yes", variant="success")
                yield Button("No (n)", id="no", variant="default")
                yield Button("Back (esc)", id="back", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#yes", Button).focus()

    def action_yes(self) -> None:
        self.dismiss("yes")

    def action_no(self) -> None:
        self.dismiss("no")

    def action_back(self) -> None:
        self.dismiss("back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("yes", "no", "back"):
            self.dismiss(event.button.id)
