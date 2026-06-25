"""Provider config screen widget."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Header, Input, Label, Static


class ProviderConfigScreen(Screen[dict[str, str]]):
    """Screen for interactive provider configuration inputs."""

    CSS = """
    ProviderConfigScreen {
        align: center middle;
    }
    .config-container {
        width: 60;
        height: auto;
        border: round $primary;
        padding: 1 2;
        background: $panel;
    }
    .config-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    .error-msg {
        color: $error;
        text-style: italic;
        margin-bottom: 1;
    }
    .info-msg {
        margin-bottom: 1;
    }
    .field-row {
        height: auto;
        margin-bottom: 1;
        layout: vertical;
    }
    .field-label {
        color: $text;
        text-style: bold;
    }
    .buttons {
        height: 3;
        align: right middle;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        error_message: str | None = None,
        prefill: dict[str, str] | None = None,
    ) -> None:
        super().__init__()
        self.error_message = error_message
        self.prefill = prefill or {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="config-container"):
            yield Static("Corge LLM Provider Configuration", classes="config-title")

            if self.error_message:
                yield Static(f"Error: {self.error_message}", classes="error-msg")
            else:
                yield Static(
                    "Please provide your LLM API configuration details.",
                    classes="info-msg",
                )

            model_val = self.prefill.get("model", "")
            api_key_val = self.prefill.get("api_key", "")
            base_url_val = self.prefill.get("base_url", "")

            with Vertical(classes="field-row"):
                yield Label("Model Name:")
                yield Input(
                    placeholder="e.g. gpt-4o, llama3",
                    id="model_input",
                    value=model_val,
                )

            with Vertical(classes="field-row"):
                yield Label("API Key:")
                yield Input(
                    placeholder="Enter your API key",
                    id="api_key_input",
                    value=api_key_val,
                    password=True,
                )

            with Vertical(classes="field-row"):
                yield Label("Base URL Override (Optional):")
                yield Input(
                    placeholder="e.g. https://api.openai.com/v1",
                    id="base_url_input",
                    value=base_url_val,
                )

            with Horizontal(classes="buttons"):
                yield Button("Save & Connect", id="save_btn", variant="success")
                yield Button("Exit", id="exit_btn", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_btn":
            model = self.query_one("#model_input", Input).value.strip()
            api_key = self.query_one("#api_key_input", Input).value.strip()
            base_url = self.query_one("#base_url_input", Input).value.strip()
            self.dismiss(
                {
                    "model": model,
                    "api_key": api_key,
                    "base_url": base_url,
                }
            )
        elif event.button.id == "exit_btn":
            self.dismiss(None)
