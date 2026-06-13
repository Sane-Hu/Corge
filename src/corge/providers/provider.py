"""External model provider boundary."""

from corge.contracts import ChatResponse, ProviderMessage


class Provider:
    """Provider responsibilities from docs/04-module-contracts.md."""

    def chat(self, messages: tuple[ProviderMessage, ...]) -> ChatResponse:
        raise NotImplementedError

