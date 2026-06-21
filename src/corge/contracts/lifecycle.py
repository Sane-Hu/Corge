"""Workflow lifecycle states from the repository state machine.

Spec traceability:
    02-technical-spec § 3  — primary lifecycle states
    Argument of Specs RD   — nested state machines for Spec/Plan phases
"""

from enum import StrEnum


class LifecycleState(StrEnum):
    """Primary lifecycle states documented in docs/02-technical-spec.md."""

    START = "START"
    REPOSITORY_SELECTION = "REPOSITORY_SELECTION"
    REPOSITORY_ANALYSIS = "REPOSITORY_ANALYSIS"
    SPEC_ENTRY = "SPEC_ENTRY"
    SPEC_VALIDATION = "SPEC_VALIDATION"
    SPEC_APPROVAL = "SPEC_APPROVAL"
    PLAN_GENERATION = "PLAN_GENERATION"
    PLAN_REVIEW = "PLAN_REVIEW"
    PLAN_APPROVAL = "PLAN_APPROVAL"
    EXECUTION = "EXECUTION"
    VERIFICATION = "VERIFICATION"
    COMPLETION_REVIEW = "COMPLETION_REVIEW"
    DONE = "DONE"


class MasterPhase(StrEnum):
    """3-Layer Execution Flow phases (Argument of Specs RD § 2)."""

    SPECIFICATION = "SPECIFICATION"
    PLANNING = "PLANNING"
    CODING = "CODING"


class SpecState(StrEnum):
    """Nested states within SPECIFICATION_PHASE (Argument of Specs RD § 3)."""

    CANVAS_FREESTYLE = "CANVAS_FREESTYLE"
    CONCRETIZATION = "CONCRETIZATION"
    ARGUMENTATION_DIFF = "ARGUMENTATION_DIFF"
    SPEC_METASTABLE = "SPEC_METASTABLE"


class PlanState(StrEnum):
    """Nested states within PLANNING_PHASE (Argument of Specs RD § 3)."""

    TECH_PLAN_REITERATION = "TECH_PLAN_REITERATION"
    STEPS_REITERATION = "STEPS_REITERATION"

