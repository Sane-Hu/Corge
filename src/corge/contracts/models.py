"""Shared boundary objects for Corge module communication.

Every model in this module is a frozen, slotted dataclass that crosses
module boundaries.  Modules pass these objects to port interfaces;
they never exchange raw dicts or untyped data.

Spec traceability:
    PRD          — spec-driven delivery
    FRD FR-002   — specification wizard fields
    FRD FR-003   — repository ingestion outputs
    FRD FR-007   — memory pyramid layers
    FRD FR-009   — approval required / not required
    FRD FR-011   — context budget management
    FRD FR-013   — audit logging
    09-context   — tier 1–5 context, confidence scoring, artifact refs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ApprovalDecision(StrEnum):
    """Human approval outcome (FRD FR-009)."""

    APPROVED = "approved"
    REJECTED = "rejected"


class ToolAction(StrEnum):
    """Stateless tool primitives (04-module-contracts § tools)."""

    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    BASH = "bash"


# ---------------------------------------------------------------------------
# Specification gate (FRD FR-001, FR-002)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AcceptanceCriteria:
    """Verifiable acceptance criteria captured by the specification gate."""

    items: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Specification:
    """Approved implementation specification.

    The wizard (FRD FR-002) elicits goal, story, requirements,
    constraints, acceptance criteria, and testing expectations.
    ``title`` carries the business goal; ``body`` carries the
    concatenated narrative; structured wizard fields are kept
    separately so downstream consumers (planning engine, prompt
    assembler) can access them without parsing.
    """

    title: str
    body: str
    acceptance_criteria: AcceptanceCriteria
    constraints: str = ""
    testing_expectations: str = ""


# ---------------------------------------------------------------------------
# Planning (07-agent-loop-specification)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PlanStep:
    """Single step inside an approved execution plan.

    ``action`` and ``target`` link the step to the tool runtime
    contract so the agent loop can route without re-parsing the
    description.
    """

    identifier: str
    description: str
    action: ToolAction | None = None
    target: str = ""


@dataclass(frozen=True, slots=True)
class Plan:
    """Approved execution plan derived from a specification.

    ``specification_ref`` traces the plan back to the specification
    title for audit and verification purposes.
    """

    steps: tuple[PlanStep, ...]
    specification_ref: str = ""


# ---------------------------------------------------------------------------
# Repository understanding (FRD FR-003, FR-004, FR-005)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RepositoryContext:
    """Repository snapshot produced by the ingestion phase.

    ``tree`` holds relative paths discovered during scanning.
    ``config_files`` isolates build / config files for the
    engineering profile extractor (FRD FR-006).
    """

    root: Path
    tree: tuple[str, ...] = ()
    config_files: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EngineeringProfile:
    """Repository-specific coding conventions (FRD FR-006).

    ``confidence`` maps each rule string to a float in [0, 1].
    Low-confidence rules are ignored by the prompt assembler
    (09-context-engineering-spec § Confidence Scoring).
    """

    rules: tuple[str, ...] = ()
    confidence: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Context bundle (09-context-engineering-spec, tiers 1–5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    """Reference to offloaded artifact content (FRD FR-010).

    Prompts receive the ``summary`` and ``uri``; never the raw
    content of large outputs.
    """

    uri: str
    summary: str


@dataclass(frozen=True, slots=True)
class MemoryEvent:
    """Memory pyramid event (FRD FR-007, L0–L2).

    ``timestamp`` is ISO-8601 for ordering and audit; empty string
    when not yet stamped (the memory store assigns it on ingest).
    """

    kind: str
    payload: dict[str, object] = field(default_factory=dict)
    timestamp: str = ""


@dataclass(frozen=True, slots=True)
class ContextBundle:
    """Selected context passed to prompt assembly.

    Tier 1 (always present): specification, plan, engineering_profile.
    Tier 2 (repo understanding): repository_context, relevant_files.
    Tier 3 (task memory): scenario_memory.
    Tier 4 (recent activity): recent_actions.
    Tier 5 (artifacts): artifact_refs (referenced only).
    """

    specification: Specification
    plan: Plan
    repository_context: RepositoryContext
    engineering_profile: EngineeringProfile
    scenario_memory: tuple[MemoryEvent, ...] = ()
    relevant_files: tuple[str, ...] = ()
    recent_actions: tuple[str, ...] = ()
    artifact_refs: tuple[ArtifactReference, ...] = ()


# ---------------------------------------------------------------------------
# Knowledge graph (FRD FR-005)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GraphQuery:
    """Knowledge graph query."""

    expression: str


@dataclass(frozen=True, slots=True)
class GraphUpdate:
    """Incremental knowledge graph update (FRD FR-004)."""

    paths: tuple[Path, ...]


# ---------------------------------------------------------------------------
# Approval gateway (FRD FR-009)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    """Approval request submitted by the agent loop.

    ``step_ref`` traces the request back to the originating
    plan step identifier for audit logging.
    """

    action: ToolAction
    target: str
    reason: str
    step_ref: str = ""


# ---------------------------------------------------------------------------
# Tool runtime (04-module-contracts § tools)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Result returned by a stateless tool execution.

    ``success`` is False when the tool encountered an error.
    ``stderr`` captures error output separately from ``output``
    so the budget manager can prioritise error context.
    """

    action: ToolAction
    output: str
    success: bool = True
    stderr: str = ""


# ---------------------------------------------------------------------------
# Provider abstraction (FRD FR-014)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderMessage:
    """Single message in a provider chat exchange."""

    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ChatResponse:
    """Provider chat response.

    ``usage`` carries token counts (e.g. ``{"prompt": 120, "completion": 45}``)
    so the budget manager can track consumption.
    """

    content: str
    usage: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Audit logging (FRD FR-013)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Audit log event.

    ``timestamp`` is ISO-8601; assigned by the audit logger on record.
    """

    kind: str
    payload: dict[str, object] = field(default_factory=dict)
    timestamp: str = ""
