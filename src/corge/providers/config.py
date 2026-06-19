"""Provider configuration for the OpenAI-compatible adapter.

This dataclass is internal to the ``providers`` package and is NOT a
contract boundary object.  Callers construct a ``ProviderConfig`` and
pass it to ``Provider.__init__``.

Supported provider families (all share the OpenAI REST wire format):
- OpenAI           — api.openai.com
- DeepSeek         — api.deepseek.com  (prefix caching via extra_body)
- Ollama           — localhost:11434/v1 (keep_alive to hold model in RAM)
- Any other OpenAI-compatible endpoint

Spec traceability:
    FRD FR-014 — provider abstraction
    PRD         — DeepSeek, Ollama, OpenAI-compat
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProviderConfig:
    """All knobs for a single provider instance.

    Args:
        model: Model identifier as accepted by the provider API.
        api_key: API key.  Empty string is accepted for Ollama (no auth).
        base_url: Base URL override.  Leave empty to use the SDK default
            (``https://api.openai.com/v1``).  Examples:
            - DeepSeek: ``https://api.deepseek.com/v1``
            - Ollama:   ``http://localhost:11434/v1``
        max_tokens: Maximum completion tokens.  0 means use the API default.
        reasoning_effort: Hint passed to reasoning models that accept it
            (``"low"``, ``"medium"``, ``"high"``).  ``None`` means omit the
            field entirely so the API/model decides.
        enable_prefix_caching: When ``True``, set ``prefix_caching=True`` in
            the request ``extra_body`` for providers that support it (e.g.
            DeepSeek).  Has no effect on providers that ignore unknown fields.
        keep_alive: Ollama keep-alive value appended to ``extra_body``.
            ``"-1"`` keeps the model loaded indefinitely.  Ignored by
            non-Ollama endpoints.
        timeout: HTTP request timeout in seconds.
        extra_headers: Optional headers forwarded verbatim to every request
            (e.g. ``{"X-Title": "corge"}``).
    """

    model: str
    api_key: str = ""
    base_url: str = ""
    max_tokens: int = 4096
    # reasoning/thinking mode
    reasoning_effort: str | None = None
    # DeepSeek-style prefix caching
    enable_prefix_caching: bool = True
    # Ollama: keep model loaded between calls
    keep_alive: str = "-1"
    timeout: float = 120.0
    extra_headers: dict[str, str] = field(default_factory=dict)
