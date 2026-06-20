from pathlib import Path
from unittest.mock import patch

from corge.contracts import (
    ApprovalRequest,
    ContextBundle,
    EngineeringProfile,
    MemoryEvent,
    Plan,
    PlanStep,
    RepositoryContext,
)
from corge.ui.cli import CliUi


def main():
    ui = CliUi()

    # Mock interactive components to showcase the UI without manual inputs
    with (
        patch("rich.prompt.Prompt.ask", return_value="Showcase Feature"),
        patch(
            "builtins.input",
            side_effect=[
                "Story",
                "",
                "",
                "Reqs",
                "",
                "",
                "Constraints",
                "",
                "",
                "AC 1\nAC 2",
                "",
                "",
                "Testing",
                "",
                "",
            ],
        ),
        patch("rich.prompt.Confirm.ask", return_value=True),
    ):
        # 1. Spec Wizard
        print("\n--- Testing show_spec_wizard ---")
        spec = ui.show_spec_wizard()
        print(f"\nCreated Specification: {spec.title}")

        # 2. Plan Review
        print("\n--- Testing show_plan ---")
        plan = Plan(
            steps=(
                PlanStep(identifier="step-1", description="Create service layer"),
                PlanStep(identifier="step-2", description="Update controller"),
            ),
            specification_ref="Showcase Feature",
        )
        ui.show_plan(plan)

        # 3. Approval Request
        print("\n--- Testing request_approval ---")
        req = ApprovalRequest(
            action="write", target="app/Service.py", reason="Step 1"
        )
        decision = ui.request_approval(req)
        print(f"You decided to: {decision}")

    # 4. Repository Analysis
    print("\n--- Testing show_repository_analysis ---")
    repo_ctx = RepositoryContext(
        root=Path("/projects/my-app"),
        tree=("app/Service.py", "app/Controller.py", "tests/test_service.py"),
        config_files=("pyproject.toml",),
    )
    ui.show_repository_analysis(repo_ctx)

    # 5. Repository Understanding
    print("\n--- Testing show_repository_understanding ---")
    ui.show_repository_understanding(repo_ctx)

    # 6. Execution Monitor
    print("\n--- Testing show_execution ---")
    ctx = ContextBundle(
        specification=spec,
        plan=plan,
        repository_context=repo_ctx,
        engineering_profile=EngineeringProfile(
            rules=("Use type hints", "Write unit tests")
        ),
    )
    ui.show_execution(ctx)

    # 7. Logs
    print("\n--- Testing show_logs ---")
    ui.show_logs()

    # 8. Engineering Profile
    print("\n--- Testing show_engineering_profile ---")
    ui.show_engineering_profile(ctx.engineering_profile)

    # 9. Scenario Memory
    print("\n--- Testing show_memory ---")
    events = (
        MemoryEvent(kind="step_completed", payload={"step": "step-1"}),
        MemoryEvent(kind="blocker_encountered", payload={"reason": "permission error"}),
    )
    ui.show_memory(events)

    # 10. Completion Review
    print("\n--- Testing show_completion_review ---")
    ui.show_completion_review(plan)


if __name__ == "__main__":
    main()
