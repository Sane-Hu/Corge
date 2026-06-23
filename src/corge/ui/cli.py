"""Textual-based UI implementation for the UiPort.

Spec traceability:
    Tech-spec §5 — TUI Screen Map: CanvasScreen, InteractiveDiffScreen, MessageScreen
    Sysdesign §UI Module — pure presentation, zero business logic
"""

from __future__ import annotations

import concurrent.futures
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Static, TextArea, LoadingIndicator

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
    UiPort,
)
from corge.ui.freestyle_canvas import CanvasScreen
from corge.ui.interactive_diff import InteractiveDiffScreen
from corge.ui.provider_config import ProviderConfigScreen


class MessageScreen(Screen[None]):
    """Generic read-only dialog (spec §5 item 3 — MessageScreen).

    Used for: execution plan view, errors, completion review.
    """

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self._title, classes="title")
            yield TextArea(self._message, read_only=True)
            yield Button("Continue", id="continue", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue":
            self.dismiss(None)


class LoadingScreen(Screen[None]):
    """Generic loading indicator screen."""

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(classes="loading-container"):
            yield Static(self._message, classes="title")
            yield LoadingIndicator()


class CorgeApp(App[None]):
    """The main Textual application for Corge."""

    CSS = """
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
        border: round $primary;
        padding: 1 2;
    }
    """


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
        self, canvas: CanvasSnapshot, spec: Specification, gaps: tuple[SemanticGap, ...]
    ) -> Specification:
        right_text = f"Title: {spec.title}\n\n{spec.body}\n"
        if gaps:
            right_text += "\nUnresolved Gaps:\n"
            for gap in gaps:
                right_text += f"  • {gap.topic}\n"

        result_text = self._run_screen(
            InteractiveDiffScreen(
                left_title="Canvas",
                left_text=canvas.text,
                right_title="Specification",
                right_text=right_text,
                prompt_text="Resolve any gaps in the Specification.",
            )
        )
        return Specification(
            title=spec.title,
            body=result_text or spec.body,
            acceptance_criteria=spec.acceptance_criteria,
        )

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

    def show_tech_plan_editor(self, plan: TechnicalPlan) -> TechnicalPlan:
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
        return TechnicalPlan(
            content=result_text or plan.content,
            specification_ref=plan.specification_ref,
        )

    def show_procedural_steps_editor(
        self, steps: tuple[ProceduralStep, ...]
    ) -> tuple[ProceduralStep, ...]:
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

        new_steps = []
        step_count = 0
        for line in (result_text or "").strip().split("\n"):
            if line.strip():
                step_count += 1
                new_steps.append(
                    ProceduralStep(
                        identifier=f"step-{step_count}",
                        description=line.strip(),
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
            f"Step   : {request.step_ref or '—'}"
        )
        result = self._run_screen(
            InteractiveDiffScreen(
                left_title="Request Context",
                left_text="The agent requires authorization to perform an action.",
                right_title="Approval Request",
                right_text=detail,
                prompt_text="Review the requested action carefully.",
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
            from pathlib import Path

            log_path = Path(".agent/audit.jsonl")
            if log_path.exists():
                msg = log_path.read_text(encoding="utf-8")[-10000:]
            else:
                msg = "No logs found."
        except Exception as e:
            msg = f"Error loading logs: {e}"
        # todo: simplistic raw log dump; upgrade path: parse JSONL into
        # an interactive data table.
        self._run_screen(MessageScreen("Logs", msg))

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
