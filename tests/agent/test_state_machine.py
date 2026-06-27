"""Tests for nested state machine enums and semantic gap blocking.

Spec traceability:
    Argument of Specs RD § 3 — Master & Nested State Machines
    Resolved Design § 1      — strict blocking on unresolved gaps
"""

from unittest.mock import MagicMock

import pytest

from corge.agent.session import SessionState, load_session, save_session
from corge.agent.session_controller import InvalidTransitionError, SessionController
from corge.contracts import (
    LifecycleState,
    MasterPhase,
    Plan,
    PlanStep,
    ProceduralStep,
    SemanticGap,
    SpecState,
    TechnicalPlan,
    ToolAction,
)

# -- Semantic gap transition tests --------------------------------------------


def test_no_gaps_allows_transition() -> None:
    controller = SessionController(
        provider=MagicMock(),
        tool_runtime=MagicMock(),
        approval_gateway=MagicMock(),
        context_service=MagicMock(),
        memory_store=MagicMock(),
        heuristic_updater=MagicMock(),
        knowledge_graph=MagicMock(),
        schema_tailor=MagicMock(),
        budget_manager=MagicMock(),
        audit_logger=MagicMock(),
        artifact_store=MagicMock(),
    )
    # No pending gaps, should allow transition to SPEC_APPROVAL
    controller.transition_to(LifecycleState.SPEC_APPROVAL)
    assert controller.state == LifecycleState.SPEC_APPROVAL


def test_unresolved_gap_blocks_transition() -> None:
    controller = SessionController(
        provider=MagicMock(),
        tool_runtime=MagicMock(),
        approval_gateway=MagicMock(),
        context_service=MagicMock(),
        memory_store=MagicMock(),
        heuristic_updater=MagicMock(),
        knowledge_graph=MagicMock(),
        schema_tailor=MagicMock(),
        budget_manager=MagicMock(),
        audit_logger=MagicMock(),
        artifact_store=MagicMock(),
    )
    # Set an unresolved gap
    controller._pending_gaps = (SemanticGap(topic="routing", resolved=False),)

    with pytest.raises(InvalidTransitionError) as exc_info:
        controller.transition_to(LifecycleState.SPEC_APPROVAL)
    assert "1 unresolved gaps exist" in str(exc_info.value)


# -- Session serialization round-trip tests -----------------------------------


def test_session_round_trip_with_full_plan(tmp_path) -> None:
    state = SessionState(
        lifecycle_state=LifecycleState.EXECUTION,
        master_phase=MasterPhase.CODING,
        plan=Plan(
            steps=(
                PlanStep(
                    identifier="s1",
                    description="do it",
                    action=ToolAction.WRITE,
                    target="f.txt",
                    completed=True,
                ),
            ),
            specification_ref="ref",
        ),
        technical_plan=TechnicalPlan(content="hello", specification_ref="ref"),
        procedural_steps=(ProceduralStep(identifier="p1", description="read"),),
    )
    save_session(tmp_path, state)
    loaded = load_session(tmp_path)

    assert loaded is not None
    assert loaded.lifecycle_state == LifecycleState.EXECUTION
    assert loaded.plan is not None
    assert loaded.plan.steps[0].identifier == "s1"
    assert loaded.plan.steps[0].completed is True
    assert loaded.technical_plan.content == "hello"
    assert len(loaded.procedural_steps) == 1
    assert loaded.procedural_steps[0].identifier == "p1"


def test_sync_nested_states_enters_argumentation_diff_when_gaps_present() -> None:
    from unittest.mock import MagicMock

    from corge.agent.session_controller import SessionController

    controller = SessionController(
        provider=MagicMock(),
        tool_runtime=MagicMock(),
        approval_gateway=MagicMock(),
        context_service=MagicMock(),
        memory_store=MagicMock(),
        heuristic_updater=MagicMock(),
        knowledge_graph=MagicMock(),
        schema_tailor=MagicMock(),
        budget_manager=MagicMock(),
        audit_logger=MagicMock(),
        artifact_store=MagicMock(),
    )
    # Mock the spec_agent to return gaps
    controller._spec_agent.analyze_specification_gaps = MagicMock(
        return_value=(SemanticGap("test"),)
    )
    controller.analyze_specification_gaps("canvas text")

    # Transition to SPEC_VALIDATION
    # Start -> REPOSITORY_SELECTION -> REPOSITORY_ANALYSIS -> SPEC_ENTRY -> SPEC_VALIDATION
    for _ in range(4):
        controller.advance()

    assert controller._state == LifecycleState.SPEC_VALIDATION
    assert controller._spec_state == SpecState.ARGUMENTATION_DIFF


def test_merge_templated_responses_resolves_gaps() -> None:
    from corge.contracts import Specification, AcceptanceCriteria, SemanticGap
    controller = SessionController(
        provider=MagicMock(),
        tool_runtime=MagicMock(),
        approval_gateway=MagicMock(),
        context_service=MagicMock(),
        memory_store=MagicMock(),
        heuristic_updater=MagicMock(),
        knowledge_graph=MagicMock(),
        schema_tailor=MagicMock(),
        budget_manager=MagicMock(),
        audit_logger=MagicMock(),
        artifact_store=MagicMock(),
    )
    
    # Mock SpecificationAgent merge to return a dummy specification
    spec = Specification(title="Test", body="Body text", acceptance_criteria=AcceptanceCriteria(items=()))
    controller._spec_agent.merge_templated_responses = MagicMock(return_value=spec)

    # Set up pending gaps
    controller._pending_gaps = (
        SemanticGap(topic="routing", resolved=False),
        SemanticGap(topic="database", resolved=False),
    )

    # Case 1: All gaps unresolved (default placeholder template is kept)
    edited_text = (
        "# Requirements\n"
        "[GAP: routing]\n"
        "Resolution: <Enter details here>\n\n"
        "[GAP: database]\n"
        "Resolution: <Enter details here>\n"
    )
    controller.merge_templated_responses(spec, edited_text)
    assert not controller._pending_gaps[0].resolved
    assert not controller._pending_gaps[1].resolved

    # Case 2: One gap resolved by entering text, one gap removed entirely
    edited_text = (
        "# Requirements\n"
        "[GAP: routing]\n"
        "Resolution: Use fastapi router.\n"
    )
    controller.merge_templated_responses(spec, edited_text)
    # routing gap was resolved (the default Resolution template was modified)
    assert controller._pending_gaps[0].resolved
    # database gap was resolved because its placeholder is completely absent
    assert controller._pending_gaps[1].resolved
