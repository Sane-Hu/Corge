"""Public contract tests: models, protocols, and stub coverage."""

from pathlib import Path

import pytest

from corge.agent import SessionController
from corge.approval import ApprovalGateway
from corge.artifacts import ArtifactStore
from corge.budget_manager import BudgetManager
from corge.context import ContextService
from corge.contracts import (
    AcceptanceCriteria,
    AgentPort,
    ApprovalGatewayPort,
    ApprovalRequest,
    ArtifactReference,
    ArtifactStorePort,
    AuditEvent,
    AuditLoggerPort,
    BudgetManagerPort,
    ChatResponse,
    ContextBundle,
    ContextPort,
    EngineeringProfile,
    KnowledgeGraphPort,
    MemoryEvent,
    MemoryStorePort,
    Plan,
    PlanStep,
    PromptAssemblerPort,
    ProviderPort,
    RepositoryContext,
    Specification,
    ToolAction,
    ToolResult,
    ToolRuntimePort,
    UiPort,
)
from corge.knowledge_graph import KnowledgeGraph
from corge.logging import AuditLogger
from corge.memory import MemoryStore
from corge.prompt_assembler import PromptAssembler
from corge.providers import Provider
from corge.tools import ToolRuntime
from corge.ui import CliUi

# -- Fixtures for reuse across tests ------------------------------------------


@pytest.fixture()
def criteria() -> AcceptanceCriteria:
    return AcceptanceCriteria(items=("criterion",))


@pytest.fixture()
def specification(criteria: AcceptanceCriteria) -> Specification:
    return Specification(
        title="Skeleton",
        body="No feature behavior.",
        acceptance_criteria=criteria,
    )


@pytest.fixture()
def plan_step() -> PlanStep:
    return PlanStep(identifier="step-1", description="Skeleton step.")


@pytest.fixture()
def plan(plan_step: PlanStep) -> Plan:
    return Plan(steps=(plan_step,))


@pytest.fixture()
def repository_context() -> RepositoryContext:
    return RepositoryContext(root=Path("."))


@pytest.fixture()
def profile() -> EngineeringProfile:
    return EngineeringProfile(rules=("Preserve module boundaries.",))


@pytest.fixture()
def context_bundle(
    specification: Specification,
    plan: Plan,
    repository_context: RepositoryContext,
    profile: EngineeringProfile,
) -> ContextBundle:
    return ContextBundle(
        specification=specification,
        plan=plan,
        repository_context=repository_context,
        engineering_profile=profile,
    )


@pytest.fixture()
def memory_event() -> MemoryEvent:
    return MemoryEvent(kind="event")


@pytest.fixture()
def approval_request() -> ApprovalRequest:
    return ApprovalRequest(
        action=ToolAction.READ,
        target="AGENTS.md",
        reason="Skeleton test.",
    )


@pytest.fixture()
def artifact_reference() -> ArtifactReference:
    return ArtifactReference(uri="artifact://test", summary="Skeleton artifact.")


@pytest.fixture()
def tool_result() -> ToolResult:
    return ToolResult(action=ToolAction.READ, output="")


# -- Protocol structural subtyping checks ------------------------------------


_PROTOCOL_IMPL_PAIRS: list[tuple[type, type]] = [
    (UiPort, CliUi),
    (AgentPort, SessionController),
    (ContextPort, ContextService),
    (PromptAssemblerPort, PromptAssembler),
    (BudgetManagerPort, BudgetManager),
    (KnowledgeGraphPort, KnowledgeGraph),
    (MemoryStorePort, MemoryStore),
    (ArtifactStorePort, ArtifactStore),
    (ApprovalGatewayPort, ApprovalGateway),
    (ToolRuntimePort, ToolRuntime),
    (ProviderPort, Provider),
    (AuditLoggerPort, AuditLogger),
]


@pytest.mark.parametrize(
    ("protocol", "impl"),
    _PROTOCOL_IMPL_PAIRS,
    ids=[f"{p.__name__}<-{i.__name__}" for p, i in _PROTOCOL_IMPL_PAIRS],
)
def test_concrete_satisfies_protocol(protocol: type, impl: type) -> None:
    """Every concrete class is a structural subtype of its protocol."""
    instance = object.__new__(impl)
    assert isinstance(instance, protocol)


# -- Documented method existence checks ---------------------------------------


def test_documented_public_classes_exist() -> None:
    expected_methods = {
        SessionController: {
            "analyze_specification_gaps",
            "generate_technical_plan",
            "generate_procedural_steps",
            "execute_step",
            "evaluate_completion",
            "update_memory",
        },
        CliUi: {
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
            "get_facts",
            "get_scenario",
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


# -- Stub methods raise NotImplementedError -----------------------------------


# (test_stub_methods_raise_not_implemented removed; no stubs remain)


def test_artifact_store_lifecycle(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello", encoding="utf-8")
    ref = store.store_artifact(test_file, "test summary")
    assert ref.uri.startswith("artifact://")
    assert store.summarize_artifact(ref) == "test summary"
    assert store.retrieve_artifact(ref) == "hello"


def test_tool_runtime_lifecycle(tmp_path: Path) -> None:
    runtime = ToolRuntime()
    test_file = tmp_path / "tool_test.txt"

    # Test write
    res = runtime.write(test_file, "initial")
    assert res.success is True
    assert test_file.read_text(encoding="utf-8") == "initial"

    # Test read
    res_read = runtime.read(test_file)
    assert res_read.success is True
    assert res_read.output == "initial"

    # Test edit
    res_edit = runtime.edit(test_file, "initial", "edited")
    assert res_edit.success is True
    assert test_file.read_text(encoding="utf-8") == "edited"


# -- Model construction with new fields --------------------------------------


def test_specification_new_fields() -> None:
    spec = Specification(
        title="Test",
        body="Body",
        acceptance_criteria=AcceptanceCriteria(items=("a",)),
        constraints="No external deps",
        testing_expectations="Unit tests required",
    )
    assert spec.constraints == "No external deps"
    assert spec.testing_expectations == "Unit tests required"


def test_plan_step_action_and_target() -> None:
    step = PlanStep(
        identifier="s1",
        description="Write file",
        action=ToolAction.WRITE,
        target="src/main.py",
    )
    assert step.action is ToolAction.WRITE
    assert step.target == "src/main.py"


def test_plan_specification_ref() -> None:
    plan = Plan(steps=(), specification_ref="Add logging")
    assert plan.specification_ref == "Add logging"


def test_repository_context_tree_and_config() -> None:
    ctx = RepositoryContext(
        root=Path("/repo"),
        tree=("src/main.py", "README.md"),
        config_files=("pyproject.toml",),
    )
    assert len(ctx.tree) == 2
    assert ctx.config_files == ("pyproject.toml",)


def test_engineering_profile_confidence() -> None:
    profile = EngineeringProfile(
        rules=("Use DTOs",),
        confidence={"Use DTOs": 0.93},
    )
    assert profile.confidence["Use DTOs"] == pytest.approx(0.93)


def test_context_bundle_tier_fields() -> None:
    mem = MemoryEvent(kind="scenario")
    ref = ArtifactReference(uri="artifact://x", summary="s")
    bundle = ContextBundle(
        specification=Specification(
            title="t", body="b", acceptance_criteria=AcceptanceCriteria(items=())
        ),
        plan=Plan(steps=()),
        repository_context=RepositoryContext(root=Path(".")),
        engineering_profile=EngineeringProfile(),
        scenario_memory=(mem,),
        relevant_files=("src/a.py",),
        recent_actions=("read src/a.py",),
        artifact_refs=(ref,),
    )
    assert len(bundle.scenario_memory) == 1
    assert bundle.relevant_files == ("src/a.py",)
    assert bundle.recent_actions == ("read src/a.py",)
    assert bundle.artifact_refs[0].uri == "artifact://x"


def test_tool_result_success_and_stderr() -> None:
    ok = ToolResult(action=ToolAction.READ, output="content")
    assert ok.success is True
    assert ok.stderr == ""

    fail = ToolResult(action=ToolAction.BASH, output="", success=False, stderr="exit 1")
    assert fail.success is False
    assert fail.stderr == "exit 1"


def test_memory_event_timestamp() -> None:
    ev = MemoryEvent(kind="fact", timestamp="2026-06-17T18:00:00Z")
    assert ev.timestamp == "2026-06-17T18:00:00Z"


def test_audit_event_timestamp() -> None:
    ev = AuditEvent(kind="complete", timestamp="2026-06-17T18:00:00Z")
    assert ev.timestamp == "2026-06-17T18:00:00Z"


def test_approval_request_step_ref() -> None:
    req = ApprovalRequest(
        action=ToolAction.WRITE,
        target="file.py",
        reason="Plan step",
        step_ref="step-3",
    )
    assert req.step_ref == "step-3"


def test_chat_response_usage() -> None:
    resp = ChatResponse(content="hello", usage={"prompt": 100, "completion": 42})
    assert resp.usage["completion"] == 42


# -- Immutability checks ------------------------------------------------------


def test_models_are_frozen() -> None:
    spec = Specification(
        title="t",
        body="b",
        acceptance_criteria=AcceptanceCriteria(items=()),
    )
    with pytest.raises(AttributeError):
        spec.title = "changed"  # type: ignore[misc]

    step = PlanStep(identifier="s", description="d")
    with pytest.raises(AttributeError):
        step.identifier = "changed"  # type: ignore[misc]

    result = ToolResult(action=ToolAction.READ, output="x")
    with pytest.raises(AttributeError):
        result.success = False  # type: ignore[misc]
