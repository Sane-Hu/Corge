"""Provider abstraction layer (FR-014).

Exports:
    Provider       — concrete OpenAI-compatible adapter.
    ProviderConfig — configuration dataclass for Provider.__init__.
    ProviderPort   — typing.Protocol interface (from contracts).
"""

from corge.contracts import ProviderPort
from corge.providers.config import ProviderConfig
from corge.providers.provider import Provider

__all__ = ["Provider", "ProviderConfig", "ProviderPort"]
