import sys
from pathlib import Path
from textual.app import App
from textual.worker import work

from corge.contracts import (
    ApprovalRequest,
    CanvasSnapshot,
    ContextBundle,
    EngineeringProfile,
    MemoryEvent,
    Plan,
    PlanStep,
    ProceduralStep,
    RepositoryContext,
    SemanticGap,
    TechnicalPlan,
)
from corge.ui.cli import CliUi, CorgeApp


class ScratchApp(CorgeApp):
    """App that runs the scratch loop in a worker thread."""

    def on_mount(self) -> None:
        self.run_scratch()

    @work(thread=True)
    def run_scratch(self) -> None:
        ui = CliUi(self)

        # 1. Spec Wizard
        spec = ui.show_spec_wizard()
        
        # Dummy Data
        canvas = CanvasSnapshot(
            text="Brainstorming...\nWe need a database.",
            timestamp="2026-06-20T12:00:00Z"
        )
        gaps = (SemanticGap(topic="Database Engine", description="Missing db"),)

        # 2. Argumentation Diff
        spec = ui.show_argumentation_diff(canvas, spec, gaps)

        # 3. Technical Plan Editor
        tech_plan = TechnicalPlan(
            content="Module 1: Database\nModule 2: API",
            specification_ref=spec.title
        )
        tech_plan = ui.show_tech_plan_editor(tech_plan)

        # 4. Procedural Steps Editor
        proc_steps = (
            ProceduralStep(identifier="step-1", description="Init database"),
            ProceduralStep(identifier="step-2", description="Create API endpoints")
        )
        proc_steps = ui.show_procedural_steps_editor(proc_steps)

        # 5. Plan Review
        plan = Plan(
            steps=(
                PlanStep(identifier="step-1", description="Create service layer"),
            ),
            specification_ref=spec.title,
        )
        ui.show_plan(plan)

        # 6. Approval Request
        req = ApprovalRequest(action="write", target="app/Service.py", reason="Step 1")
        decision = ui.request_approval(req)

        # 7-13. Other screens
        ui.show_completion_review(plan)
        
        # Exit when done
        self.call_from_thread(self.exit)


def main():
    app = ScratchApp()
    app.run()


if __name__ == "__main__":
    main()
