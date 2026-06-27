"""Provider config screen widget."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Select, Static


class ProviderConfigScreen(Screen[dict[str, str] | None]):
    """Screen for interactive provider configuration inputs."""

    BINDINGS = [
        ("ctrl+s", "save", "Save & Connect"),
        ("escape", "exit", "Exit"),
    ]

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
    .config-path {
        color: $text-muted;
        margin-bottom: 1;
        text-align: center;
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
        config_path: Path | None = None,
    ) -> None:
        super().__init__()
        self.error_message = error_message
        self.prefill = prefill or {}
        self.config_path = config_path

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="config-container"):
            yield Static("Corge LLM Provider Configuration", classes="config-title")

            if self.config_path:
                yield Static(f"Config File: {self.config_path}", classes="config-path")

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

            with Vertical(classes="field-row"):
                yield Label("Reasoning Effort:")
                pref_val: Any = self.prefill.get("reasoning_effort")
                if pref_val not in ("low", "medium", "high"):
                    pref_val = Select.NULL
                yield Select(
                    options=[
                        ("Omitted (Default)", Select.NULL),
                        ("Low", "low"),
                        ("Medium", "medium"),
                        ("High", "high"),
                    ],
                    value=pref_val,
                    id="reasoning_effort_select",
                    allow_blank=False,
                )

            with Vertical(classes="field-row"):
                yield Label("Max Socratic Questions:")
                pref_q = self.prefill.get("max_socratic_questions", 3)
                try:
                    pref_q_int = int(pref_q)
                except (ValueError, TypeError):
                    pref_q_int = 3
                if pref_q_int not in (1, 2, 3, 4, 5):
                    pref_q_int = 3
                yield Select(
                    options=[
                        ("1", 1),
                        ("2", 2),
                        ("3", 3),
                        ("4", 4),
                        ("5", 5),
                    ],
                    value=pref_q_int,
                    id="max_socratic_questions_select",
                    allow_blank=False,
                )

            with Horizontal(classes="buttons"):
                yield Button("Save & Connect", id="save_btn", variant="success")
                yield Button("Exit", id="exit_btn", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#model_input", Input).focus()

    def action_save(self) -> None:
        model = self.query_one("#model_input", Input).value.strip()
        api_key = self.query_one("#api_key_input", Input).value.strip()
        base_url = self.query_one("#base_url_input", Input).value.strip()
        
        effort_widget = self.query_one("#reasoning_effort_select", Select)
        effort_val = effort_widget.value
        reasoning_effort = ""
        if effort_val is not None and effort_val is not Select.NULL:
            reasoning_effort = str(effort_val)
            
        questions_widget = self.query_one("#max_socratic_questions_select", Select)
        max_socratic_questions = str(questions_widget.value) if questions_widget.value is not Select.NULL else "3"

        self.dismiss(
            {
                "model": model,
                "api_key": api_key,
                "base_url": base_url,
                "reasoning_effort": reasoning_effort,
                "max_socratic_questions": max_socratic_questions,
            }
        )

    def action_exit(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_btn":
            model = self.query_one("#model_input", Input).value.strip()
            api_key = self.query_one("#api_key_input", Input).value.strip()
            base_url = self.query_one("#base_url_input", Input).value.strip()
            
            effort_widget = self.query_one("#reasoning_effort_select", Select)
            effort_val = effort_widget.value
            reasoning_effort = ""
            if effort_val is not None and effort_val is not Select.NULL:
                reasoning_effort = str(effort_val)
                
            questions_widget = self.query_one("#max_socratic_questions_select", Select)
            max_socratic_questions = str(questions_widget.value) if questions_widget.value is not Select.NULL else "3"

            self.dismiss(
                {
                    "model": model,
                    "api_key": api_key,
                    "base_url": base_url,
                    "reasoning_effort": reasoning_effort,
                    "max_socratic_questions": max_socratic_questions,
                }
            )
        elif event.button.id == "exit_btn":
            self.dismiss(None)
