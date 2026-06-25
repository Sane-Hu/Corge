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
from typing import Any

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
    completed: bool = False


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
    markov_context: MarkovStepContext | None = None
    current_step_id: str | None = None
    engineering_facts: tuple[str, ...] = ()


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


@dataclass(frozen=True, slots=True)
class GraphNode:
    """Single node returned by a knowledge graph query (FRD FR-005).

    ``kind`` is one of the spec-defined node types: file, directory, class,
    function, service, controller, model, test, config.
    ``node_id`` is a stable string key (e.g. a relative path or
    ``<path>::<name>`` for classes and functions).
    ``path`` holds the containing file path for non-directory nodes; empty
    string for directory nodes that have no single owning file.
    ``name`` holds the symbol name for class/function nodes; empty string for
    file/directory nodes.
    """

    kind: str
    node_id: str
    path: str = ""
    name: str = ""


@dataclass(frozen=True, slots=True)
class GraphResult:
    """Structured result returned by ``query_graph()`` (FRD FR-005).

    Wraps a tuple of ``GraphNode`` objects so callers receive a typed,
    frozen boundary object instead of a raw collection.
    """

    nodes: tuple[GraphNode, ...]


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
    payload: dict[str, Any] = field(default_factory=dict)


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


# ---------------------------------------------------------------------------
# Argument of Specs — Sticky Notes & Canvas (Argument of Specs RD § 2, § 4)
# ---------------------------------------------------------------------------


class StickyNoteStatus(StrEnum):
    """Validity state of a sticky note's graph pointer."""

    ACTIVE = "active"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class StickyNote:
    """Dev note anchored to a Knowledge Graph node.

    Maintains a live pointer (``node_id``) to a graph node.
    If the node is deleted or heavily modified, the UI sets
    ``status`` to ``INVALID`` and renders a red warning icon.
    """

    node_id: str
    content: str
    status: StickyNoteStatus = StickyNoteStatus.ACTIVE
    note_type: str = "active"


@dataclass(frozen=True, slots=True)
class SemanticGap:
    """An explicitly tracked required-but-missing property in a spec.

    Transition to SPEC_METASTABLE is blocked while any gap has
    ``resolved == False``.
    """

    topic: str
    resolved: bool = False


@dataclass(frozen=True, slots=True)
class CanvasSnapshot:
    """Immutable snapshot of the freestyle canvas at concretization time.

    ``timestamp`` marks when the canvas was frozen.
    ``concretized_ranges`` lists (start_line, end_line) tuples indicating
    which lines the agent concretized; everything else was user-added.
    """

    text: str
    timestamp: str
    concretized_ranges: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True, slots=True)
class ArgumentationEntry:
    """Single exchange in the Socratic Q&A log."""

    question: str
    answer: str
    timestamp: str = ""
    was_user_override: bool = False


# ---------------------------------------------------------------------------
# Argument of Specs — Planning (Argument of Specs RD § 2, Layer 2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TechnicalPlan:
    """Architectural map produced in the TECH_PLAN_REITERATION sub-state.

    Separate from the existing ``Plan`` model which holds procedural
    execution steps.  This holds high-level module boundary changes
    and interface definitions.
    """

    content: str
    specification_ref: str = ""


@dataclass(frozen=True, slots=True)
class ProceduralStep:
    """Single step produced in the STEPS_REITERATION sub-state.

    More granular than ``PlanStep``; these are the algorithmic steps
    derived from an approved ``TechnicalPlan``.
    """

    identifier: str
    description: str
    completed: bool = False


# ---------------------------------------------------------------------------
# Argument of Specs — Coding context (Argument of Specs RD § 2, Layer 3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MarkovStepContext:
    """N-1 context payload for the Coding phase Markov chain.

    Includes both the agent's original proposal and the user's manual
    correction so the LLM can learn from inaccuracies.
    ``compressed_trajectory`` summarises N-2 … N-Start.
    """

    agent_proposal: str
    user_correction: str
    compressed_trajectory: str = ""


# ---------------------------------------------------------------------------
# Argument of Specs — Heuristic Updater (Argument of Specs RD § 5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HeuristicConfig:
    """Configurable thresholds for the spec-wizard heuristic updater.

    Loaded from ``corge_heuristics.yaml``.
    """

    delta_clip_max: float = 0.05
    abandonment_penalty: float = -0.15
    decay_rate: float = 0.99
    max_socratic_questions: int = 3
