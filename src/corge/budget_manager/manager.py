"""Context budget enforcement boundaries."""

from corge.contracts import ContextBundle


class BudgetManager:
    """Budget manager responsibilities from docs/04-module-contracts.md."""

    def estimate_tokens(self, context: ContextBundle) -> int:
        raise NotImplementedError

    def rank_context(self, context: ContextBundle) -> ContextBundle:
        raise NotImplementedError

    def clip(self, context: ContextBundle, token_limit: int) -> ContextBundle:
        raise NotImplementedError

    def deduplicate(self, context: ContextBundle) -> ContextBundle:
        raise NotImplementedError

    def summarize(self, context: ContextBundle) -> str:
        raise NotImplementedError

    def compact(self, context: ContextBundle) -> ContextBundle:
        raise NotImplementedError

