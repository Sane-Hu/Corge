"""Corge command-line entrypoint.

Traces to docs/02-technical-spec.md and docs/04-functional_testing.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

from textual import work

from corge.agent.bayesian_updater import BayesianUpdater
from corge.agent.schema_tailor import SchemaTailor
from corge.agent.session_controller import SessionController
from corge.approval.gateway import ApprovalGateway
from corge.budget_manager.manager import BudgetManager
from corge.context.service import ContextService
from corge.context.sticky_validator import StickyNoteValidator
from corge.contracts import (
    CanvasSnapshot,
    LifecycleState,
    Plan,
    PlanStep,
    ProceduralStep,
    RepositoryContext,
    Specification,
    SpecState,
    TechnicalPlan,
)
from corge.knowledge_graph.graph import KnowledgeGraph
from corge.logging.argumentation_log import ArgumentationLog
from corge.logging.audit import AuditLogger
from corge.memory.store import MemoryStore
from corge.providers.provider import bootstrap_provider
from corge.tools.runtime import ToolRuntime
from corge.ui.cli import CliUi, CorgeApp


class RealCorgeApp(CorgeApp):
    """Main Textual application orchestration run loop using the real provider."""

    def __init__(self, target_repo: Path, config_path: Path) -> None:
        super().__init__()
        self.target_repo = target_repo.resolve()
        self.config_path = config_path.resolve()

    def on_mount(self) -> None:
        self.run_session()

    @work(thread=True)
    def run_session(self) -> None:
        agent_dir = self.target_repo / ".agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        # 1. Instantiate concrete implementations
        provider = bootstrap_provider(self.config_path)
        knowledge_graph = KnowledgeGraph(agent_dir / "kg")
        memory_store = MemoryStore(self.target_repo)
        context_service = ContextService(
            knowledge_graph, memory_store, self.target_repo
        )
        schema_tailor = SchemaTailor(knowledge_graph)
        budget_manager = BudgetManager()
        audit_logger = AuditLogger(agent_dir)
        argumentation_log = ArgumentationLog(agent_dir)
        tool_runtime = ToolRuntime()

        validator = StickyNoteValidator(knowledge_graph)
        ui = CliUi(self, validator)
        approval_gateway = ApprovalGateway(ui, audit_logger)
        heuristic_updater = BayesianUpdater(agent_dir, argumentation_log)

        controller = SessionController(
            provider=provider,
            tool_runtime=tool_runtime,
            approval_gateway=approval_gateway,
            context_service=context_service,
            memory_store=memory_store,
            heuristic_updater=heuristic_updater,
            knowledge_graph=knowledge_graph,
            schema_tailor=schema_tailor,
            budget_manager=budget_manager,
        )

        spec: Specification | None = None
        tech_plan: TechnicalPlan | None = None
        proc_steps: tuple[ProceduralStep, ...] = ()
        plan: Plan | None = None

        while controller.state != LifecycleState.DONE:
            if controller.state == LifecycleState.START:
                controller.advance()

            elif controller.state == LifecycleState.REPOSITORY_SELECTION:
                is_empty = True
                if self.target_repo.exists():
                    for child in self.target_repo.iterdir():
                        if child.name not in (".git", ".agent"):
                            is_empty = False
                            break
                controller.set_empty_repo(is_empty)
                controller.advance()

            elif controller.state == LifecycleState.REPOSITORY_ANALYSIS:
                bundle = context_service.load_context(
                    RepositoryContext(root=self.target_repo)
                )
                if not controller.is_empty_repo:
                    knowledge_graph.build_graph(bundle.repository_context)
                ui.show_repository_understanding(bundle.repository_context)
                controller.advance()

            elif controller.state == LifecycleState.SPEC_ENTRY:
                spec = ui.show_spec_wizard()
                controller.advance()

            elif controller.state == LifecycleState.SPEC_VALIDATION:
                assert spec is not None
                spec, gaps = controller.run_socratic_loop(
                    spec.body, argumentation_log, ui
                )

                if gaps:
                    controller.advance_spec_state(SpecState.ARGUMENTATION_DIFF)
                    canvas = CanvasSnapshot(text=spec.body, timestamp="now")
                    spec = ui.show_argumentation_diff(canvas, spec, gaps)

                controller.advance()

            elif controller.state == LifecycleState.SPEC_APPROVAL:
                controller.advance()

            elif controller.state == LifecycleState.PLAN_GENERATION:
                assert spec is not None
                tech_plan = controller.generate_technical_plan(spec)
                tech_plan = ui.show_tech_plan_editor(tech_plan)
                controller.advance()

            elif controller.state == LifecycleState.PLAN_REVIEW:
                assert tech_plan is not None
                assert spec is not None
                proc_steps = controller.generate_procedural_steps(tech_plan)
                proc_steps = ui.show_procedural_steps_editor(proc_steps)

                plan = Plan(
                    steps=tuple(
                        PlanStep(identifier=s.identifier, description=s.description)
                        for s in proc_steps
                    ),
                    specification_ref=spec.title,
                )
                ui.show_plan(plan)
                controller.advance()

            elif controller.state == LifecycleState.PLAN_APPROVAL:
                controller.advance()

            elif controller.state == LifecycleState.EXECUTION:
                assert spec is not None
                assert plan is not None

                import dataclasses

                updated_steps = list(plan.steps)
                for i, step in enumerate(plan.steps):
                    bundle = context_service.retrieve_relevant_context(spec, step)
                    ui.show_execution(bundle)
                    controller.execute_step(step, bundle)
                    updated_steps[i] = dataclasses.replace(step, completed=True)

                plan = dataclasses.replace(plan, steps=tuple(updated_steps))
                controller.advance()

            elif controller.state == LifecycleState.VERIFICATION:
                assert plan is not None
                assert spec is not None
                step = plan.steps[-1] if plan.steps else PlanStep(
                    identifier="verification",
                    description="Verification of acceptance criteria",
                )
                bundle = context_service.retrieve_relevant_context(spec, step)
                controller.evaluate_completion(plan, bundle)
                controller.advance()

            elif controller.state == LifecycleState.COMPLETION_REVIEW:
                assert plan is not None
                ui.show_completion_review(plan)
                controller.advance()

            else:
                break

        try:
            self.call_from_thread(self.exit)
        except Exception:
            pass


def main() -> None:
    """CLI entrypoint function."""
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1]).resolve()
    else:
        from corge.ui.directory_selector import choose_directory_cli
        target_path = choose_directory_cli()

    if not target_path.exists():
        print(f"Error: Target path '{target_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    config_path = Path("config.toml").resolve()
    try:
        app = RealCorgeApp(target_repo=target_path, config_path=config_path)
        app.run()
    except (FileNotFoundError, ValueError, ConnectionError) as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
