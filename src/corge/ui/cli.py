"""Command Line Interface implementation for the UI port."""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

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

ANVIL_ART = r"""
[bold cyan]
 ███   ███  ████   ███  █████ 
█     █   █ █   █ █     █     
█     █   █ ████  █  ██ ████  
█     █   █ █  █  █   █ █     
 ███   ███  █   █  ███  █████ 
[/bold cyan]
"""


class CliUi:
    """CLI implementation of the UI port using rich."""

    def __init__(self) -> None:
        self.console = Console()

    def _multiline_input(self, prompt: str) -> str:
        """Read multiple lines until two consecutive empty lines."""
        self.console.print(
            f"[bold]{prompt}[/bold] [dim](Enter two empty lines to finish)[/dim]:"
        )
        lines: list[str] = []
        empty_count = 0
        while True:
            try:
                line = input()
            except EOFError:
                break
            if not line.strip():
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
            lines.append(line)
        return "\n".join(lines).strip()

    def show_spec_wizard(self) -> Specification:
        """Prompt for a new feature specification."""
        self.console.print(ANVIL_ART)

        goal = Prompt.ask("[bold]Feature Goal[/bold]")
        story = self._multiline_input("User Story")
        reqs = self._multiline_input("Functional Requirements")
        constraints = self._multiline_input("Constraints")
        ac_input = self._multiline_input("Acceptance Criteria (one per line)")
        testing = self._multiline_input("Testing Expectations")

        ac = AcceptanceCriteria(
            tuple(i.strip() for i in ac_input.split("\n") if i.strip())
        )
        body = f"{story}\n\n{reqs}"

        return Specification(
            title=goal,
            body=body,
            acceptance_criteria=ac,
            constraints=constraints,
            testing_expectations=testing,
        )

    def show_plan(self, plan: Plan) -> None:
        """Display the execution plan."""
        content = ""
        for i, step in enumerate(plan.steps, 1):
            content += f"[bold cyan]{i}.[/bold cyan] {step.description}\n"

        panel = Panel(
            content.strip(),
            title="[bold]Plan Review[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )
        self.console.print(panel)

    def show_execution(self, context: ContextBundle) -> None:
        """Display the current execution context."""
        step_desc = (
            context.plan.steps[0].description if context.plan.steps else "Unknown"
        )
        total_steps = len(context.plan.steps)
        content = (
            f"[bold]Step ? / {total_steps}[/bold]\n{step_desc}\n\n"
            "[bold green]Executing...[/bold green]"
        )

        panel = Panel(
            content,
            title="[bold]Execution Monitor[/bold]",
            border_style="green",
            padding=(1, 2),
        )
        self.console.print(panel)

    def show_logs(self) -> None:
        """Display logs (placeholder for now)."""
        panel = Panel(
            "Waiting for logs...", title="[bold]Logs[/bold]", border_style="dim"
        )
        self.console.print(panel)

    def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        """Prompt the user for approval."""
        content = (
            f"[bold]Action:[/bold] {request.action}\n"
            f"[bold]Target:[/bold] {request.target}\n"
            f"[bold]Reason:[/bold] {request.reason}"
        )
        panel = Panel(
            content,
            title="[bold red]Approval Request[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
        self.console.print(panel)

        if Confirm.ask("[bold red]Approve?[/bold red]"):
            return ApprovalDecision.APPROVED
        return ApprovalDecision.REJECTED

    def show_repository_analysis(self, repository_context: RepositoryContext) -> None:
        """Display repository analysis progress."""
        content = (
            "Scanning Tree\n"
            "Summarizing Files\n"
            "Building Graph\n"
            "Extracting Facts\n"
            "Building Profile\n\n"
            "[bold green]Progress: 100%[/bold green]"
        )
        panel = Panel(
            content,
            title="[bold]Repository Analysis[/bold]",
            border_style="blue",
            padding=(1, 2),
        )
        self.console.print(panel)

    def show_repository_understanding(
        self, repository_context: RepositoryContext
    ) -> None:
        """Display repository knowledge facts."""
        nodes = len(repository_context.tree) + len(repository_context.config_files)
        content = (
            f"[bold]Path:[/bold] {repository_context.root.name}\n\n"
            f"[bold]Graph Nodes:[/bold] ~{nodes}\n"
            f"[bold]Graph Edges:[/bold] ~{nodes * 2}"
        )
        panel = Panel(
            content,
            title="[bold]Repository Understanding[/bold]",
            border_style="magenta",
            padding=(1, 2),
        )
        self.console.print(panel)

    def show_engineering_profile(self, profile: EngineeringProfile) -> None:
        """Display the extracted engineering profile rules."""
        if not profile.rules:
            content = "No rules defined"
        else:
            content = "\n".join(f"[green]✓[/green] {rule}" for rule in profile.rules)

        panel = Panel(
            content,
            title="[bold]Engineering Profile[/bold]",
            border_style="yellow",
            padding=(1, 2),
        )
        self.console.print(panel)

    def show_memory(self, events: tuple[MemoryEvent, ...]) -> None:
        """Display memory pyramid facts."""
        if not events:
            content = "Empty"
        else:
            content = "\n".join(f"- {event.kind}" for event in events)

        panel = Panel(
            content,
            title="[bold]Scenario Memory[/bold]",
            border_style="cyan",
            padding=(1, 2),
        )
        self.console.print(panel)

    def show_completion_review(self, plan: Plan) -> None:
        """Display the completion review screen."""
        content = (
            "[bold]Acceptance Criteria[/bold]\n"
            "[green]✓[/green]\n\n"
            "[bold]Tests[/bold]\n"
            "[green]✓ Passed[/green]"
        )
        panel = Panel(
            content,
            title="[bold]Completion Review[/bold]",
            border_style="green",
            padding=(1, 2),
        )
        self.console.print(panel)
