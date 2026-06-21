"""Tests for nested state machine enums and semantic gap blocking.

Spec traceability:
    Argument of Specs RD § 3 — Master & Nested State Machines
    Resolved Design § 1      — strict blocking on unresolved gaps
"""

import pytest

from corge.contracts import (
    MasterPhase,
    PlanState,
    SemanticGap,
    SpecState,
)


class InvalidTransitionError(Exception):
    """Raised when a state transition is blocked."""
    pass


class SemanticGapTracker:
    """Tracks explicit semantic gaps blocking the transition to SPEC_METASTABLE.

    Transition is blocked while any gap has ``resolved == False``.
    """

    def __init__(self) -> None:
        self._gaps: list[SemanticGap] = []

    def add_gap(self, gap: SemanticGap) -> None:
        self._gaps.append(gap)

    def resolve(self, topic: str) -> None:
        self._gaps = [
            SemanticGap(topic=g.topic, resolved=True) if g.topic == topic else g
            for g in self._gaps
        ]

    def has_unresolved_gaps(self) -> bool:
        return any(not g.resolved for g in self._gaps)

    def unresolved(self) -> tuple[SemanticGap, ...]:
        return tuple(g for g in self._gaps if not g.resolved)


# -- Enum existence tests -----------------------------------------------------


def test_master_phase_values() -> None:
    assert set(MasterPhase) == {
        MasterPhase.SPECIFICATION,
        MasterPhase.PLANNING,
        MasterPhase.CODING,
    }


def test_spec_state_values() -> None:
    assert set(SpecState) == {
        SpecState.CANVAS_FREESTYLE,
        SpecState.CONCRETIZATION,
        SpecState.ARGUMENTATION_DIFF,
        SpecState.SPEC_METASTABLE,
    }


def test_plan_state_values() -> None:
    assert set(PlanState) == {
        PlanState.TECH_PLAN_REITERATION,
        PlanState.STEPS_REITERATION,
    }


# -- Semantic gap tracker tests ------------------------------------------------


def test_no_gaps_allows_transition() -> None:
    tracker = SemanticGapTracker()
    assert not tracker.has_unresolved_gaps()


def test_unresolved_gap_blocks_transition() -> None:
    tracker = SemanticGapTracker()
    tracker.add_gap(SemanticGap(topic="authentication"))
    assert tracker.has_unresolved_gaps()


def test_resolving_all_gaps_unblocks() -> None:
    tracker = SemanticGapTracker()
    tracker.add_gap(SemanticGap(topic="authentication"))
    tracker.add_gap(SemanticGap(topic="database"))
    tracker.resolve("authentication")
    assert tracker.has_unresolved_gaps()  # database still open
    tracker.resolve("database")
    assert not tracker.has_unresolved_gaps()


def test_invalid_transition_error_on_unresolved_gaps() -> None:
    """Simulates the state machine blocking transition to PLANNING."""
    tracker = SemanticGapTracker()
    tracker.add_gap(SemanticGap(topic="routing", resolved=False))

    current_state = SpecState.ARGUMENTATION_DIFF
    target_state = SpecState.SPEC_METASTABLE

    if tracker.has_unresolved_gaps():
        with pytest.raises(InvalidTransitionError):
            raise InvalidTransitionError(
                f"Cannot transition {current_state} -> {target_state}: "
                f"{len(tracker.unresolved())} unresolved gaps"
            )
