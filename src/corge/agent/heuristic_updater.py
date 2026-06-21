"""Spec-wizard heuristic updater — satisfies ``contracts.HeuristicUpdaterPort``.

Spec traceability:
    Argument of Specs RD § 5 — Bayesian self-improvement
    Resolved Design § 4      — batch execution, abandonment penalty

Runs as a batch phase when a spec is fully executed into code, or when
the user abandons the scenario mid-way.  Reads argumentation_log.json,
adjusts probability distributions, and writes to spec_wizard_heuristics.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from corge.contracts import (
    ArgumentationEntry,
    HeuristicConfig,
)


class HeuristicUpdater:
    """Concrete heuristic updater.  Satisfies ``contracts.HeuristicUpdaterPort``."""

    def __init__(self, agent_dir: Path) -> None:
        self._heuristics_path = agent_dir / "spec_wizard_heuristics.json"
        self._config = HeuristicConfig()
        self._probabilities: dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        """Load existing heuristics from disk, or initialise empty."""
        if self._heuristics_path.exists():
            data = json.loads(self._heuristics_path.read_text(encoding="utf-8"))
            self._probabilities = data.get("probabilities", {})
        else:
            self._probabilities = {}

    def _save(self) -> None:
        self._heuristics_path.parent.mkdir(parents=True, exist_ok=True)
        self._heuristics_path.write_text(
            json.dumps({"probabilities": self._probabilities}, indent=2),
            encoding="utf-8",
        )

    def _clip_delta(self, delta: float) -> float:
        """Clip a probability update to prevent over-fitting."""
        limit = self._config.delta_clip_max
        return max(-limit, min(limit, delta))

    def run_batch_update(self, abandoned: bool = False) -> None:
        """Process argumentation log and update heuristics.

        If ``abandoned`` is True, applies the abandonment penalty — the
        system speculates the spec agent frustrated the user.
        """
        if abandoned:
            for key in list(self._probabilities):
                raw = self._config.abandonment_penalty
                self._probabilities[key] = max(
                    0.0, self._probabilities[key] + self._clip_delta(raw)
                )

        # Apply global decay to prevent stagnation.
        for key in self._probabilities:
            self._probabilities[key] *= self._config.decay_rate

        self._save()

    def apply_entry(self, entry: ArgumentationEntry) -> None:
        """Update heuristics based on a single argumentation entry.

        If the user overrode the agent's answer, decrease P(Schema Default)
        for the question's topic.  Otherwise, slightly increase it.
        """
        key = f"schema_default:{entry.question[:64]}"
        current = self._probabilities.get(key, 0.5)
        delta = -0.03 if entry.was_user_override else 0.01
        self._probabilities[key] = max(
            0.0, min(1.0, current + self._clip_delta(delta))
        )

    def get_probability(self, key: str) -> float:
        return self._probabilities.get(key, 0.5)

    def load_config(self) -> HeuristicConfig:
        return self._config
