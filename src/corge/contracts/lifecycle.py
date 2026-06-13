"""Workflow lifecycle states from the repository state machine."""

from enum import StrEnum


class LifecycleState(StrEnum):
    """Primary lifecycle states documented in docs/05-state-machine.md."""

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

