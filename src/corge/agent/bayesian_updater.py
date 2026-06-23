"""Bayesian Heuristic Updater for the Spec-Wizard.

This module implements the offline/batch Bayesian updater that adjusts the
probability distributions of the agent's Socratic questioning strategies
and tech-stack schema defaults based on historical user interactions.

Spec traceability:
    Argument of Specs RD v4.0 § 5 - Bayesian Self-Improvement
"""

import json
import logging
from pathlib import Path

from corge.contracts import ArgumentationLogPort, HeuristicConfig

_log = logging.getLogger(__name__)


class BayesianUpdater:
    """Concrete implementation of HeuristicUpdaterPort."""

    def __init__(self, agent_dir: Path, log_port: ArgumentationLogPort) -> None:
        self._heuristics_file = agent_dir / "spec_wizard_heuristics.json"
        self._config_path = agent_dir / "corge_heuristics.toml"
        self._log_port = log_port

        # Default probabilities if file doesn't exist
        self._probs: dict[str, float] = {}
        self._load_heuristics()

    def _load_heuristics(self) -> None:
        if self._heuristics_file.exists():
            try:
                content = self._heuristics_file.read_text(encoding="utf-8")
                self._probs = json.loads(content)
            except Exception:
                self._probs = {}

    def _save_heuristics(self) -> None:
        self._heuristics_file.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._probs, indent=2)
        self._heuristics_file.write_text(payload, encoding="utf-8")

    def load_config(self) -> HeuristicConfig:
        """Load optional repo-level configuration."""
        path = self._config_path
        if not path.exists():
            return HeuristicConfig()
        try:
            import tomllib

            with path.open("rb") as f:
                data = tomllib.load(f)
            default_config = HeuristicConfig()
            delta_clip = data.get("delta_clip_max", default_config.delta_clip_max)
            penalty = data.get(
                "abandonment_penalty", default_config.abandonment_penalty
            )
            decay = data.get("decay_rate", default_config.decay_rate)
            return HeuristicConfig(
                delta_clip_max=delta_clip,
                abandonment_penalty=penalty,
                decay_rate=decay,
            )
        except Exception as exc:
            _log.warning("Failed to load heuristics config: %s", exc)
            return HeuristicConfig()

    def get_probability(self, key: str) -> float:
        """Get current probability distribution for a heuristic, default 0.5."""
        return self._probs.get(key, 0.5)

    def run_batch_update(self, abandoned: bool = False) -> None:
        """Run the batch Bayesian update using EWMA.

        The statistical rationale:
        Instead of a complex full Bayesian network which is prone to overfitting
        on small sample sizes (a single developer session), we use an EWMA.
        This provides a "smoothed" posterior probability.

        P_new = (1 - alpha) * P_old + alpha * Observation

        Where:
        - P_old is the prior probability.
        - alpha (decay_rate) controls how much weight we give to the new observation.
        - Observation is 1.0 (success/valuable) or 0.0 (ignored/overwritten).

        To prevent gradient explosion (e.g., catastrophic forgetting of a good
        heuristic because of one bad session), we strictly clip the delta
        (change in probability) to a maximum defined in HeuristicConfig.
        """
        config = self.load_config()
        entries = self._log_port.get_entries()

        if not entries:
            # If the session was abandoned with no entries, penalize the base assumption
            if abandoned:
                prior = self.get_probability("base_engagement")
                delta = config.abandonment_penalty

                # Clip delta
                if abs(delta) > config.delta_clip_max:
                    delta = config.delta_clip_max * (-1 if delta < 0 else 1)

                self._probs["base_engagement"] = max(0.0, min(1.0, prior + delta))
                self._save_heuristics()
            return

        # Example heuristic extraction:
        # Evaluate how often the user manually overrode the agent's schema assumptions
        override_count = sum(1 for e in entries if e.was_user_override)
        total_interactions = len(entries)

        # Observation is the ratio of non-overridden interactions
        observation_value = 0.5
        if total_interactions > 0:
            observation_value = 1.0 - (override_count / total_interactions)

        # EWMA update for the "schema_assumption_validity" heuristic
        prior = self.get_probability("schema_assumption_validity")

        # Calculate raw delta
        alpha = 1.0 - config.decay_rate  # decay_rate usually ~0.99, so alpha is ~0.01
        raw_delta = alpha * (observation_value - prior)

        # Apply strict delta clipping (safety mechanism)
        if abs(raw_delta) > config.delta_clip_max:
            raw_delta = config.delta_clip_max * (-1 if raw_delta < 0 else 1)

        # Calculate posterior and clamp between 0.0 and 1.0
        posterior = prior + raw_delta
        posterior = max(0.0, min(1.0, posterior))

        self._probs["schema_assumption_validity"] = posterior

        # Save updated priors
        self._save_heuristics()
