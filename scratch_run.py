import sys
from pathlib import Path
from unittest.mock import patch

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
from corge.ui.cli import CliUi


def main():
    ui = CliUi()
    interactive = "--interactive" in sys.argv

    print("Tip: Run with --interactive to manually test UI inputs.\n")

    # 1. Spec Wizard
    print("\n--- Testing show_spec_wizard ---")
    if interactive:
        spec = ui.show_spec_wizard()
    else:
        with (
            patch("rich.prompt.Prompt.ask", return_value="Showcase Feature"),
            patch(
                "builtins.input",
                side_effect=[
                    "Story", "", "", "Reqs", "", "", "Constraints", "", "",
                    "AC 1\nAC 2", "", "", "Testing", "", "",
                ],
            ),
        ):
            spec = ui.show_spec_wizard()
    print(f"\nCreated Specification: {spec.title}")

    # Dummy Data for the new interactive components
    canvas = CanvasSnapshot(
        text="Brainstorming the Showcase Feature...\nWe need a database and an API.",
        timestamp="2026-06-20T12:00:00Z"
    )
    gaps = (SemanticGap(topic="Database Engine"), SemanticGap(topic="API Framework"))

    # 2. Argumentation Diff
    print("\n--- Testing show_argumentation_diff ---")
    if interactive:
        spec = ui.show_argumentation_diff(canvas, spec, gaps)
    else:
        with patch("builtins.input", side_effect=["PostgreSQL", "", "", "FastAPI", "", ""]):
            spec = ui.show_argumentation_diff(canvas, spec, gaps)

    # 3. Technical Plan Editor
    print("\n--- Testing show_tech_plan_editor ---")
    tech_plan = TechnicalPlan(
        content="Module 1: Database\nModule 2: API",
        specification_ref=spec.title
    )
    if interactive:
        tech_plan = ui.show_tech_plan_editor(tech_plan)
    else:
        with patch("rich.prompt.Confirm.ask", return_value=False):
            tech_plan = ui.show_tech_plan_editor(tech_plan)

    # 4. Procedural Steps Editor
    print("\n--- Testing show_procedural_steps_editor ---")
    proc_steps = (
        ProceduralStep(identifier="step-1", description="Init database"),
        ProceduralStep(identifier="step-2", description="Create API endpoints")
    )
    if interactive:
        proc_steps = ui.show_procedural_steps_editor(proc_steps)
    else:
        with patch("rich.prompt.Confirm.ask", return_value=False):
            proc_steps = ui.show_procedural_steps_editor(proc_steps)

    # 5. Plan Review
    print("\n--- Testing show_plan ---")
    plan = Plan(
        steps=(
            PlanStep(identifier="step-1", description="Create service layer"),
            PlanStep(identifier="step-2", description="Update controller"),
        ),
        specification_ref=spec.title,
    )
    ui.show_plan(plan)

    # 6. Approval Request
    print("\n--- Testing request_approval ---")
    req = ApprovalRequest(action="write", target="app/Service.py", reason="Step 1")
    if interactive:
        decision = ui.request_approval(req)
    else:
        with patch("rich.prompt.Confirm.ask", return_value=True):
            decision = ui.request_approval(req)
    print(f"You decided to: {decision}")

    # 7. Repository Analysis
    print("\n--- Testing show_repository_analysis ---")
    repo_ctx = RepositoryContext(
        root=Path("/projects/my-app"),
        tree=("app/Service.py", "app/Controller.py", "tests/test_service.py"),
        config_files=("pyproject.toml",),
    )
    ui.show_repository_analysis(repo_ctx)

    # 8. Repository Understanding
    print("\n--- Testing show_repository_understanding ---")
    ui.show_repository_understanding(repo_ctx)

    # 9. Execution Monitor
    print("\n--- Testing show_execution ---")
    ctx = ContextBundle(
        specification=spec,
        plan=plan,
        repository_context=repo_ctx,
        engineering_profile=EngineeringProfile(rules=("Use type hints", "Write unit tests")),
    )
    ui.show_execution(ctx)

    # 10. Logs
    print("\n--- Testing show_logs ---")
    ui.show_logs()

    # 11. Engineering Profile
    print("\n--- Testing show_engineering_profile ---")
    ui.show_engineering_profile(ctx.engineering_profile)

    # 12. Scenario Memory
    print("\n--- Testing show_memory ---")
    events = (
        MemoryEvent(kind="step_completed", payload={"step": "step-1"}),
        MemoryEvent(kind="blocker_encountered", payload={"reason": "permission error"}),
    )
    ui.show_memory(events)

    # 13. Completion Review
    print("\n--- Testing show_completion_review ---")
    ui.show_completion_review(plan)


if __name__ == "__main__":
    main()
