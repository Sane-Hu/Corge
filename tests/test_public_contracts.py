"""Public skeleton contract tests."""

from pathlib import Path

import pytest

from corge.agent import AgentService
from corge.approval import ApprovalGateway
from corge.artifacts import ArtifactStore
from corge.budget_manager import BudgetManager
from corge.context import ContextService
from corge.contracts import (
    AcceptanceCriteria,
    ApprovalDecision,
    ApprovalRequest,
    ArtifactReference,
    AuditEvent,
    ContextBundle,
    EngineeringProfile,
    GraphQuery,
    GraphUpdate,
    MemoryEvent,
    Plan,
    PlanStep,
    ProviderMessage,
    RepositoryContext,
    Specification,
    ToolAction,
    ToolResult,
)
from corge.knowledge_graph import KnowledgeGraph
from corge.logging import AuditLogger
from corge.memory import MemoryStore
from corge.prompt_assembler import PromptAssembler
from corge.providers import Provider
from corge.tools import ToolRuntime
from corge.ui import UiPort


def test_documented_public_classes_exist() -> None:
    expected_methods = {
        AgentService: {
            "generate_plan",
            "execute_step",
            "evaluate_completion",
            "update_memory",
        },
        UiPort: {
            "show_spec_wizard",
            "show_plan",
            "show_execution",
            "show_logs",
            "request_approval",
            "show_repository_analysis",
            "show_repository_understanding",
            "show_engineering_profile",
            "show_memory",
            "show_completion_review",
        },
        ContextService: {
            "load_context",
            "refresh_context",
            "retrieve_relevant_context",
        },
        PromptAssembler: {"collect_context", "assemble_prompt"},
        BudgetManager: {
            "estimate_tokens",
            "rank_context",
            "clip",
            "deduplicate",
            "summarize",
            "compact",
        },
        KnowledgeGraph: {"build_graph", "update_graph", "query_graph"},
        MemoryStore: {
            "store_event",
            "store_fact",
            "store_scenario",
            "update_profile",
        },
        ArtifactStore: {
            "store_artifact",
            "retrieve_artifact",
            "summarize_artifact",
        },
        ApprovalGateway: {"approve", "reject"},
        ToolRuntime: {"read", "write", "edit", "bash"},
        Provider: {"chat"},
        AuditLogger: {
            "record_prompt",
            "record_tool_call",
            "record_approval",
            "record_completion",
        },
    }

    for public_class, method_names in expected_methods.items():
        assert isinstance(public_class.__name__, str)
        for method_name in method_names:
            assert callable(getattr(public_class, method_name))


def test_stub_methods_raise_not_implemented() -> None:
    criteria = AcceptanceCriteria(items=("criterion",))
    specification = Specification(
        title="Skeleton",
        body="No feature behavior.",
        acceptance_criteria=criteria,
    )
    plan_step = PlanStep(identifier="step-1", description="Skeleton step.")
    plan = Plan(steps=(plan_step,))
    repository_context = RepositoryContext(root=Path("."))
    profile = EngineeringProfile(rules=("Preserve module boundaries.",))
    context_bundle = ContextBundle(
        specification=specification,
        plan=plan,
        repository_context=repository_context,
        engineering_profile=profile,
    )
    memory_event = MemoryEvent(kind="event")
    approval_request = ApprovalRequest(
        action=ToolAction.READ,
        target="AGENTS.md",
        reason="Skeleton test.",
    )
    artifact_reference = ArtifactReference(
        uri="artifact://test",
        summary="Skeleton artifact.",
    )
    tool_result = ToolResult(action=ToolAction.READ, output="")

    stub_calls = [
        lambda: AgentService().generate_plan(specification),
        lambda: AgentService().execute_step(plan_step, context_bundle),
        lambda: AgentService().evaluate_completion(plan, context_bundle),
        lambda: AgentService().update_memory(memory_event),
        lambda: UiPort().show_spec_wizard(),
        lambda: UiPort().show_plan(plan),
        lambda: UiPort().show_execution(context_bundle),
        lambda: UiPort().show_logs(),
        lambda: UiPort().request_approval(approval_request),
        lambda: UiPort().show_repository_analysis(repository_context),
        lambda: UiPort().show_repository_understanding(repository_context),
        lambda: UiPort().show_engineering_profile(profile),
        lambda: UiPort().show_memory((memory_event,)),
        lambda: UiPort().show_completion_review(plan),
        lambda: ContextService().load_context(repository_context),
        lambda: ContextService().refresh_context(repository_context),
        lambda: ContextService().retrieve_relevant_context(specification, plan_step),
        lambda: PromptAssembler().collect_context(plan_step),
        lambda: PromptAssembler().assemble_prompt(context_bundle),
        lambda: BudgetManager().estimate_tokens(context_bundle),
        lambda: BudgetManager().rank_context(context_bundle),
        lambda: BudgetManager().clip(context_bundle, 1000),
        lambda: BudgetManager().deduplicate(context_bundle),
        lambda: BudgetManager().summarize(context_bundle),
        lambda: BudgetManager().compact(context_bundle),
        lambda: KnowledgeGraph().build_graph(repository_context),
        lambda: KnowledgeGraph().update_graph(GraphUpdate(paths=(Path("."),))),
        lambda: KnowledgeGraph().query_graph(GraphQuery(expression="files")),
        lambda: MemoryStore().store_event(memory_event),
        lambda: MemoryStore().store_fact("fact"),
        lambda: MemoryStore().store_scenario(memory_event),
        lambda: MemoryStore().update_profile(profile),
        lambda: ArtifactStore().store_artifact(Path("log.txt"), "summary"),
        lambda: ArtifactStore().retrieve_artifact(artifact_reference),
        lambda: ArtifactStore().summarize_artifact(artifact_reference),
        lambda: ApprovalGateway().approve(approval_request),
        lambda: ApprovalGateway().reject(approval_request),
        lambda: ToolRuntime().read(Path("AGENTS.md")),
        lambda: ToolRuntime().write(Path("file.txt"), "content"),
        lambda: ToolRuntime().edit(Path("file.txt"), "old", "new"),
        lambda: ToolRuntime().bash("pytest", Path(".")),
        lambda: Provider().chat((ProviderMessage(role="user", content="hello"),)),
        lambda: AuditLogger().record_prompt("prompt"),
        lambda: AuditLogger().record_tool_call(tool_result),
        lambda: AuditLogger().record_approval(
            approval_request, ApprovalDecision.APPROVED
        ),
        lambda: AuditLogger().record_completion(AuditEvent(kind="complete")),
    ]

    for stub_call in stub_calls:
        with pytest.raises(NotImplementedError):
            stub_call()
