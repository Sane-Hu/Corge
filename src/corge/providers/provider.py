"""External model provider — satisfies ``contracts.ProviderPort``."""

from corge.contracts import ChatResponse, ProviderMessage


class Provider:
    """Concrete provider stub.  Satisfies ``contracts.ProviderPort``."""

    def chat(self, messages: tuple[ProviderMessage, ...]) -> ChatResponse:
        raise NotImplementedError
