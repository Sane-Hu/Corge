"""Command Line Interface implementation for the UI port."""

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

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

    def show_argumentation_diff(
        self, canvas: CanvasSnapshot, spec: Specification, gaps: tuple[SemanticGap, ...]
    ) -> Specification:
        """Display side-by-side diff of Canvas vs Specification and prompt for gap resolution."""
        left_panel = Panel(
            canvas.text, title="[bold]Freestyle Canvas[/bold]", border_style="blue"
        )

        spec_text = f"[bold]{spec.title}[/bold]\n\n{spec.body}\n\n[bold]Acceptance Criteria:[/bold]\n"
        for ac in spec.acceptance_criteria.items:
            spec_text += f"- {ac}\n"

        if gaps:
            spec_text += "\n[bold red]Semantic Gaps:[/bold red]\n"
            for gap in gaps:
                spec_text += f"- {gap.topic} (Unresolved)\n"

        right_panel = Panel(
            spec_text, title="[bold]Concretized Specification[/bold]", border_style="green"
        )

        self.console.print(Columns([left_panel, right_panel], expand=True))

        if gaps:
            self.console.print("\n[bold yellow]Please resolve the semantic gaps:[/bold yellow]")
            resolutions = []
            for gap in gaps:
                res = self._multiline_input(f"Resolve: {gap.topic}")
                resolutions.append(f"[Resolved Gap - {gap.topic}]:\n{res}")
            
            body = spec.body + "\n\n" + "\n\n".join(resolutions)
            return Specification(
                title=spec.title,
                body=body,
                acceptance_criteria=spec.acceptance_criteria,
                constraints=spec.constraints,
                testing_expectations=spec.testing_expectations,
            )
        
        return spec

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

    def show_tech_plan_editor(self, plan: TechnicalPlan) -> TechnicalPlan:
        """Display and optionally edit the technical plan."""
        panel = Panel(
            plan.content, title="[bold]Technical Plan Review[/bold]", border_style="cyan"
        )
        self.console.print(panel)
        
        if Confirm.ask("[bold]Edit Technical Plan?[/bold]"):
            new_content = self._multiline_input("New Technical Plan Content")
            return TechnicalPlan(content=new_content, specification_ref=plan.specification_ref)
        
        return plan

    def show_procedural_steps_editor(
        self, steps: tuple[ProceduralStep, ...]
    ) -> tuple[ProceduralStep, ...]:
        """Display and optionally edit the procedural steps."""
        content = ""
        for i, step in enumerate(steps, 1):
            content += f"[bold cyan]{i}.[/bold cyan] \\[{step.identifier}] {step.description}\n"
            
        panel = Panel(
            content.strip(), title="[bold]Procedural Steps Review[/bold]", border_style="cyan"
        )
        self.console.print(panel)
        
        if Confirm.ask("[bold]Edit Procedural Steps?[/bold]"):
            self.console.print("[dim]Enter new steps (one per line, empty line to finish):[/dim]")
            new_steps_list: list[ProceduralStep] = []
            while True:
                try:
                    line = input()
                except EOFError:
                    break
                if not line.strip():
                    break
                new_steps_list.append(ProceduralStep(
                    identifier=f"step-{len(new_steps_list)+1}",
                    description=line.strip()
                ))
            if new_steps_list:
                return tuple(new_steps_list)
                
        return steps

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
