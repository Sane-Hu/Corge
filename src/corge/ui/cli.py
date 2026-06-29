"""Textual-based UI implementation for the UiPort.

Spec traceability:
    Tech-spec §5 — TUI Screen Map: CanvasScreen, InteractiveDiffScreen, MessageScreen
    Sysdesign §UI Module — pure presentation, zero business logic
"""

from __future__ import annotations

import concurrent.futures
import difflib
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    DirectoryTree,
    Footer,
    Header,
    Input,
    LoadingIndicator,
    RichLog,
    Static,
)

from corge.contracts import (
    AcceptanceCriteria,
    ApprovalDecision,
    ApprovalRequest,
    EngineeringProfile,
    MemoryEvent,
    Plan,
    ProceduralStep,
    RepositoryContext,
    Specification,
    StickyNoteValidatorPort,
    TechnicalPlan,
    ToolAction,
    UiPort,
)
from corge.ui.confirm_screen import ConfirmScreen, SocraticOptInScreen
from corge.ui.freestyle_canvas import CanvasScreen
from corge.ui.interactive_diff import InteractiveDiffScreen
from corge.ui.provider_config import ProviderConfigScreen


class MessageScreen(Screen[str]):
    """Generic read-only dialog (spec §5 item 3 — MessageScreen).

    Used for: execution plan view, errors, completion review.
    """

    BINDINGS = [
        ("enter", "continue", "Continue"),
    ]

    CSS = """
    .footer-buttons {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    .footer-buttons Button {
        margin: 0 2;
    }
    """

    def __init__(self, title: str, message: str, show_back: bool = False, show_new_spec: bool = False, show_quit: bool = False) -> None:
        super().__init__()
        self._title = title
        self._message = message
        self._show_back = show_back
        self._show_new_spec = show_new_spec
        self._show_quit = show_quit

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static(self._title, classes="title")
            with ScrollableContainer(id="message_container"):
                yield Static(self._message, id="message_text", markup=False)
            with Horizontal(classes="footer-buttons"):
                if self._show_back:
                    yield Button("Back (esc)", id="back", variant="error")
                if self._show_new_spec:
                    yield Button("New Spec (n)", id="new_spec", variant="warning")
                yield Button("Copy (c)", id="copy", variant="default")
                auto_adv = getattr(self.app, "auto_advance", False)
                yield Button(
                    "Auto: ON (a)" if auto_adv else "Auto: OFF (a)",
                    id="auto_advance",
                    variant="success" if auto_adv else "default",
                )
                if self._show_quit:
                    yield Button("Quit (q)", id="quit", variant="error")
                yield Button("Continue (enter)", id="continue", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        if getattr(self.app, "auto_advance", False):
            self.dismiss("continue")
            return
        if self._show_back:
            self._bindings.bind("escape", "back", "Back")
        else:
            self._bindings.bind("escape", "continue", "Continue")
        if self._show_new_spec:
            self._bindings.bind("n", "new_spec", "New Spec")
        if self._show_quit:
            self._bindings.bind("q", "quit", "Quit")
        self._bindings.bind("c", "copy_text", "Copy")
        self._bindings.bind("a", "toggle_auto_advance", "Auto-advance")
        self.query_one("#continue", Button).focus()

    def action_continue(self) -> None:
        self.dismiss("continue")

    def action_back(self) -> None:
        self.dismiss("back")

    def action_new_spec(self) -> None:
        self.dismiss("new_spec")

    def action_quit(self) -> None:
        self.dismiss("quit")

    def action_copy_text(self) -> None:
        self.app.copy_to_clipboard(self._message)
        self.notify("Copied screen content to clipboard!")

    def action_toggle_auto_advance(self) -> None:
        current = getattr(self.app, "auto_advance", False)
        new_val = not current
        self.app: CorgeApp
        cast(CorgeApp, self.app).auto_advance = new_val
        status = "ENABLED" if new_val else "DISABLED"
        self.notify(f"Auto-advance: {status}")
        if new_val:
            self.dismiss("continue")
        else:
            try:
                btn = self.query_one("#auto_advance", Button)
                btn.label = "Auto: OFF (a)"
                btn.variant = "default"
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue":
            self.dismiss("continue")
        elif event.button.id == "back":
            self.dismiss("back")
        elif event.button.id == "new_spec":
            self.dismiss("new_spec")
        elif event.button.id == "quit":
            self.action_quit()
        elif event.button.id == "copy":
            self.action_copy_text()
        elif event.button.id == "auto_advance":
            self.action_toggle_auto_advance()


class PostCompletionScreen(Screen[str]):
    """Menu shown when a specification is completely implemented."""

    BINDINGS = [
        ("n", "new_spec", "New Spec"),
        ("s", "switch_repo", "Switch Project"),
        ("q", "quit", "Quit"),
        ("escape", "quit", "Quit"),
    ]

    CSS = """
    PostCompletionScreen {
        align: center middle;
    }
    PostCompletionScreen > Vertical {
        width: 60%;
        height: auto;
        border: round $primary;
        padding: 1 2;
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

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("Implementation Complete", classes="title")
            yield Static(
                "The specification has been successfully implemented and verified.\n\nWhat would you like to do next?",
                id="message",
            )
            with Horizontal(classes="footer-buttons"):
                yield Button("New Spec (n)", id="new_spec", variant="success")
                yield Button("Switch Project (s)", id="switch_repo", variant="primary")
                yield Button("Quit (q/esc)", id="quit", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#new_spec", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id)

    def action_new_spec(self) -> None:
        self.dismiss("new_spec")

    def action_switch_repo(self) -> None:
        self.dismiss("switch_repo")

    def action_quit(self) -> None:
        self.dismiss("quit")


class LoadingScreen(Screen[None]):
    """Generic loading indicator screen."""

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message
        self._stream_log = RichLog(id="stream_log")

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="loading-container"):
            yield Static(self._message, classes="title")
            yield LoadingIndicator()
            yield self._stream_log

    def append_token(self, token: str) -> None:
        if token:
            self._stream_log.write(token)


class CorgeApp(App[None]):
    """The main Textual application for Corge."""

    auto_advance: bool = False

    def copy_to_clipboard(self, text: str) -> None:
        """Robust system clipboard copy with OSC 52 and Linux tool fallbacks."""
        super().copy_to_clipboard(text)
        
        import shutil
        import subprocess
        
        if shutil.which("wl-copy"):
            try:
                subprocess.run(["wl-copy"], input=text.encode("utf-8"), check=False)
            except Exception:
                pass
        elif shutil.which("xclip"):
            try:
                subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode("utf-8"), check=False)
            except Exception:
                pass
        elif shutil.which("xsel"):
            try:
                subprocess.run(["xsel", "--clipboard", "--input"], input=text.encode("utf-8"), check=False)
            except Exception:
                pass

    CSS = """
    $primary: #75188f;
    $secondary: #75167a;
    $accent: #e886fa; /* Lighter purple for readable text accents */

    Screen {
        background: #2b0630; /* Solid dark purple background */
    }

    MessageScreen {
        align: center middle;
    }
    MessageScreen > Vertical {
        width: 80%;
        height: auto;
        border: round $primary;
        padding: 1 2;
    }
    #message_container {
        height: 15;
        border: solid $secondary;
        background: #1a021d;
        padding: 1 2;
        margin-bottom: 1;
    }
    #message_text {
        width: 100%;
        height: auto;
    }
    .title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    LoadingScreen {
        align: center middle;
    }
    .loading-container {
        width: 50%;
        height: auto;
        max-height: 80%;
        border: round $primary;
        padding: 1 2;
    }
    .stream-scroll {
        height: 10;
        margin-top: 1;
        overflow-y: auto;
    }
    """


class CorgeDirectoryTree(DirectoryTree):
    """Subclass of DirectoryTree that allows toggling hidden files/folders."""

    show_hidden: bool = False

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        if self.show_hidden:
            return paths
        return [p for p in paths if not p.name.startswith(".")]


class DirectorySelectorApp(App[Path]):
    """App to select a directory before starting Corge."""

    def copy_to_clipboard(self, text: str) -> None:
        """Robust system clipboard copy with OSC 52 and Linux tool fallbacks."""
        super().copy_to_clipboard(text)
        
        import shutil
        import subprocess
        
        if shutil.which("wl-copy"):
            try:
                subprocess.run(["wl-copy"], input=text.encode("utf-8"), check=False)
            except Exception:
                pass
        elif shutil.which("xclip"):
            try:
                subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode("utf-8"), check=False)
            except Exception:
                pass
        elif shutil.which("xsel"):
            try:
                subprocess.run(["xsel", "--clipboard", "--input"], input=text.encode("utf-8"), check=False)
            except Exception:
                pass

    CSS = """
    .title { padding: 1; background: $boost; }
    .hidden { display: none; }
    #action_buttons {
        layout: horizontal;
        height: auto;
        margin: 0;
        padding: 0;
    }
    #select_btn {
        margin: 1 1 1 2;
        width: 1fr;
    }
    #api_btn {
        margin: 1 2 1 1;
        width: 1fr;
    }
    """

    BINDINGS = [
        ("escape", "escape_key", "Back/Quit"),
        ("backspace", "go_up", "Up Dir"),
        ("u", "go_up", "Up Dir"),
        ("s", "select_current", "Select Highlighted Dir"),
        ("c", "create_dir", "Create Dir"),
        ("m", "manual_path", "Manual Path"),
        ("h", "toggle_hidden", "Toggle Hidden"),
        ("a", "configure_api", "Configure API"),
    ]

    _input_mode: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True, id="header")
        yield Static(
            "Browse to your repository folder. Highlight it and press 's' or click 'Select' to confirm.",
            classes="title"
        )
        inp = Input(id="action_input")
        inp.styles.display = "none"
        yield inp
        start_path = Path.cwd()
        # UX Improvement: If running from the Corge source/dev repository itself,
        # start the selector at the parent directory to allow easy selection of sibling repos.
        if (start_path / "src" / "corge").exists() or start_path.name.lower() == "corge":
            start_path = start_path.parent

        yield CorgeDirectoryTree(str(start_path.resolve()))
        with Horizontal(id="action_buttons"):
            yield Button("Select Highlighted Directory (s)", id="select_btn", variant="success")
            yield Button("Configure API (a)", id="api_btn", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(CorgeDirectoryTree).focus()

    def action_go_up(self) -> None:
        tree = self.query_one(CorgeDirectoryTree)
        tree.path = str(Path(tree.path).parent.resolve())

    def action_toggle_hidden(self) -> None:
        tree = self.query_one(CorgeDirectoryTree)
        tree.show_hidden = not tree.show_hidden
        tree.path = tree.path

    def action_escape_key(self) -> None:
        inp = self.query_one("#action_input", Input)
        if inp.styles.display == "block":
            inp.styles.display = "none"
            inp.value = ""
            tree = self.query_one(CorgeDirectoryTree)
            tree.focus()
            self._input_mode = None
        else:
            self.exit(None)

    def action_select_current(self) -> None:
        tree = self.query_one(CorgeDirectoryTree)
        if tree.cursor_node and tree.cursor_node.data:
            path = Path(tree.cursor_node.data.path)
            if path.is_dir():
                self.exit(path.resolve())
            else:
                self.exit(path.parent.resolve())

    @on(Button.Pressed, "#select_btn")
    def handle_select_btn(self) -> None:
        self.action_select_current()

    @on(Button.Pressed, "#api_btn")
    def handle_api_btn(self) -> None:
        self.action_configure_api()

    def action_configure_api(self) -> None:
        tree = self.query_one(CorgeDirectoryTree)
        target_path = Path(tree.path).resolve()
        if tree.cursor_node and tree.cursor_node.data:
            cursor_path = Path(tree.cursor_node.data.path).resolve()
            if cursor_path.is_dir():
                target_path = cursor_path
            else:
                target_path = cursor_path.parent

        # Config resolution order:
        # 1. target_path / ".agents" / "CorgeAPIConfig.toml"
        # 2. target_path / "agents" / "CorgeAPIConfig.toml"
        # 3. target_path / "CorgeAPIConfig.toml"
        # 4. target_path / ".agent" / "CorgeAPIConfig.toml"
        # Defaults to target_path / ".agents" / "CorgeAPIConfig.toml"
        config_path = target_path / ".agents" / "CorgeAPIConfig.toml"
        if not config_path.exists():
            for path in [
                target_path / "agents" / "CorgeAPIConfig.toml",
                target_path / "CorgeAPIConfig.toml",
                target_path / ".agent" / "CorgeAPIConfig.toml",
            ]:
                if path.exists():
                    config_path = path
                    break

        prefill = {}
        import tomllib
        if config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    prefill = tomllib.load(f)
            except Exception:
                pass

        if prefill.get("api_key") == "your-api-key-here":
            prefill["api_key"] = ""

        def on_save(new_cfg: dict[str, str] | None) -> None:
            if not new_cfg:
                self.query_one(CorgeDirectoryTree).focus()
                return

            existing = {}
            if config_path.exists():
                try:
                    with open(config_path, "rb") as f:
                        existing = tomllib.load(f)
                except Exception:
                    pass
            else:
                # Prefill from config.toml.example
                template_path = (
                    Path(__file__).resolve().parent.parent.parent / "config.toml.example"
                )
                if not template_path.exists():
                    template_path = Path("config.toml.example")
                if template_path.exists():
                    try:
                        with open(template_path, "rb") as f:
                            existing = tomllib.load(f)
                    except Exception:
                        pass

            existing["model"] = new_cfg["model"]
            existing["api_key"] = new_cfg["api_key"]
            existing["base_url"] = new_cfg.get("base_url", "")

            effort = new_cfg.get("reasoning_effort", "")
            if effort:
                existing["reasoning_effort"] = effort
            elif "reasoning_effort" in existing:
                del existing["reasoning_effort"]

            questions = new_cfg.get("max_socratic_questions", "3")
            try:
                existing["max_socratic_questions"] = int(questions)
            except (ValueError, TypeError):
                existing["max_socratic_questions"] = 3

            # Make sure standard defaults exist if missing
            if "max_tokens" not in existing:
                existing["max_tokens"] = 4096
            if "keep_alive" not in existing:
                existing["keep_alive"] = "-1"
            if "timeout" not in existing:
                existing["timeout"] = 120.0
            if "enable_prefix_caching" not in existing:
                existing["enable_prefix_caching"] = True

            # Custom flat-dictionary to TOML serializer
            lines = ["# Corge LLM Provider Configuration"]
            extra_headers = {}
            for k, v in existing.items():
                if k == "extra_headers":
                    extra_headers = v
                    continue
                if v is None:
                    continue
                if isinstance(v, bool):
                    lines.append(f"{k} = {str(v).lower()}")
                elif isinstance(v, (int, float)):
                    lines.append(f"{k} = {v}")
                else:
                    lines.append(f'{k} = "{v}"')

            if extra_headers:
                lines.append("\n[extra_headers]")
                for hk, hv in extra_headers.items():
                    lines.append(f'{hk} = "{hv}"')

            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.query_one(CorgeDirectoryTree).focus()

        self.push_screen(ProviderConfigScreen(prefill=prefill, config_path=config_path), on_save)

    def action_create_dir(self) -> None:
        inp = self.query_one("#action_input", Input)
        inp.styles.display = "block"
        inp.placeholder = "Enter name of new directory to create in current path..."
        inp.focus()
        self._input_mode = "create"

    def action_manual_path(self) -> None:
        inp = self.query_one("#action_input", Input)
        inp.styles.display = "block"
        inp.placeholder = "Enter absolute path to navigate to..."
        inp.focus()
        self._input_mode = "manual"

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        val = event.value.strip()
        inp = event.input
        tree = self.query_one(CorgeDirectoryTree)

        if not val:
            inp.styles.display = "none"
            inp.value = ""
            tree.focus()
            self._input_mode = None
            return

        if self._input_mode == "create":
            new_path = Path(tree.path) / val
            try:
                new_path.mkdir(parents=True, exist_ok=True)
                tree.path = str(new_path)
                self._input_mode = None
            except OSError as e:
                inp.value = ""
                inp.placeholder = f"Error creating directory: {e.strerror or str(e)}"
                return
        elif self._input_mode == "manual":
            try:
                new_path = Path(val).expanduser().resolve()
                if new_path.is_dir():
                    tree.path = str(new_path)
                    self._input_mode = None
                else:
                    inp.value = ""
                    inp.placeholder = f"Error: '{val}' is not a valid directory!"
                    return
            except Exception as e:
                inp.value = ""
                inp.placeholder = f"Error: {str(e)}"
                return

        inp.styles.display = "none"
        inp.value = ""
        tree.focus()



class CliUi(UiPort):
    """Thread-safe UI port that delegates to the Textual app.

    All screen pushes go through ``call_from_thread`` so agent threads
    can invoke UI operations safely from outside the event loop.
    """

    def __init__(
        self,
        app: CorgeApp,
        validator: StickyNoteValidatorPort | None = None,
    ) -> None:
        self._app = app
        self._validator = validator

    def _run_screen(self, screen: Screen[Any]) -> Any:
        future: concurrent.futures.Future[Any] = concurrent.futures.Future()

        def callback(result: Any) -> None:
            future.set_result(result)

        self._app.call_from_thread(self._app.push_screen, screen, callback)
        res = future.result()
        if res == "quit":
            self._app.call_from_thread(self._app.exit)
            raise SystemExit()
        return res

    def update_journey_state(self, agent_name: str, state_name: str) -> None:
        def do_update() -> None:
            self._app.title = f"Corge — {agent_name}"
            self._app.sub_title = f"State: {state_name}"

        self._app.call_from_thread(do_update)

    # ------------------------------------------------------------------
    # Specification phase screens
    # ------------------------------------------------------------------

    def show_spec_wizard(self, prefill: str = "") -> Specification | None:
        """Present a freestyle brainstorming canvas to the user."""
        text = self._run_screen(CanvasScreen(validator=self._validator, initial_text=prefill))
        if text is None:
            return None
        # Wrap raw canvas text; SpecificationAgent.concretize() will structure it.
        return Specification(
            title="Canvas Draft",
            body=text,
            acceptance_criteria=AcceptanceCriteria(items=()),
        )

    def show_argumentation_diff(
        self, canvas_text: str, right_text: str
    ) -> str | None:
        """Display raw canvas text on the left and the editable spec template on the right."""
        result_text = self._run_screen(
            InteractiveDiffScreen(
                left_title="Canvas",
                left_text=canvas_text,
                right_title="Specification",
                right_text=right_text,
                prompt_text="Resolve any gaps in the Specification.",
                reject_text="Back",
                diff_title="Diff (Canvas vs Spec)",
            )
        )
        return cast(str | None, result_text)

    def show_question(self, question: str, context: str) -> str:
        """Display a Socratic question and return the user's answer."""
        import re
        prefill = ""
        for line in question.splitlines():
            line_stripped = line.strip()
            match = re.match(r"^(\d+)\.", line_stripped)
            if match:
                num = match.group(1)
                prefill += f"{num}. <Enter answer here>\n"
        if prefill:
            prefill = prefill.rstrip("\n")

        result_text = self._run_screen(
            InteractiveDiffScreen(
                left_title="Clarifying Questions",
                left_text=question,
                right_title="Your Answers",
                right_text=prefill,
                prompt_text="Please provide your answers. Click Submit when done.",
                approve_text="Submit Answers",
                reject_text="Skip",
            )
        )
        return result_text or ""

    def show_confirm(self, title: str, message: str) -> bool:
        """Display a confirmation dialog returning True (Yes) or False (No)."""
        result = self._run_screen(ConfirmScreen(title, message))
        return bool(result)

    def show_socratic_opt_in(self, message: str) -> str:
        """Display Socratic Spec Wizard opt-in dialog returning 'yes', 'no', or 'back'."""
        result = self._run_screen(SocraticOptInScreen(message))
        return str(result or "no")

    # ------------------------------------------------------------------
    # Planning phase screens
    # ------------------------------------------------------------------

    def show_plan(self, plan: Plan) -> bool:
        """Display the execution plan steps (spec §5 MessageScreen)."""
        msg = "\n".join(
            f"{i}. [{s.identifier}] {s.description}"
            for i, s in enumerate(plan.steps, 1)
        )
        return bool(self._run_screen(MessageScreen("Execution Plan", msg or "(no steps)", show_back=True)) == "continue")

    def show_tech_plan_editor(self, plan: TechnicalPlan, specification: Specification) -> TechnicalPlan | None:
        result_text = self._run_screen(
            InteractiveDiffScreen(
                left_title="Approved Specification",
                left_text=specification.body,
                right_title="Technical Plan",
                right_text=plan.content,
                prompt_text=(
                    "Review and refine the Technical Plan. Click Approve when ready."
                ),
                reject_text="Back",
                diff_title="Diff (Technical Plan vs Approved Specification)",
            )
        )
        if result_text is None:
            return None
        return TechnicalPlan(
            content=result_text,
            specification_ref=plan.specification_ref,
        )

    def show_procedural_steps_editor(
        self, steps: tuple[ProceduralStep, ...], technical_plan: TechnicalPlan
    ) -> tuple[ProceduralStep, ...] | None:
        steps_text = "\n".join(f"[{s.identifier}] {s.description}" for s in steps)
        result_text = self._run_screen(
            InteractiveDiffScreen(
                left_title="Technical Plan",
                left_text=technical_plan.content,
                right_title="Procedural Steps",
                right_text=steps_text,
                prompt_text="Edit procedural steps. Each line becomes one step.",
                reject_text="Back",
                diff_title="Diff (Current Procedural Steps vs Previous Draft)",
            )
        )
        if result_text is None:
            return None

        import re
        new_steps = []
        step_count = 0
        for line in result_text.strip().split("\n"):
            stripped = line.strip()
            if stripped:
                step_count += 1
                match = re.match(r"^\[([^\]]+)\]\s*(.*)$", stripped)
                if match:
                    identifier = match.group(1).strip()
                    description = match.group(2).strip()
                else:
                    identifier = f"step-{step_count}"
                    description = stripped
                new_steps.append(
                    ProceduralStep(
                        identifier=identifier,
                        description=description,
                    )
                )
        return tuple(new_steps) if new_steps else steps

    # ------------------------------------------------------------------
    # Coding phase screens
    # ------------------------------------------------------------------

    def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        """Show approval request via split pane (finding 8.7 — has Reject button)."""
        detail = (
            f"Action : {request.action}\n"
            f"Target : {request.target}\n"
            f"Reason : {request.reason}\n"
            f"Step   : {request.step_ref or '—'}\n\n"
        )

        override_diff = None
        if request.action == ToolAction.EDIT:
            old = request.payload.get("old", "")
            new = request.payload.get("new", "")
            diff_lines = list(
                difflib.unified_diff(
                    old.splitlines(keepends=True),
                    new.splitlines(keepends=True),
                    fromfile=f"{request.target} (Old)",
                    tofile=f"{request.target} (New)",
                    n=3,
                )
            )
            override_diff = "".join(diff_lines) if diff_lines else "No differences."
            detail += f"Old text length: {len(old)}\nNew text length: {len(new)}\n"
        elif request.action == ToolAction.WRITE:
            content = request.payload.get("content", "")
            detail += f"Content length: {len(content)}\n"
            override_diff = f"--- /dev/null\n+++ {request.target}\n@@ -0,0 +1,{len(content.splitlines())} @@\n"
            override_diff += "".join(f"+{line}\n" for line in content.splitlines())
        elif request.action == ToolAction.BASH:
            detail += f"Command:\n{request.target}\n"
            override_diff = (
                f"Executing bash command in current directory:\n$ {request.target}\n"
            )

        diff_title = "Diff vs Original Draft"
        if request.action == ToolAction.EDIT:
            diff_title = f"Proposed File Edit Diff — {request.target}"
        elif request.action == ToolAction.WRITE:
            diff_title = f"Proposed New File Content — {request.target}"
        elif request.action == ToolAction.BASH:
            diff_title = f"Proposed Bash Command — {request.target}"

        result = self._run_screen(
            InteractiveDiffScreen(
                left_title="Request Context",
                left_text=(
                    "The agent requires authorization to perform an action.\n\n"
                    "Press Ctrl+T or click 'Toggle Diff' below to toggle live diff."
                ),
                right_title="Approval Request",
                right_text=detail,
                prompt_text="Review the requested action carefully.",
                override_diff_text=override_diff,
                right_read_only=True,
                diff_title=diff_title,
            )
        )
        # InteractiveDiffScreen.dismiss(text) → APPROVED; dismiss(None) → REJECTED
        if result is not None:
            return ApprovalDecision.APPROVED
        return ApprovalDecision.REJECTED

    def show_step_diff(
        self,
        step_id: str,
        description: str,
        diff_text: str,
    ) -> bool:
        """Display step completion diff review screen using InteractiveDiffScreen."""
        from corge.ui.interactive_diff import InteractiveDiffScreen

        result = self._run_screen(
            InteractiveDiffScreen(
                left_title="Step Context",
                left_text=(
                    f"Step '{step_id}' executed successfully.\n\n"
                    f"Description: {description}\n\n"
                    "Please review the changes made to your repository."
                ),
                right_title="Files Modified",
                right_text="Select 'Keep Changes' to accept the modifications, or 'Discard Changes' to revert them.",
                prompt_text="Review the modifications before proceeding.",
                approve_text="Keep Changes",
                reject_text="Discard Changes",
                override_diff_text=diff_text,
                right_read_only=True,
                diff_title=f"Step Completion Diff — {step_id}",
            )
        )
        return result is not None

    def show_completion_review(self, plan: Plan) -> bool:
        """Display per-step completion status (spec §5 item 3, finding 8.9)."""
        lines = ["Completion Review\n"]
        for step in plan.steps:
            status = "✓ done" if step.completed else "○ pending"
            lines.append(f"  [{status}] [{step.identifier}] {step.description}")

        if all(s.completed for s in plan.steps):
            lines.append(
                "\n✓ All steps completed. "
                "Implementation has passed acceptance and verification."
            )
        else:
            pending = sum(1 for s in plan.steps if not s.completed)
            lines.append(f"\n{pending} step(s) still pending.")

        return bool(self._run_screen(MessageScreen("Completion Review", "\n".join(lines), show_back=True)) == "continue")

    def show_post_completion_options(self) -> str:
        """Display options after completion (spec §5 item 3)."""
        return str(self._run_screen(PostCompletionScreen()))

    # ------------------------------------------------------------------
    # Repository & profile display screens (finding 8.6)
    # ------------------------------------------------------------------

    def show_repository_analysis(self, repository_context: RepositoryContext) -> bool:
        tree_lines = "\n".join(f"  {p}" for p in repository_context.tree[:100])
        config_lines = "\n".join(f"  {c}" for c in repository_context.config_files)
        msg = (
            f"Root: {repository_context.root}\n\n"
            f"Files ({len(repository_context.tree)}):\n{tree_lines or '  (empty)'}\n\n"
            f"Config files:\n{config_lines or '  (none)'}"
        )
        return bool(self._run_screen(MessageScreen("Repository Analysis", msg, show_back=True, show_quit=True)) == "continue")

    def show_repository_understanding(
        self, repository_context: RepositoryContext
    ) -> bool:
        msg = (
            f"Repository: {repository_context.root}\n\n"
            f"Total tracked paths: {len(repository_context.tree)}\n"
            f"Config/build files: {len(repository_context.config_files)}"
        )
        return bool(self._run_screen(MessageScreen("Repository Understanding", msg, show_back=True, show_quit=True)) == "continue")

    def show_engineering_profile(self, profile: EngineeringProfile) -> bool:
        if profile.rules:
            lines = [
                f"  • {rule}  (confidence: {profile.confidence.get(rule, 1.0):.0%})"
                for rule in profile.rules
            ]
            msg = (
                "Engineering conventions derived from this repository:\n\n"
                + "\n".join(lines)
            )
        else:
            msg = "No engineering conventions recorded yet."
        return bool(self._run_screen(MessageScreen("Engineering Profile", msg, show_back=True, show_quit=True)) == "continue")

    def show_memory(self, events: tuple[MemoryEvent, ...]) -> str:
        if events:
            lines = [f"  [{e.timestamp or '—'}] {e.kind}" for e in events[:50]]
            msg = f"Recent memory events ({len(events)}):\n\n" + "\n".join(lines)
        else:
            msg = "No memory events recorded yet."
        return str(self._run_screen(MessageScreen("Memory Events", msg, show_back=True, show_new_spec=True)))

    def show_logs(self) -> bool:
        try:
            import json
            from pathlib import Path

            log_path = Path(".agent/audit.jsonl")
            if log_path.exists():
                lines = log_path.read_text(encoding="utf-8").splitlines()
                formatted_lines = []
                for line in lines[-200:]:  # Show last 200 log entries
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        ts = entry.get("timestamp", "").split(".")[0].replace("T", " ")
                        kind = entry.get("kind", "").upper()
                        payload = entry.get("payload", {})

                        if kind == "PROPOSE_ACTION":
                            action = payload.get("action", "")
                            target = payload.get("target", "")
                            reason = payload.get("reason", "")
                            fmt = f"[{ts}] {kind}: {action} -> {target}\n      Reason: {reason}"
                        elif kind == "TOOL_RESULT":
                            action = payload.get("action", "")
                            target = payload.get("target", "")
                            status = (
                                "Success"
                                if payload.get("exit_code") == 0
                                or "exit_code" not in payload
                                else f"Failed (exit: {payload.get('exit_code')})"
                            )
                            fmt = f"[{ts}] {kind}: {action} -> {target} [{status}]"
                        elif kind == "EVALUATE_COMPLETION":
                            success = payload.get("success", False)
                            fmt = f"[{ts}] {kind}: Success = {success}"
                        elif kind == "RECORD_COMPLETION":
                            success = payload.get("success", False)
                            fmt = f"[{ts}] {kind}: Success = {success}"
                        elif kind == "RECORD_APPROVAL":
                            decision = payload.get("decision", "")
                            fmt = f"[{ts}] {kind}: Decision = {decision}"
                        else:
                            fmt = f"[{ts}] {kind}: {payload}"
                        formatted_lines.append(fmt)
                    except Exception:
                        formatted_lines.append(line)
                msg = "\n".join(formatted_lines)
            else:
                msg = "No logs found."
        except Exception as e:
            msg = f"Error loading logs: {e}"
        return bool(self._run_screen(MessageScreen("Audit Logs", msg, show_back=True)) == "continue")

    def show_provider_config_screen(
        self, error_message: str | None = None, prefill: dict[str, str] | None = None
    ) -> dict[str, str] | None:
        """Present the provider configuration screen to the user."""
        config_path = getattr(self._app, "config_path", None)
        res: dict[str, str] | None = self._run_screen(
            ProviderConfigScreen(error_message=error_message, prefill=prefill, config_path=config_path)
        )
        return res

    def show_loading(self, message: str) -> None:
        """Display a blocking loading overlay with a message."""
        self._app.call_from_thread(self._app.push_screen, LoadingScreen(message))

    def hide_loading(self) -> None:
        """Dismiss the active loading overlay."""

        def _pop_if_loading() -> None:
            if isinstance(self._app.screen, LoadingScreen):
                self._app.pop_screen()

        self._app.call_from_thread(_pop_if_loading)

    def stream_token(self, token: str) -> None:
        """Stream an LLM generation token directly to the UI."""

        def do_update() -> None:
            if isinstance(self._app.screen, LoadingScreen):
                self._app.screen.append_token(token)

        self._app.call_from_thread(do_update)
