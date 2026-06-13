"""Context retrieval and refresh boundaries."""

from corge.contracts import ContextBundle, PlanStep, RepositoryContext, Specification


class ContextService:
    """Context responsibilities from docs/04-module-contracts.md."""

    def load_context(self, repository_context: RepositoryContext) -> ContextBundle:
        raise NotImplementedError

    def refresh_context(self, repository_context: RepositoryContext) -> ContextBundle:
        raise NotImplementedError

    def retrieve_relevant_context(
        self, specification: Specification, step: PlanStep
    ) -> ContextBundle:
        raise NotImplementedError

