"""Textual-based UI implementation for the UiPort."""

import concurrent.futures
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Static, TextArea

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
    TechnicalPlan,
    UiPort,
)
from corge.ui.freestyle_canvas import CanvasScreen
from corge.ui.interactive_diff import InteractiveDiffScreen


class MessageScreen(Screen):
    """Generic screen to display a message and wait for acknowledgment."""
    
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


class CorgeApp(App):
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
    """


class CliUi(UiPort):
    """Thread-safe UI port that delegates to the Textual app."""

    def __init__(self, app: CorgeApp) -> None:
        self.app = app

    def _run_screen(self, screen: Screen) -> Any:
        future: concurrent.futures.Future = concurrent.futures.Future()
        
        def callback(result: Any) -> None:
            future.set_result(result)
            
        self.app.call_from_thread(self.app.push_screen, screen, callback)
        return future.result()

    def show_spec_wizard(self) -> Specification:
        text = self._run_screen(CanvasScreen())
        # Parse basic spec from canvas text
        return Specification(
            title="Brainstormed Feature",
            body=text,
            acceptance_criteria=AcceptanceCriteria(items=("Passes all tests",)),
        )

    def show_argumentation_diff(
        self, canvas: CanvasSnapshot, spec: Specification, gaps: tuple[SemanticGap, ...]
    ) -> Specification:
        right_text = f"Title: {spec.title}\n\n{spec.body}\n"
        if gaps:
            right_text += "\nUnresolved Gaps:\n"
            for gap in gaps:
                right_text += f"- {gap.topic}\n"

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
            body=result_text,
            acceptance_criteria=spec.acceptance_criteria,
        )

    def show_plan(self, plan: Plan) -> None:
        msg = "\n".join(f"{i}. {s.description}" for i, s in enumerate(plan.steps, 1))
        self._run_screen(MessageScreen("Execution Plan", msg))

    def show_tech_plan_editor(self, plan: TechnicalPlan) -> TechnicalPlan:
        result_text = self._run_screen(
            InteractiveDiffScreen(
                left_title="Previous Context",
                left_text="Technical plan draft.",
                right_title="Technical Plan",
                right_text=plan.content,
            )
        )
        return TechnicalPlan(
            content=result_text, specification_ref=plan.specification_ref
        )

    def show_procedural_steps_editor(
        self, steps: tuple[ProceduralStep, ...]
    ) -> tuple[ProceduralStep, ...]:
        steps_text = "\n".join(f"[{s.identifier}] {s.description}" for s in steps)
        result_text = self._run_screen(
            InteractiveDiffScreen(
                left_title="Technical Plan",
                left_text="(Refer to Tech Plan)",
                right_title="Procedural Steps",
                right_text=steps_text,
            )
        )
        
        new_steps = []
        for i, line in enumerate(result_text.strip().split("\n"), 1):
            if line.strip():
                new_steps.append(ProceduralStep(identifier=f"step-{i}", description=line.strip()))
        return tuple(new_steps)

    def show_execution(self, context: ContextBundle) -> None:
        # We don't block for execution monitor, we just update the UI (if we had a persistent widget)
        pass

    def show_logs(self) -> None:
        pass

    def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        msg = f"Action: {request.action}\nTarget: {request.target}\nReason: {request.reason}"
        result = self._run_screen(InteractiveDiffScreen(
            left_title="Request Context",
            left_text="System requires approval.",
            right_title="Approval Request",
            right_text=msg,
        ))
        # If dismissed via approve button, result is the text. We treat it as APPROVED.
        if result is not None:
            return ApprovalDecision.APPROVED
        return ApprovalDecision.REJECTED

    def show_repository_analysis(self, repository_context: RepositoryContext) -> None:
        pass

    def show_repository_understanding(self, repository_context: RepositoryContext) -> None:
        pass

    def show_engineering_profile(self, profile: EngineeringProfile) -> None:
        pass

    def show_memory(self, events: tuple[MemoryEvent, ...]) -> None:
        pass

    def show_completion_review(self, plan: Plan) -> None:
        self._run_screen(MessageScreen("Completion Review", "All tasks completed successfully."))
