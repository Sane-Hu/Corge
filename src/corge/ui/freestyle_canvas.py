"""Freestyle canvas component for textual UI."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Static, TextArea


class CanvasScreen(Screen):
    """Mental Model Hatchery for organic brainstorming."""
    
    CSS = """
    CanvasScreen {
        layout: vertical;
        align: center middle;
    }
    .container {
        width: 80%;
        height: 80%;
        border: round $accent;
        padding: 1 2;
        margin: 1;
    }
    .header {
        text-align: center;
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(classes="container"):
            yield Static("Freestyle Canvas (Brainstorming)", classes="header")
            self.text_area = TextArea(
                "Write your feature goals, user stories, and constraints here.\n"
                "You can also paste sticky notes or graph references.\n"
            )
            yield self.text_area
            yield Button("Submit to Concretization", id="submit", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            self.dismiss(self.text_area.text)
