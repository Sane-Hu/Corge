"""Context retrieval and refresh — satisfies ``contracts.ContextPort``."""

import pathlib

from corge.contracts import (
    ContextBundle,
    EngineeringProfile,
    MarkovStepContext,
    Plan,
    PlanStep,
    RepositoryContext,
    Specification,
)


class ContextService:
    """Concrete context stub.  Satisfies ``contracts.ContextPort`` protocol."""

    def __init__(self) -> None:
        self._last_step_result: str = ""
        self._last_user_correction: str = ""
        self._compressed_history: list[str] = []

    def _get_dummy_spec(self) -> Specification:
        from corge.contracts import AcceptanceCriteria
        return Specification(
            title="", body="", acceptance_criteria=AcceptanceCriteria(())
        )

    def _get_dummy_plan(self) -> Plan:
        return Plan(())

    def load_context(self, repository_context: RepositoryContext) -> ContextBundle:
        """Load full context, strictly ensuring Layer 1 Argumentation is absent."""
        return ContextBundle(
            specification=self._get_dummy_spec(),
            plan=self._get_dummy_plan(),
            repository_context=repository_context,
            engineering_profile=EngineeringProfile(),
            # Explicitly omitting argumentation history to prevent leakage
        )

    def refresh_context(self, repository_context: RepositoryContext) -> ContextBundle:
        """Refresh context for the Planning layer (Layer 2)."""
        return self.load_context(repository_context)

    def retrieve_relevant_context(
        self, specification: Specification, step: PlanStep
    ) -> ContextBundle:
        """Retrieve relevant context for the Coding layer (Layer 3) using Markov chaining.
        
        Injects Step N-1 outputs and compresses older history to prevent context explosion.
        """
        # Compress N-2 and older
        if self._last_step_result:
            truncated = self._last_step_result[:100]
            self._compressed_history.append(f"Prev step result: {truncated}...")
            if len(self._compressed_history) > 3:
                self._compressed_history.pop(0)

        markov_ctx = MarkovStepContext(
            agent_proposal=self._last_step_result,
            user_correction=self._last_user_correction,
            compressed_trajectory=" | ".join(self._compressed_history)
        )

        return ContextBundle(
            specification=specification,
            plan=Plan((step,), specification_ref=specification.title),
            repository_context=RepositoryContext(root=pathlib.Path(".")),
            engineering_profile=EngineeringProfile(),
            markov_context=markov_ctx
        )

    def update_markov_state(self, result: str, correction: str = "") -> None:
        """Update the N-1 state after a step completes."""
        self._last_step_result = result
        self._last_user_correction = correction
