"""Memory pyramid storage — satisfies ``contracts.MemoryStorePort``."""

from corge.contracts import EngineeringProfile, MemoryEvent


class MemoryStore:
    """Concrete memory store stub.  Satisfies ``contracts.MemoryStorePort``."""

    def store_event(self, event: MemoryEvent) -> None:
        raise NotImplementedError

    def store_fact(self, fact: str) -> None:
        raise NotImplementedError

    def store_scenario(self, scenario: MemoryEvent) -> None:
        raise NotImplementedError

    def update_profile(self, profile: EngineeringProfile) -> None:
        raise NotImplementedError
