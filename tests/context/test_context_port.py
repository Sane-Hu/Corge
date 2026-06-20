"""Tests for MarkovStepContext N-1 logic (Argument of Specs RD § 2, Layer 3)."""

from corge.contracts import MarkovStepContext


def test_markov_context_holds_proposal_and_correction() -> None:
    """N-1 context contains both the agent proposal and user correction."""
    ctx = MarkovStepContext(
        agent_proposal="def foo(): return 1",
        user_correction="def foo(): return 2",
        compressed_trajectory="Step 1: scaffolded module",
    )
    assert ctx.agent_proposal != ctx.user_correction
    assert ctx.compressed_trajectory != ""


def test_markov_context_defaults() -> None:
    """Compressed trajectory defaults to empty string."""
    ctx = MarkovStepContext(
        agent_proposal="x",
        user_correction="x",
    )
    assert ctx.compressed_trajectory == ""


def test_markov_context_is_frozen() -> None:
    """MarkovStepContext is immutable."""
    ctx = MarkovStepContext(agent_proposal="a", user_correction="b")
    import pytest
    with pytest.raises(AttributeError):
        ctx.agent_proposal = "changed"  # type: ignore[misc]
