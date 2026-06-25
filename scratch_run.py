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
    ChatResponse,
    LifecycleState,
    Plan,
    PlanStep,
    ProceduralStep,
    ProviderMessage,
    ProviderPort,
    RepositoryContext,
    Specification,
    SpecState,
    TechnicalPlan,
)
from corge.knowledge_graph.graph import KnowledgeGraph
from corge.logging.argumentation_log import ArgumentationLog
from corge.logging.audit import AuditLogger
from corge.memory.store import MemoryStore
from corge.tools.runtime import ToolRuntime
from corge.ui.cli import CliUi, CorgeApp


from typing import Callable
class MockProvider(ProviderPort):
    def chat(self, messages: tuple[ProviderMessage, ...], on_token: Callable[[str], None] | None = None) -> ChatResponse:
        text = " ".join(m.content.lower() for m in messages)

        if "analyze the following canvas text" in text or "gaps" in text:
            return ChatResponse(
                content='```json\n[{"topic": "Mock Gap"}]\n```', usage={}
            )
        elif "concretize" in text or "structure" in text:
            content = (
                '```json\n{"title": "Mock Specification", '
                '"body": "This is a mock spec body.", '
                '"acceptance_criteria": ["Mock AC 1"], '
                '"constraints": "Mock constraints", '
                '"testing_expectations": "Mock expectations"}\n```'
            )
            return ChatResponse(content=content, usage={})
        elif "technical plan" in text:
            content = "Generated mock technical plan detailing the mock implementation."
            return ChatResponse(content=content, usage={})
        elif "procedural step" in text or "step-by-step" in text:
            return ChatResponse(content="1. Mock Step 1\n2. Mock Step 2", usage={})
        elif "execute" in text or "tool" in text:
            content = '```json\n{"done": true, "actions": []}\n```'
            return ChatResponse(content=content, usage={})
        elif "evaluate" in text or "acceptance" in text:
            content = '```json\n{"all_satisfied": true}\n```'
            return ChatResponse(content=content, usage={})

        return ChatResponse(content="Mocked Provider Response.", usage={})


class ScratchApp(CorgeApp):
    """App that runs the scratch loop in a worker thread."""

    def on_mount(self) -> None:
        self.run_scratch()

    @work(thread=True)
    def run_scratch(self) -> None:
        agent_dir = Path(".agent")
        agent_dir.mkdir(exist_ok=True)

        # 1. Instantiate concrete implementations
        mock_provider = MockProvider()
        knowledge_graph = KnowledgeGraph(agent_dir / "kg")
        memory_store = MemoryStore(Path.cwd())
        context_service = ContextService(knowledge_graph, memory_store, Path.cwd())
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
            provider=mock_provider,
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
                controller.set_empty_repo(False)
                controller.advance()

            elif controller.state == LifecycleState.REPOSITORY_ANALYSIS:
                bundle = context_service.load_context(
                    RepositoryContext(root=Path.cwd())
                )
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
                step = (
                    plan.steps[0]
                    if plan.steps
                    else PlanStep(identifier="mock", description="mock step")
                )
                bundle = context_service.retrieve_relevant_context(spec, step)
                ui.show_execution(bundle)

                for step in plan.steps:
                    controller.execute_step(step, bundle)
                    step.completed = True

                controller.advance()

            elif controller.state == LifecycleState.VERIFICATION:
                assert plan is not None
                assert spec is not None
                step = (
                    plan.steps[-1]
                    if plan.steps
                    else PlanStep(identifier="mock", description="mock step")
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

        # End loop, exit gracefully
        try:
            self.call_from_thread(self.exit)
        except Exception:
            pass


def main() -> None:
    app = ScratchApp()
    app.run()


if __name__ == "__main__":
    main()
