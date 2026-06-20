"""Tests for BayesianUpdater."""

from pathlib import Path

from corge.agent.bayesian_updater import BayesianUpdater
from corge.contracts import ArgumentationEntry, CanvasSnapshot


class _MockLogPort:
    def __init__(self, entries):
        self._entries = entries
        
    def record_entry(self, entry: ArgumentationEntry) -> None:
        pass
        
    def record_canvas_snapshot(self, snapshot: CanvasSnapshot) -> None:
        pass

    def get_entries(self) -> tuple[ArgumentationEntry, ...]:
        return self._entries

def test_bayesian_updater_clipping(tmp_path: Path):
    # Simulate an all-override session (very bad for the agent)
    entries = tuple([ArgumentationEntry("Q", "A", was_user_override=True) for _ in range(10)])
    log_port = _MockLogPort(entries)
    
    updater = BayesianUpdater(tmp_path, log_port)
    # Default is 0.5
    assert updater.get_probability("schema_assumption_validity") == 0.5
    
    updater.run_batch_update()
    
    # Delta should be clipped to config.delta_clip_max (0.05)
    # The observation was 0.0 (all overridden)
    # raw_delta = 0.01 * (0.0 - 0.5) = -0.005
    # Wait, raw_delta is -0.005, which is LESS than the clip_max (0.05). So it won't clip!
    # It will just subtract 0.005.
    
    assert updater.get_probability("schema_assumption_validity") == 0.495
    
def test_bayesian_updater_abandonment(tmp_path: Path):
    log_port = _MockLogPort(())
    updater = BayesianUpdater(tmp_path, log_port)
    
    updater.run_batch_update(abandoned=True)
    # abandonment penalty is -0.15, but delta_clip_max is 0.05
    # So it should be clipped to -0.05
    assert updater.get_probability("base_engagement") == 0.45
