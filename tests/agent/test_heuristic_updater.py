"""Tests for BayesianUpdater — the canonical HeuristicUpdaterPort implementation.

Spec traceability:
    Tech-spec §4 §Bayesian Heuristic Learning — EWMA formula, delta clipping,
        abandonment penalty, decay rate
    Argument of Specs RD § 5 — batch phase, offline update
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from corge.agent.bayesian_updater import BayesianUpdater
from corge.contracts import ArgumentationEntry, HeuristicConfig


@pytest.fixture()
def agent_dir(tmp_path: Path) -> Path:
    d = tmp_path / ".agent"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_log(*entries: ArgumentationEntry):
    """Return a mock ArgumentationLogPort with the given entries."""
    log = MagicMock()
    log.get_entries.return_value = entries
    return log


@pytest.fixture()
def updater(agent_dir: Path) -> BayesianUpdater:
    log = _make_log()  # empty log by default
    return BayesianUpdater(agent_dir, log)


def test_initial_probability_is_default(updater: BayesianUpdater) -> None:
    """Unknown keys return the default 0.5 prior."""
    assert updater.get_probability("nonexistent") == pytest.approx(0.5)


def test_load_config_returns_spec_defaults(updater: BayesianUpdater) -> None:
    """HeuristicConfig defaults must match Tech-spec §4."""
    config = updater.load_config()
    assert isinstance(config, HeuristicConfig)
    assert config.delta_clip_max == pytest.approx(0.05)
    assert config.abandonment_penalty == pytest.approx(-0.15)
    assert config.decay_rate == pytest.approx(0.99)


def test_ewma_increases_probability_on_zero_overrides(agent_dir: Path) -> None:
    """When no interactions are overridden, schema_assumption_validity rises."""
    entries = (
        ArgumentationEntry(question="q1", answer="a1", was_user_override=False),
        ArgumentationEntry(question="q2", answer="a2", was_user_override=False),
    )
    log = _make_log(*entries)
    updater = BayesianUpdater(agent_dir, log)

    # prior = 0.5 (default)
    updater.run_batch_update(abandoned=False)
    prob = updater.get_probability("schema_assumption_validity")
    # observation = 1.0 (no overrides) → P_new should be > 0.5
    assert prob > 0.5


def test_ewma_decreases_probability_on_all_overrides(agent_dir: Path) -> None:
    """When all interactions are overridden, validity probability falls."""
    entries = (
        ArgumentationEntry(question="q1", answer="a1", was_user_override=True),
        ArgumentationEntry(question="q2", answer="a2", was_user_override=True),
    )
    log = _make_log(*entries)
    updater = BayesianUpdater(agent_dir, log)
    updater.run_batch_update(abandoned=False)
    prob = updater.get_probability("schema_assumption_validity")
    # observation = 0.0 (all overridden) → P_new should be < 0.5
    assert prob < 0.5


def test_delta_clipping_prevents_large_swings(agent_dir: Path) -> None:
    """The probability delta must never exceed delta_clip_max (0.05)."""
    entries = tuple(
        ArgumentationEntry(question=f"q{i}", answer="a", was_user_override=True)
        for i in range(20)
    )
    log = _make_log(*entries)
    updater = BayesianUpdater(agent_dir, log)
    updater.run_batch_update(abandoned=False)
    prob = updater.get_probability("schema_assumption_validity")
    diff = abs(prob - 0.5)
    assert diff <= 0.05 + 1e-9  # clipped to delta_clip_max


def test_abandonment_penalty_decreases_base_engagement(agent_dir: Path) -> None:
    """Abandoned sessions penalize base_engagement probability."""
    log = _make_log()  # no entries → triggers abandonment path
    updater = BayesianUpdater(agent_dir, log)
    before = updater.get_probability("base_engagement")

    updater.run_batch_update(abandoned=True)
    after = updater.get_probability("base_engagement")

    assert after < before


def test_persistence_survives_reinitialisation(agent_dir: Path) -> None:
    """Heuristics written to disk are loaded correctly on next instantiation."""
    entries = (
        ArgumentationEntry(question="db", answer="pg", was_user_override=False),
    )
    log1 = _make_log(*entries)
    u1 = BayesianUpdater(agent_dir, log1)
    u1.run_batch_update(abandoned=False)
    prob1 = u1.get_probability("schema_assumption_validity")

    log2 = _make_log()
    u2 = BayesianUpdater(agent_dir, log2)
    prob2 = u2.get_probability("schema_assumption_validity")

    assert prob1 == pytest.approx(prob2)
