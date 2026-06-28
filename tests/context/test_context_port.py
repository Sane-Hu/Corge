"""Tests for MarkovStepContext N-1 logic (Argument of Specs RD § 2, Layer 3)."""

from corge.contracts import MarkovStepContext


def test_markov_context_holds_proposal_and_correction() -> None:
    """N-1 context contains both the tool result and user correction."""
    ctx = MarkovStepContext(
        tool_result="def foo(): return 1",
        user_correction="def foo(): return 2",
        compressed_trajectory="Step 1: scaffolded module",
    )
    assert ctx.tool_result != ctx.user_correction
    assert ctx.compressed_trajectory != ""


def test_markov_context_defaults() -> None:
    """Compressed trajectory defaults to empty string."""
    ctx = MarkovStepContext(
        tool_result="x",
        user_correction="x",
    )
    assert ctx.compressed_trajectory == ""


def test_markov_context_is_frozen() -> None:
    """MarkovStepContext is immutable."""
    ctx = MarkovStepContext(tool_result="a", user_correction="b")
    import pytest

    with pytest.raises(AttributeError):
        ctx.tool_result = "changed"  # type: ignore[misc]
