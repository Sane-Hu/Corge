"""Typed placeholders shared by skeleton module interfaces."""

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class ApprovalDecision(StrEnum):
    """Human approval outcome."""

    APPROVED = "approved"
    REJECTED = "rejected"


class ToolAction(StrEnum):
    """Tool actions exposed by the stateless tool runtime."""

    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    BASH = "bash"


@dataclass(frozen=True, slots=True)
class AcceptanceCriteria:
    """Acceptance criteria captured by the specification gate."""

    items: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Specification:
    """Approved implementation specification placeholder."""

    title: str
    body: str
    acceptance_criteria: AcceptanceCriteria


@dataclass(frozen=True, slots=True)
class PlanStep:
    """Single approved plan step placeholder."""

    identifier: str
    description: str


@dataclass(frozen=True, slots=True)
class Plan:
    """Approved execution plan placeholder."""

    steps: tuple[PlanStep, ...]


@dataclass(frozen=True, slots=True)
class RepositoryContext:
    """Repository context boundary object."""

    root: Path


@dataclass(frozen=True, slots=True)
class EngineeringProfile:
    """Engineering profile boundary object."""

    rules: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ContextBundle:
    """Selected context passed to prompt assembly."""

    specification: Specification
    plan: Plan
    repository_context: RepositoryContext
    engineering_profile: EngineeringProfile


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    """Reference to offloaded artifact content."""

    uri: str
    summary: str


@dataclass(frozen=True, slots=True)
class GraphQuery:
    """Knowledge graph query placeholder."""

    expression: str


@dataclass(frozen=True, slots=True)
class GraphUpdate:
    """Knowledge graph update placeholder."""

    paths: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class MemoryEvent:
    """Memory pyramid event placeholder."""

    kind: str
    payload: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    """Approval request boundary object."""

    action: ToolAction
    target: str
    reason: str


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Tool runtime result placeholder."""

    action: ToolAction
    output: str


@dataclass(frozen=True, slots=True)
class ProviderMessage:
    """Provider chat message placeholder."""

    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ChatResponse:
    """Provider chat response placeholder."""

    content: str


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Audit log event placeholder."""

    kind: str
    payload: dict[str, object] = field(default_factory=dict)

