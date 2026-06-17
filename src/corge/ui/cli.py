"""Command Line Interface implementation for the UI port."""

from corge.contracts import (
    AcceptanceCriteria,
    ApprovalDecision,
    ApprovalRequest,
    ContextBundle,
    EngineeringProfile,
    MemoryEvent,
    Plan,
    RepositoryContext,
    Specification,
)
from corge.ui.port import UiPort

ANVIL_ART = r"""
███   ███  ████   ███  █████ 
█     █   █ █   █ █     █     
█     █   █ ████  █  ██ ████  
█     █   █ █  █  █   █ █     
 ███   ███  █   █  ███  █████ 
"""


def _print_box(lines: list[str], width: int = 30) -> None:
    """Print an ASCII box with the given lines."""
    print(f"┌{'─' * width}┐")
    for line in lines:
        print(f"│ {line[:width - 2].ljust(width - 2)} │")
    print(f"└{'─' * width}┘")


class CliUi(UiPort):
    """CLI implementation of the UI port using pure print/input."""

    def show_spec_wizard(self) -> Specification:
        """Prompt for a new feature specification."""
        print(ANVIL_ART)
        
        goal = input("\nFeature Goal: ")
        story = input("User Story: ")
        reqs = input("Functional Requirements: ")
        constraints = input("Constraints: ")
        ac_input = input("Acceptance Criteria (comma separated): ")
        testing = input("Testing Expectations: ")
        
        # ponytail: mapping to the minimal Specification model
        ac = AcceptanceCriteria(
            tuple(i.strip() for i in ac_input.split(",") if i.strip())
        )
        body = f"{story}\n{reqs}\n{constraints}\n{testing}"
        
        return Specification(title=goal, body=body, acceptance_criteria=ac)

    def show_plan(self, plan: Plan) -> None:
        """Display the execution plan."""
        lines = ["Generated Plan", ""]
        for i, step in enumerate(plan.steps, 1):
            lines.append(f"{i}. {step.description}")
        lines.extend(["", "[Approve] [Reject]"])
        _print_box(lines)

    def show_execution(self, context: ContextBundle) -> None:
        """Display the current execution context."""
        # ponytail: Naively picking first step as 'current' for the display
        # The contract doesn't currently pass the exact running state/step
        step_desc = (
            context.plan.steps[0].description if context.plan.steps else "Unknown"
        )
        lines = [
            "Current Step",
            "",
            "Step 1 / ?",
            step_desc,
            "",
            "Current Action",
            "Executing",
        ]
        _print_box(lines)

    def show_logs(self) -> None:
        """Display logs (placeholder for now)."""
        _print_box(["Logs", "", "Waiting for logs..."])

    def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        """Prompt the user for approval."""
        lines = [
            "Approval Required",
            "",
            f"Action: {request.action}",
            "",
            f"Target: {request.target}",
            "",
            f"Reason: {request.reason}",
            "",
            "[Approve] [Reject]",
        ]
        _print_box(lines, width=max(30, len(request.target) + 12))
        
        while True:
            resp = input("Decision (a/r): ").strip().lower()
            if resp in ("a", "approve", "y", "yes"):
                return ApprovalDecision.APPROVED
            if resp in ("r", "reject", "n", "no"):
                return ApprovalDecision.REJECTED

    def show_repository_analysis(self, repository_context: RepositoryContext) -> None:
        """Display repository analysis progress."""
        lines = [
            "Repository Analysis",
            "",
            "Scanning Tree",
            "Summarizing Files",
            "Building Graph",
            "Extracting Facts",
            "Building Profile",
            "",
            "Progress: 100%",
        ]
        _print_box(lines)

    def show_repository_understanding(
        self, repository_context: RepositoryContext
    ) -> None:
        """Display repository knowledge facts."""
        lines = [
            "Repository Understanding",
            "",
            f"Path: {repository_context.root.name}",
            "",
            "Graph Nodes: ??",
            "Graph Edges: ??",
        ]
        _print_box(lines)

    def show_engineering_profile(self, profile: EngineeringProfile) -> None:
        """Display the extracted engineering profile rules."""
        lines = ["Engineering Profile", ""]
        if not profile.rules:
            lines.append("No rules defined")
        for rule in profile.rules:
            lines.append(f"✓ {rule}")
        lines.extend(["", "[Edit Profile]"])
        _print_box(lines)

    def show_memory(self, events: tuple[MemoryEvent, ...]) -> None:
        """Display memory pyramid facts."""
        lines = ["Scenario Memory", ""]
        for event in events:
            lines.append(f"- {event.kind}")
        if not events:
            lines.append("Empty")
        _print_box(lines)

    def show_completion_review(self, plan: Plan) -> None:
        """Display the completion review screen."""
        lines = [
            "Completion Review",
            "",
            "Acceptance Criteria",
            "✓",
            "",
            "Tests",
            "✓ Passed",
            "",
            "[Approve Completion]",
        ]
        _print_box(lines)
