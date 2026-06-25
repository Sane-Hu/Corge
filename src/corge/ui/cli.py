"""Textual-based UI implementation for the UiPort.

Spec traceability:
    Tech-spec §5 — TUI Screen Map: CanvasScreen, InteractiveDiffScreen, MessageScreen
    Sysdesign §UI Module — pure presentation, zero business logic
"""

from __future__ import annotations

import concurrent.futures
from collections.abc import Iterable
import difflib
from pathlib import Path
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Vertical
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
    TextArea,
)

from corge.contracts import (
    AcceptanceCriteria,
    ApprovalDecision,
    ApprovalRequest,
    CanvasSnapshot,
    ContextBundle,
    EngineeringProfile,
    MemoryEvent,
    Plan,
    ProceduralStep,
    RepositoryContext,
    SemanticGap,
    Specification,
    StickyNoteValidatorPort,
    TechnicalPlan,
    ToolAction,
    UiPort,
)
from corge.ui.freestyle_canvas import CanvasScreen
from corge.ui.interactive_diff import InteractiveDiffScreen
from corge.ui.provider_config import ProviderConfigScreen
from corge.ui.confirm_screen import ConfirmScreen


class MessageScreen(Screen[None]):
    """Generic read-only dialog (spec §5 item 3 — MessageScreen).

    Used for: execution plan view, errors, completion review.
    """

    BINDINGS = [
        ("escape", "continue", "Continue"),
        ("enter", "continue", "Continue"),
    ]

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static(self._title, classes="title")
            yield TextArea(self._message, read_only=True)
            yield Button("Continue", id="continue", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#continue", Button).focus()

    def action_continue(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue":
            self.dismiss(None)


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

    CSS = """
    .title { padding: 1; background: $boost; }
    .hidden { display: none; }
    #select_btn {
        margin: 1 2;
        width: 100%;
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
        yield CorgeDirectoryTree(str(Path.cwd()))
        yield Button("Select Highlighted Directory (s)", id="select_btn", variant="success")
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
        return future.result()

    def update_journey_state(self, agent_name: str, state_name: str) -> None:
        def do_update() -> None:
            self._app.title = f"Corge — {agent_name}"
            self._app.sub_title = f"State: {state_name}"

        self._app.call_from_thread(do_update)

    # ------------------------------------------------------------------
    # Specification phase screens
    # ------------------------------------------------------------------

    def show_spec_wizard(self) -> Specification:
        """Present a freestyle brainstorming canvas to the user."""
        text = self._run_screen(CanvasScreen(validator=self._validator))
        # Wrap raw canvas text; SpecificationAgent.concretize() will structure it.
        return Specification(
            title="Canvas Draft",
            body=text or "",
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
            )
        )
        return result_text

    def show_question(self, question: str, context: str) -> str:
        """Display a Socratic question and return the user's answer."""
        result_text = self._run_screen(
            InteractiveDiffScreen(
                left_title="Clarifying Questions",
                left_text=question,
                right_title="Your Answers",
                right_text="",
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

    # ------------------------------------------------------------------
    # Planning phase screens
    # ------------------------------------------------------------------

    def show_plan(self, plan: Plan) -> None:
        """Display the execution plan steps (spec §5 MessageScreen)."""
        msg = "\n".join(
            f"{i}. [{s.identifier}] {s.description}"
            for i, s in enumerate(plan.steps, 1)
        )
        self._run_screen(MessageScreen("Execution Plan", msg or "(no steps)"))

    def show_tech_plan_editor(self, plan: TechnicalPlan) -> TechnicalPlan | None:
        result_text = self._run_screen(
            InteractiveDiffScreen(
                left_title="Approved Specification",
                left_text="(See specification in session context)",
                right_title="Technical Plan",
                right_text=plan.content,
                prompt_text=(
                    "Review and refine the Technical Plan. Click Approve when ready."
                ),
            )
        )
        if result_text is None:
            return None
        return TechnicalPlan(
            content=result_text,
            specification_ref=plan.specification_ref,
        )

    def show_procedural_steps_editor(
        self, steps: tuple[ProceduralStep, ...]
    ) -> tuple[ProceduralStep, ...] | None:
        steps_text = "\n".join(f"[{s.identifier}] {s.description}" for s in steps)
        result_text = self._run_screen(
            InteractiveDiffScreen(
                left_title="Technical Plan",
                left_text="(Refer to approved Technical Plan)",
                right_title="Procedural Steps",
                right_text=steps_text,
                prompt_text="Edit procedural steps. Each line becomes one step.",
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

    def show_execution(self, context: ContextBundle) -> None:
        """Display current execution state during the coding phase (finding 8.5).

        Shows the active plan step and spec title so the engineer can
        monitor progress while the agent is working.
        """
        step_lines = "\n".join(
            f"  {i}. [{s.identifier}] {s.description}"
            for i, s in enumerate(context.plan.steps, 1)
        )
        msg = (
            f"Specification: {context.specification.title}\n\n"
            f"Executing plan steps:\n{step_lines or '  (none)'}"
        )
        self._run_screen(MessageScreen("Execution in Progress", msg))

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

        result = self._run_screen(
            InteractiveDiffScreen(
                left_title="Request Context",
                left_text="The agent requires authorization to perform an action.\n\nPress Ctrl+D to toggle live diff.",
                right_title="Approval Request",
                right_text=detail,
                prompt_text="Review the requested action carefully.",
                override_diff_text=override_diff,
                right_read_only=True,
            )
        )
        # InteractiveDiffScreen.dismiss(text) → APPROVED; dismiss(None) → REJECTED
        if result is not None:
            return ApprovalDecision.APPROVED
        return ApprovalDecision.REJECTED

    def show_completion_review(self, plan: Plan) -> None:
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

        self._run_screen(MessageScreen("Completion Review", "\n".join(lines)))

    # ------------------------------------------------------------------
    # Repository & profile display screens (finding 8.6)
    # ------------------------------------------------------------------

    def show_repository_analysis(self, repository_context: RepositoryContext) -> None:
        tree_lines = "\n".join(f"  {p}" for p in repository_context.tree[:100])
        config_lines = "\n".join(f"  {c}" for c in repository_context.config_files)
        msg = (
            f"Root: {repository_context.root}\n\n"
            f"Files ({len(repository_context.tree)}):\n{tree_lines or '  (empty)'}\n\n"
            f"Config files:\n{config_lines or '  (none)'}"
        )
        self._run_screen(MessageScreen("Repository Analysis", msg))

    def show_repository_understanding(
        self, repository_context: RepositoryContext
    ) -> None:
        msg = (
            f"Repository: {repository_context.root}\n\n"
            f"Total tracked paths: {len(repository_context.tree)}\n"
            f"Config/build files: {len(repository_context.config_files)}"
        )
        self._run_screen(MessageScreen("Repository Understanding", msg))

    def show_engineering_profile(self, profile: EngineeringProfile) -> None:
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
        self._run_screen(MessageScreen("Engineering Profile", msg))

    def show_memory(self, events: tuple[MemoryEvent, ...]) -> None:
        if events:
            lines = [f"  [{e.timestamp or '—'}] {e.kind}" for e in events[:50]]
            msg = f"Recent memory events ({len(events)}):\n\n" + "\n".join(lines)
        else:
            msg = "No memory events recorded yet."
        self._run_screen(MessageScreen("Memory Events", msg))

    def show_logs(self) -> None:
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
        self._run_screen(MessageScreen("Audit Logs", msg))

    def show_provider_config_screen(
        self, error_message: str | None = None, prefill: dict[str, str] | None = None
    ) -> dict[str, str] | None:
        """Present the provider configuration screen to the user."""
        res: dict[str, str] | None = self._run_screen(
            ProviderConfigScreen(error_message=error_message, prefill=prefill)
        )
        return res

    def show_loading(self, message: str) -> None:
        """Display a blocking loading overlay with a message."""
        self._app.call_from_thread(self._app.push_screen, LoadingScreen(message))

    def hide_loading(self) -> None:
        """Dismiss the active loading overlay."""
        self._app.call_from_thread(self._app.pop_screen)

    def stream_token(self, token: str) -> None:
        """Stream an LLM generation token directly to the UI."""

        def do_update() -> None:
            if isinstance(self._app.screen, LoadingScreen):
                self._app.screen.append_token(token)

        self._app.call_from_thread(do_update)
