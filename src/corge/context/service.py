"""Context retrieval and refresh — satisfies ``contracts.ContextPort``."""

from corge.contracts import ContextBundle, PlanStep, RepositoryContext, Specification


class ContextService:
    """Concrete context stub.  Satisfies ``contracts.ContextPort`` protocol."""

    def load_context(self, repository_context: RepositoryContext) -> ContextBundle:
        raise NotImplementedError

    def refresh_context(self, repository_context: RepositoryContext) -> ContextBundle:
        raise NotImplementedError

    def retrieve_relevant_context(
        self, specification: Specification, step: PlanStep
    ) -> ContextBundle:
        raise NotImplementedError
