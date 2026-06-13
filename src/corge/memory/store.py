"""Memory pyramid storage boundaries."""

from corge.contracts import EngineeringProfile, MemoryEvent


class MemoryStore:
    """Memory responsibilities from docs/04-module-contracts.md."""

    def store_event(self, event: MemoryEvent) -> None:
        raise NotImplementedError

    def store_fact(self, fact: str) -> None:
        raise NotImplementedError

    def store_scenario(self, scenario: MemoryEvent) -> None:
        raise NotImplementedError

    def update_profile(self, profile: EngineeringProfile) -> None:
        raise NotImplementedError

