"""Protocol interfaces for every Corge module boundary.

Each protocol defines the contract a module must satisfy.  Modules
depend on these protocols (via ``contracts``), never on each other's
concrete classes.  This enforces the modular monolith boundary
documented in 03-system-architecture and 04-module-contracts.

All protocols are ``runtime_checkable`` so structural subtyping can
be verified in tests without importing concrete implementations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from corge.contracts.models import (
    ApprovalDecision,
    ApprovalRequest,
    ArgumentationEntry,
    ArtifactReference,
    AuditEvent,
    CanvasSnapshot,
    ChatResponse,
    ContextBundle,
    EngineeringProfile,
    GraphQuery,
    GraphResult,
    GraphUpdate,
    HeuristicConfig,
    MemoryEvent,
    Plan,
    PlanStep,
    ProceduralStep,
    ProviderMessage,
    RepositoryContext,
    SemanticGap,
    Specification,
    TechnicalPlan,
    ToolResult,
)

# ---------------------------------------------------------------------------
# UI (04-module-contracts § ui) — no business logic
# ---------------------------------------------------------------------------


@runtime_checkable
class UiPort(Protocol):
    """Presentation layer boundary."""

    def show_spec_wizard(self) -> Specification: ...

    def show_argumentation_diff(
        self, canvas: CanvasSnapshot, spec: Specification, gaps: tuple[SemanticGap, ...]
    ) -> Specification: ...

    def show_plan(self, plan: Plan) -> None: ...

    def show_tech_plan_editor(self, plan: TechnicalPlan) -> TechnicalPlan: ...

    def show_procedural_steps_editor(
        self, steps: tuple[ProceduralStep, ...]
    ) -> tuple[ProceduralStep, ...]: ...

    def show_execution(self, context: ContextBundle) -> None: ...

    def show_logs(self) -> None: ...

    def request_approval(self, request: ApprovalRequest) -> ApprovalDecision: ...

    def show_repository_analysis(
        self, repository_context: RepositoryContext
    ) -> None: ...

    def show_repository_understanding(
        self, repository_context: RepositoryContext
    ) -> None: ...

    def show_engineering_profile(self, profile: EngineeringProfile) -> None: ...

    def show_memory(self, events: tuple[MemoryEvent, ...]) -> None: ...

    def show_completion_review(self, plan: Plan) -> None: ...


# ---------------------------------------------------------------------------
# Agent (04-module-contracts § agent)
# ---------------------------------------------------------------------------


@runtime_checkable
class AgentPort(Protocol):
    """Planning and execution orchestration boundary."""

    def analyze_specification_gaps(
        self, canvas_text: str
    ) -> tuple[SemanticGap, ...]: ...

    def generate_technical_plan(
        self, specification: Specification
    ) -> TechnicalPlan: ...

    def generate_procedural_steps(
        self, technical_plan: TechnicalPlan
    ) -> tuple[ProceduralStep, ...]: ...

    def execute_step(self, step: PlanStep, context: ContextBundle) -> None: ...

    def evaluate_completion(self, plan: Plan, context: ContextBundle) -> bool: ...

    def update_memory(self, event: MemoryEvent) -> None: ...


# ---------------------------------------------------------------------------
# Context (04-module-contracts § context)
# ---------------------------------------------------------------------------


@runtime_checkable
class ContextPort(Protocol):
    """Context retrieval and refresh boundary."""

    def load_context(self, repository_context: RepositoryContext) -> ContextBundle: ...

    def refresh_context(
        self, repository_context: RepositoryContext
    ) -> ContextBundle: ...

    def retrieve_relevant_context(
        self, specification: Specification, step: PlanStep
    ) -> ContextBundle: ...

    def update_markov_state(self, result: str, correction: str = "") -> None: ...


# ---------------------------------------------------------------------------
# Prompt assembler (04-module-contracts § prompt_assembler)
# ---------------------------------------------------------------------------


@runtime_checkable
class PromptAssemblerPort(Protocol):
    """Prompt construction boundary."""

    def collect_context(self, step: PlanStep) -> ContextBundle: ...

    def assemble_prompt(self, context: ContextBundle) -> str: ...


# ---------------------------------------------------------------------------
# Budget manager (04-module-contracts § budget_manager)
# ---------------------------------------------------------------------------


@runtime_checkable
class BudgetManagerPort(Protocol):
    """Context budget enforcement boundary."""

    def estimate_tokens(self, context: ContextBundle) -> int: ...

    def rank_context(self, context: ContextBundle) -> ContextBundle: ...

    def clip(self, context: ContextBundle, token_limit: int) -> ContextBundle: ...

    def deduplicate(self, context: ContextBundle) -> ContextBundle: ...

    def summarize(self, context: ContextBundle) -> str: ...

    def compact(self, context: ContextBundle) -> ContextBundle: ...


# ---------------------------------------------------------------------------
# Knowledge graph (04-module-contracts § knowledge_graph)
# ---------------------------------------------------------------------------


@runtime_checkable
class KnowledgeGraphPort(Protocol):
    """Repository knowledge graph boundary."""

    def build_graph(self, repository_context: RepositoryContext) -> None: ...

    def update_graph(self, update: GraphUpdate) -> None: ...

    def query_graph(self, query: GraphQuery) -> GraphResult: ...


# ---------------------------------------------------------------------------
# Memory (04-module-contracts § memory)
# ---------------------------------------------------------------------------


@runtime_checkable
class MemoryStorePort(Protocol):
    """Memory pyramid storage boundary."""

    def store_event(self, event: MemoryEvent) -> None: ...

    def store_fact(self, fact: str, source: str = "") -> None: ...

    def store_scenario(self, scenario: MemoryEvent) -> None: ...

    def update_profile(self, profile: EngineeringProfile) -> None: ...


# ---------------------------------------------------------------------------
# Artifacts (04-module-contracts § artifacts)
# ---------------------------------------------------------------------------


@runtime_checkable
class ArtifactStorePort(Protocol):
    """Artifact offloading boundary."""

    def store_artifact(self, path: Path, summary: str) -> ArtifactReference: ...

    def retrieve_artifact(self, reference: ArtifactReference) -> str: ...

    def summarize_artifact(self, reference: ArtifactReference) -> str: ...


# ---------------------------------------------------------------------------
# Approval (04-module-contracts § approval)
# ---------------------------------------------------------------------------


@runtime_checkable
class ApprovalGatewayPort(Protocol):
    """Single approval authority boundary."""

    def approve(self, request: ApprovalRequest) -> ApprovalDecision: ...

    def reject(self, request: ApprovalRequest) -> ApprovalDecision: ...


# ---------------------------------------------------------------------------
# Tools (04-module-contracts § tools)
# ---------------------------------------------------------------------------


@runtime_checkable
class ToolRuntimePort(Protocol):
    """Stateless execution primitives boundary."""

    def read(self, path: Path) -> ToolResult: ...

    def write(self, path: Path, content: str) -> ToolResult: ...

    def edit(self, path: Path, old: str, new: str) -> ToolResult: ...

    def bash(self, command: str, cwd: Path) -> ToolResult: ...


# ---------------------------------------------------------------------------
# Provider (04-module-contracts § providers)
# ---------------------------------------------------------------------------


@runtime_checkable
class ProviderPort(Protocol):
    """External model integration boundary."""

    def chat(self, messages: tuple[ProviderMessage, ...]) -> ChatResponse: ...


# ---------------------------------------------------------------------------
# Audit logging (04-module-contracts § logging)
# ---------------------------------------------------------------------------


@runtime_checkable
class AuditLoggerPort(Protocol):
    """Audit logging boundary."""

    def record_prompt(self, prompt: str) -> None: ...

    def record_tool_call(self, result: ToolResult) -> None: ...

    def record_approval(
        self, request: ApprovalRequest, decision: ApprovalDecision
    ) -> None: ...

    def record_completion(self, event: AuditEvent) -> None: ...


# ---------------------------------------------------------------------------
# Argumentation log (Argument of Specs RD § 5)
# ---------------------------------------------------------------------------


@runtime_checkable
class ArgumentationLogPort(Protocol):
    """Argumentation session recording boundary."""

    def record_entry(self, entry: ArgumentationEntry) -> None: ...

    def record_canvas_snapshot(self, snapshot: CanvasSnapshot) -> None: ...

    def get_entries(self) -> tuple[ArgumentationEntry, ...]: ...


# ---------------------------------------------------------------------------
# Heuristic updater (Argument of Specs RD § 4)
# ---------------------------------------------------------------------------


@runtime_checkable
class HeuristicUpdaterPort(Protocol):
    """Spec-wizard heuristic learning boundary.

    Runs as a batch phase on spec completion or session abandonment.
    """

    def run_batch_update(self, abandoned: bool = False) -> None: ...

    def get_probability(self, key: str) -> float: ...

    def load_config(self) -> HeuristicConfig: ...


# ---------------------------------------------------------------------------
# Schema tailor (Argument of Specs RD § 2, Layer 1)
# ---------------------------------------------------------------------------


@runtime_checkable
class SchemaTailorPort(Protocol):
    """Tech-stack schema loading boundary."""

    def detect_framework(self) -> str | None: ...

    def fetch_schema(self, framework_id: str | None) -> dict[str, object]: ...
