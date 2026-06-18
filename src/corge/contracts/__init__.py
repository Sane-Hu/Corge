"""Shared public contracts for Corge module boundaries.

This package is the single import surface for all boundary types:

* **Models** — frozen dataclasses that cross module boundaries.
* **Protocols** — ``typing.Protocol`` interfaces every module satisfies.
* **Lifecycle** — workflow state enumeration.

Modules import from ``corge.contracts`` and never from each other.
"""

from corge.contracts.lifecycle import LifecycleState
from corge.contracts.models import (
    AcceptanceCriteria,
    ApprovalDecision,
    ApprovalRequest,
    ArtifactReference,
    AuditEvent,
    ChatResponse,
    ContextBundle,
    EngineeringProfile,
    GraphNode,
    GraphQuery,
    GraphResult,
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
from corge.contracts.ports import (
    AgentPort,
    ApprovalGatewayPort,
    ArtifactStorePort,
    AuditLoggerPort,
    BudgetManagerPort,
    ContextPort,
    KnowledgeGraphPort,
    MemoryStorePort,
    PromptAssemblerPort,
    ProviderPort,
    ToolRuntimePort,
    UiPort,
)

__all__ = [
    # Models
    "AcceptanceCriteria",
    "ApprovalDecision",
    "ApprovalRequest",
    "ArtifactReference",
    "AuditEvent",
    "ChatResponse",
    "ContextBundle",
    "EngineeringProfile",
    "GraphNode",
    "GraphQuery",
    "GraphResult",
    "GraphUpdate",
    "MemoryEvent",
    "Plan",
    "PlanStep",
    "ProviderMessage",
    "RepositoryContext",
    "Specification",
    "ToolAction",
    "ToolResult",
    # Lifecycle
    "LifecycleState",
    # Protocols
    "AgentPort",
    "ApprovalGatewayPort",
    "ArtifactStorePort",
    "AuditLoggerPort",
    "BudgetManagerPort",
    "ContextPort",
    "KnowledgeGraphPort",
    "MemoryStorePort",
    "PromptAssemblerPort",
    "ProviderPort",
    "ToolRuntimePort",
    "UiPort",
]
