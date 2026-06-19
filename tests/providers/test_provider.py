"""Tests for the Provider adapter (FR-014).

All HTTP calls are mocked — no network required.

Spec traceability:
    FRD FR-014 — provider abstraction (OpenAI-compat, reasoning, caching)
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from corge.contracts import ChatResponse, ProviderMessage, ProviderPort
from corge.providers import Provider, ProviderConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completion(
    content: str,
    prompt_tokens: int = 100,
    completion_tokens: int = 20,
    cached_tokens: int = 0,
    model_extra: dict | None = None,
) -> MagicMock:
    """Build a mock openai.types.chat.ChatCompletion."""
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        prompt_tokens_details=SimpleNamespace(cached_tokens=cached_tokens),
        model_extra=model_extra or {},
    )
    choice = SimpleNamespace(message=SimpleNamespace(content=content))
    comp = MagicMock()
    comp.choices = [choice]
    comp.usage = usage
    return comp


def _default_config(**kwargs: object) -> ProviderConfig:
    return ProviderConfig(model="test-model", api_key="sk-test", **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_provider_satisfies_protocol() -> None:
    """Provider must be a structural subtype of ProviderPort."""
    instance = object.__new__(Provider)
    assert isinstance(instance, ProviderPort)


# ---------------------------------------------------------------------------
# Basic chat mapping
# ---------------------------------------------------------------------------


def test_openai_chat_maps_response() -> None:
    """chat() returns a ChatResponse with correct content and usage keys."""
    cfg = _default_config()
    provider = Provider(cfg)

    mock_completion = _make_completion(
        "Hello!", prompt_tokens=50, completion_tokens=5
    )
    with patch.object(
        provider._client.chat.completions,
        "create",
        return_value=mock_completion,
    ):
        resp = provider.chat((ProviderMessage(role="user", content="Hi"),))

    assert isinstance(resp, ChatResponse)
    assert resp.content == "Hello!"
    assert resp.usage["prompt_tokens"] == 50
    assert resp.usage["completion_tokens"] == 5


def test_usage_keys_always_present() -> None:
    """All four cache/token keys must be present even when API omits them."""
    provider = Provider(_default_config())
    mock_completion = _make_completion("ok", prompt_tokens=0, completion_tokens=0)
    mock_completion.usage = None  # simulate missing usage

    with patch.object(
        provider._client.chat.completions, "create", return_value=mock_completion
    ):
        resp = provider.chat((ProviderMessage(role="user", content="x"),))

    for key in (
        "prompt_tokens", "completion_tokens", "cache_read_tokens", "cache_write_tokens"
    ):
        assert key in resp.usage, f"missing key: {key}"
        assert isinstance(resp.usage[key], int)


# ---------------------------------------------------------------------------
# Reasoning / thinking mode
# ---------------------------------------------------------------------------


def test_reasoning_effort_forwarded() -> None:
    """When reasoning_effort is set, it is passed to the API."""
    cfg = _default_config(reasoning_effort="low")
    provider = Provider(cfg)

    mock_completion = _make_completion("answer")
    with patch.object(
        provider._client.chat.completions,
        "create",
        return_value=mock_completion,
    ) as mock_create:
        provider.chat((ProviderMessage(role="user", content="q"),))
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs.get("reasoning_effort") == "low"


def test_reasoning_effort_omitted_when_none() -> None:
    """When reasoning_effort is None, the key must NOT be sent to the API."""
    cfg = _default_config(reasoning_effort=None)
    provider = Provider(cfg)

    mock_completion = _make_completion("answer")
    with patch.object(
        provider._client.chat.completions,
        "create",
        return_value=mock_completion,
    ) as mock_create:
        provider.chat((ProviderMessage(role="user", content="q"),))
        call_kwargs = mock_create.call_args.kwargs
        assert "reasoning_effort" not in call_kwargs


def test_strips_think_tags() -> None:
    """Thinking tokens wrapped in <think> blocks are stripped from content."""
    cfg = _default_config()
    provider = Provider(cfg)

    raw = "<think>step 1\nstep 2</think>\nFinal answer."
    mock_completion = _make_completion(raw)
    with patch.object(
        provider._client.chat.completions, "create", return_value=mock_completion
    ):
        resp = provider.chat((ProviderMessage(role="user", content="q"),))

    assert "<think>" not in resp.content
    assert "Final answer." in resp.content


def test_strips_think_tags_no_tag() -> None:
    """Content without <think> tags is returned unchanged."""
    cfg = _default_config()
    provider = Provider(cfg)

    mock_completion = _make_completion("plain answer")
    with patch.object(
        provider._client.chat.completions, "create", return_value=mock_completion
    ):
        resp = provider.chat((ProviderMessage(role="user", content="q"),))

    assert resp.content == "plain answer"


# ---------------------------------------------------------------------------
# Context caching — DeepSeek prefix caching
# ---------------------------------------------------------------------------


def test_deepseek_prefix_caching_in_extra_body() -> None:
    """enable_prefix_caching=True injects prefix_caching into extra_body."""
    cfg = _default_config(enable_prefix_caching=True)
    provider = Provider(cfg)

    mock_completion = _make_completion("ok")
    with patch.object(
        provider._client.chat.completions,
        "create",
        return_value=mock_completion,
    ) as mock_create:
        provider.chat((ProviderMessage(role="user", content="q"),))
        call_kwargs = mock_create.call_args.kwargs
        extra_body = call_kwargs.get("extra_body", {})
        assert extra_body.get("prefix_caching") is True


def test_prefix_caching_disabled() -> None:
    """enable_prefix_caching=False must not add prefix_caching to extra_body."""
    cfg = _default_config(enable_prefix_caching=False)
    provider = Provider(cfg)

    mock_completion = _make_completion("ok")
    with patch.object(
        provider._client.chat.completions,
        "create",
        return_value=mock_completion,
    ) as mock_create:
        provider.chat((ProviderMessage(role="user", content="q"),))
        call_kwargs = mock_create.call_args.kwargs
        extra_body = call_kwargs.get("extra_body", {})
        assert "prefix_caching" not in extra_body


def test_openai_cache_read_tokens_surfaced() -> None:
    """OpenAI cached_tokens from prompt_tokens_details surfaces in usage."""
    provider = Provider(_default_config())
    mock_completion = _make_completion("ok", cached_tokens=512)

    with patch.object(
        provider._client.chat.completions, "create", return_value=mock_completion
    ):
        resp = provider.chat((ProviderMessage(role="user", content="q"),))

    assert resp.usage["cache_read_tokens"] == 512


def test_deepseek_cache_hit_tokens_surfaced() -> None:
    """DeepSeek prompt_cache_hit_tokens surfaces in cache_read_tokens."""
    provider = Provider(_default_config())
    mock_completion = _make_completion(
        "ok",
        model_extra={"prompt_cache_hit_tokens": 256, "prompt_cache_miss_tokens": 44},
    )
    # Remove OpenAI-style cached tokens so only DeepSeek path is exercised.
    mock_completion.usage.prompt_tokens_details = None

    with patch.object(
        provider._client.chat.completions, "create", return_value=mock_completion
    ):
        resp = provider.chat((ProviderMessage(role="user", content="q"),))

    assert resp.usage["cache_read_tokens"] == 256
    assert resp.usage["cache_write_tokens"] == 44


# ---------------------------------------------------------------------------
# Context caching — Ollama keep_alive
# ---------------------------------------------------------------------------


def test_ollama_keep_alive_in_extra_body() -> None:
    """Ollama base URLs trigger keep_alive in extra_body."""
    cfg = ProviderConfig(
        model="test-model",
        api_key="",
        base_url="http://localhost:11434/v1",
        keep_alive="-1",
    )
    provider = Provider(cfg)

    mock_completion = _make_completion("ok")
    with patch.object(
        provider._client.chat.completions,
        "create",
        return_value=mock_completion,
    ) as mock_create:
        provider.chat((ProviderMessage(role="user", content="q"),))
        call_kwargs = mock_create.call_args.kwargs
        extra_body = call_kwargs.get("extra_body", {})
        assert extra_body.get("keep_alive") == "-1"


def test_non_ollama_no_keep_alive() -> None:
    """Non-Ollama endpoints must not receive keep_alive in extra_body."""
    cfg = _default_config(base_url="https://api.deepseek.com/v1")
    provider = Provider(cfg)

    mock_completion = _make_completion("ok")
    with patch.object(
        provider._client.chat.completions,
        "create",
        return_value=mock_completion,
    ) as mock_create:
        provider.chat((ProviderMessage(role="user", content="q"),))
        call_kwargs = mock_create.call_args.kwargs
        extra_body = call_kwargs.get("extra_body", {})
        assert "keep_alive" not in extra_body


# ---------------------------------------------------------------------------
# max_tokens / no max_tokens
# ---------------------------------------------------------------------------


def test_max_tokens_forwarded() -> None:
    """max_tokens > 0 is forwarded as max_completion_tokens."""
    cfg = _default_config(max_tokens=2048)
    provider = Provider(cfg)

    mock_completion = _make_completion("ok")
    with patch.object(
        provider._client.chat.completions,
        "create",
        return_value=mock_completion,
    ) as mock_create:
        provider.chat((ProviderMessage(role="user", content="q"),))
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs.get("max_completion_tokens") == 2048


def test_max_tokens_zero_omitted() -> None:
    """max_tokens=0 must NOT send max_completion_tokens (use API default)."""
    cfg = _default_config(max_tokens=0)
    provider = Provider(cfg)

    mock_completion = _make_completion("ok")
    with patch.object(
        provider._client.chat.completions,
        "create",
        return_value=mock_completion,
    ) as mock_create:
        provider.chat((ProviderMessage(role="user", content="q"),))
        call_kwargs = mock_create.call_args.kwargs
        assert "max_completion_tokens" not in call_kwargs
