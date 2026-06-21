"""Shared public contracts for Corge module boundaries.

This package is the single import surface for all boundary types:

* **Models** — frozen dataclasses that cross module boundaries.
* **Protocols** — ``typing.Protocol`` interfaces every module satisfies.
* **Lifecycle** — workflow state enumeration.

Modules import from ``corge.contracts`` and never from each other.
"""

from corge.contracts.lifecycle import (
    LifecycleState,
    MasterPhase,
    PlanState,
    SpecState,
)
from corge.contracts.models import (
    AcceptanceCriteria,
    ApprovalDecision,
    ApprovalRequest,
    ArgumentationEntry,
    ArtifactReference,
    AuditEvent,
    CanvasSnapshot,
    ChatResponse,
    ContextBundle,
    EngineeringProfile,
    GraphNode,
    GraphQuery,
    GraphResult,
    GraphUpdate,
    HeuristicConfig,
    MarkovStepContext,
    MemoryEvent,
    Plan,
    PlanStep,
    ProceduralStep,
    ProviderMessage,
    RepositoryContext,
    SemanticGap,
    Specification,
    StickyNote,
    StickyNoteStatus,
    TechnicalPlan,
    ToolAction,
    ToolResult,
)
from corge.contracts.ports import (
    AgentPort,
    ApprovalGatewayPort,
    ArgumentationLogPort,
    ArtifactStorePort,
    AuditLoggerPort,
    BudgetManagerPort,
    ContextPort,
    HeuristicUpdaterPort,
    KnowledgeGraphPort,
    MemoryStorePort,
    PromptAssemblerPort,
    ProviderPort,
    SchemaTailorPort,
    ToolRuntimePort,
    UiPort,
)

__all__ = [
    # Models
    "AcceptanceCriteria",
    "ApprovalDecision",
    "ApprovalRequest",
    "ArgumentationEntry",
    "ArtifactReference",
    "AuditEvent",
    "CanvasSnapshot",
    "ChatResponse",
    "ContextBundle",
    "EngineeringProfile",
    "GraphNode",
    "GraphQuery",
    "GraphResult",
    "GraphUpdate",
    "HeuristicConfig",
    "MarkovStepContext",
    "MemoryEvent",
    "Plan",
    "PlanStep",
    "ProceduralStep",
    "ProviderMessage",
    "RepositoryContext",
    "SemanticGap",
    "Specification",
    "StickyNote",
    "StickyNoteStatus",
    "TechnicalPlan",
    "ToolAction",
    "ToolResult",
    # Lifecycle
    "LifecycleState",
    "MasterPhase",
    "PlanState",
    "SpecState",
    # Protocols
    "AgentPort",
    "ApprovalGatewayPort",
    "ArgumentationLogPort",
    "ArtifactStorePort",
    "AuditLoggerPort",
    "BudgetManagerPort",
    "ContextPort",
    "HeuristicUpdaterPort",
    "KnowledgeGraphPort",
    "MemoryStorePort",
    "PromptAssemblerPort",
    "ProviderPort",
    "SchemaTailorPort",
    "ToolRuntimePort",
    "UiPort",
]
