"""Tests for the heuristic updater (Argument of Specs RD § 5)."""

from pathlib import Path

import pytest

from corge.agent.heuristic_updater import HeuristicUpdater
from corge.contracts import ArgumentationEntry, HeuristicConfig


@pytest.fixture()
def agent_dir(tmp_path: Path) -> Path:
    return tmp_path / ".agent"


@pytest.fixture()
def updater(agent_dir: Path) -> HeuristicUpdater:
    agent_dir.mkdir(parents=True, exist_ok=True)
    return HeuristicUpdater(agent_dir)


def test_initial_probability_is_default(updater: HeuristicUpdater) -> None:
    """Unknown keys return the default 0.5 prior."""
    assert updater.get_probability("nonexistent") == 0.5


def test_apply_entry_decreases_on_override(updater: HeuristicUpdater) -> None:
    """User overriding the agent's answer decreases P(Schema Default)."""
    entry = ArgumentationEntry(
        question="auth_method",
        answer="JWT",
        was_user_override=True,
    )
    updater.apply_entry(entry)
    prob = updater.get_probability("schema_default:auth_method")
    assert prob < 0.5


def test_apply_entry_increases_on_agreement(updater: HeuristicUpdater) -> None:
    """User agreeing with the agent slightly increases P(Schema Default)."""
    entry = ArgumentationEntry(
        question="auth_method",
        answer="session",
        was_user_override=False,
    )
    updater.apply_entry(entry)
    prob = updater.get_probability("schema_default:auth_method")
    assert prob > 0.5


def test_abandonment_penalty_decreases_all(
    updater: HeuristicUpdater,
) -> None:
    """Abandonment penalty decreases all tracked probabilities."""
    entry = ArgumentationEntry(
        question="db_choice", answer="postgres", was_user_override=False
    )
    updater.apply_entry(entry)
    before = updater.get_probability("schema_default:db_choice")

    updater.run_batch_update(abandoned=True)
    after = updater.get_probability("schema_default:db_choice")

    assert after < before


def test_delta_clip_max_respected(agent_dir: Path) -> None:
    """Probability updates are bounded by delta_clip_max."""
    agent_dir.mkdir(parents=True, exist_ok=True)
    updater = HeuristicUpdater(agent_dir)
    config = updater.load_config()

    # Seed a probability at 0.5
    entry = ArgumentationEntry(
        question="x", answer="y", was_user_override=True
    )
    updater.apply_entry(entry)

    # The delta should not exceed delta_clip_max
    diff = abs(updater.get_probability("schema_default:x") - 0.5)
    assert diff <= config.delta_clip_max + 1e-9


def test_persistence_across_instances(agent_dir: Path) -> None:
    """Heuristics survive across updater instances after a batch save."""
    agent_dir.mkdir(parents=True, exist_ok=True)
    u1 = HeuristicUpdater(agent_dir)
    entry = ArgumentationEntry(
        question="persistence_test", answer="val", was_user_override=True
    )
    u1.apply_entry(entry)
    # Batch update persists to disk.
    u1.run_batch_update(abandoned=False)
    p1 = u1.get_probability("schema_default:persistence_test")

    u2 = HeuristicUpdater(agent_dir)
    p2 = u2.get_probability("schema_default:persistence_test")
    assert p1 == pytest.approx(p2)


def test_load_config_returns_defaults(updater: HeuristicUpdater) -> None:
    config = updater.load_config()
    assert isinstance(config, HeuristicConfig)
    assert config.delta_clip_max == pytest.approx(0.05)
    assert config.abandonment_penalty == pytest.approx(-0.15)
    assert config.decay_rate == pytest.approx(0.99)
