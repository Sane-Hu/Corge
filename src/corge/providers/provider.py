"""OpenAI-compatible provider adapter — satisfies ``contracts.ProviderPort``.

Supported provider families:
- OpenAI           (automatic server-side prompt caching for long prompts)
- DeepSeek         (prefix caching via ``extra_body``)
- Ollama           (keep_alive to hold model in RAM between calls)
- Any OpenAI-compatible endpoint

Spec traceability:
    FRD FR-014  — single integration point for model APIs
    PRD         — DeepSeek, Ollama, OpenAI-compat; reasoning/thinking mode;
                  context caching to save costs
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import openai

from corge.contracts import ChatResponse, ProviderMessage
from corge.providers.config import ProviderConfig


class Provider:
    """Concrete provider adapter.  Satisfies ``contracts.ProviderPort``.

    Usage::

        cfg = ProviderConfig(
            model="deepseek-chat",
            api_key="sk-...",
            base_url="https://api.deepseek.com/v1",
        )
        provider = Provider(cfg)
        response = provider.chat((ProviderMessage(role="user", content="Hello"),))

    Context caching behaviour
    -------------------------
    * **OpenAI**: server-side automatic caching applies to prompts > 1024
      tokens; the adapter surfaces ``cached_tokens`` in ``ChatResponse.usage``
      when the API reports it.
    * **DeepSeek**: ``prefix_caching=True`` is injected in ``extra_body`` when
      ``ProviderConfig.enable_prefix_caching`` is ``True`` (the default).
    * **Ollama**: ``keep_alive`` is set in ``extra_body`` so the model remains
      loaded in RAM between calls.

    Reasoning/thinking mode
    -----------------------
    When ``ProviderConfig.reasoning_effort`` is set and the model supports it,
    the effort hint is forwarded via the SDK.  Thinking tokens embedded in the
    assistant message are stripped before the text content is returned; only
    the final prose answer is exposed through ``ChatResponse.content``.
    """

    def __init__(self, config: ProviderConfig) -> None:
        self._config = config
        base_url = config.base_url
        if not base_url:
            if config.api_key.startswith("sk-or-"):
                base_url = "https://openrouter.ai/api/v1"
            elif config.model.startswith("deepseek-"):
                base_url = "https://api.deepseek.com/v1"

        client_kwargs: dict[str, object] = {
            "api_key": config.api_key or "not-needed",
            "timeout": config.timeout,
        }
        if base_url:
            client_kwargs["base_url"] = base_url
        if config.extra_headers:
            client_kwargs["default_headers"] = config.extra_headers

        self._client = openai.OpenAI(**client_kwargs)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Public interface (ProviderPort)
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: tuple[ProviderMessage, ...],
        on_token: Callable[[str], None] | None = None,
    ) -> ChatResponse:
        """Send a chat request and return the assistant reply.

        Args:
            messages: Ordered conversation history.  The caller is responsible
                for keeping this within the model's context window.

        Returns:
            ``ChatResponse`` with the assistant text and token usage.

        Raises:
            openai.OpenAIError: On any API-level failure (rate limit, auth,
                network, etc.).
        """
        cfg = self._config
        extra_body: dict[str, object] = {}

        if cfg.enable_prefix_caching:
            # DeepSeek honours this field; other providers ignore unknown keys.
            extra_body["prefix_caching"] = True

        if cfg.base_url and "11434" in cfg.base_url:
            # Ollama: keep model loaded between calls.
            extra_body["keep_alive"] = cfg.keep_alive

        create_kwargs: dict[str, object] = {
            "model": cfg.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }

        if cfg.max_tokens > 0:
            create_kwargs["max_completion_tokens"] = cfg.max_tokens

        if cfg.reasoning_effort is not None:
            # OpenAI o-series, DeepSeek R1 both accept this.
            create_kwargs["reasoning_effort"] = cfg.reasoning_effort

        if extra_body:
            create_kwargs["extra_body"] = extra_body

        if on_token:
            create_kwargs["stream"] = True
            create_kwargs["stream_options"] = {"include_usage": True}
            stream = self._client.chat.completions.create(**create_kwargs)  # type: ignore[call-overload]
            
            full_content = []
            usage_obj = None
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_content.append(token)
                    on_token(token)
                
                # Usage is usually sent in the final chunk when include_usage=True
                if hasattr(chunk, "usage") and chunk.usage:
                    usage_obj = chunk.usage
            
            raw_content = "".join(full_content)
            content = _strip_thinking_tags(raw_content)
            usage = self._extract_usage(usage_obj)
            return ChatResponse(content=content, usage=usage)

        completion = self._client.chat.completions.create(**create_kwargs)  # type: ignore[call-overload]
        return self._parse_response(completion)

    def validate_connection(self) -> bool:
        """Verify the API connection and endpoint by sending a minimal chat request.

        Returns:
            True if the connection and credentials are valid and the API responds
            successfully; False otherwise.
        """
        try:
            self._client.chat.completions.create(
                model=self._config.model,
                messages=[{"role": "user", "content": "ping"}],
                max_completion_tokens=1,
            )
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_response(
        self, completion: openai.types.chat.ChatCompletion
    ) -> ChatResponse:
        """Extract text content and usage from a completion object.

        Thinking tokens (from DeepSeek R1 or o1-style models) are embedded in
        ``choice.message.reasoning_content`` by DeepSeek or wrapped in
        ``<think>...</think>`` blocks in the content string by some OSS models.
        We strip the ``<think>`` wrapper so ``ChatResponse.content`` always
        contains only the final prose answer.
        """
        choice = completion.choices[0]
        raw_content: str = choice.message.content or ""

        # Strip <think>...</think> blocks (OSS reasoning models).
        content = _strip_thinking_tags(raw_content)

        usage = self._extract_usage(completion.usage)
        return ChatResponse(content=content, usage=usage)

    def _extract_usage(self, usage_obj: Any) -> dict[str, int]:
        """Extract standard token usage dictionary from an OpenAI usage object."""
        usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        }
        if usage_obj:
            usage["prompt_tokens"] = usage_obj.prompt_tokens or 0
            usage["completion_tokens"] = usage_obj.completion_tokens or 0
            # OpenAI reports cached tokens inside prompt_tokens_details.
            ptd = getattr(usage_obj, "prompt_tokens_details", None)
            if ptd is not None:
                usage["cache_read_tokens"] = getattr(ptd, "cached_tokens", 0) or 0
            # DeepSeek reports cache hits in usage extensions.
            usage_extras = getattr(usage_obj, "model_extra", None) or {}
            usage["cache_read_tokens"] = usage["cache_read_tokens"] or (
                usage_extras.get("prompt_cache_hit_tokens", 0) or 0
            )
            usage["cache_write_tokens"] = (
                usage_extras.get("prompt_cache_miss_tokens", 0) or 0
            )
        return usage


def _strip_thinking_tags(text: str) -> str:
    """Remove ``<think>…</think>`` blocks from model output.

    Some open-source reasoning models (Qwen-thinking, certain DeepSeek
    finetuned versions) embed chain-of-thought inside the content field
    wrapped in ``<think>`` tags.  The budget manager and downstream
    consumers only need the final answer.

    This is intentionally simple: it handles a single top-level block.
    Nested or malformed tags fall through unmodified.

    todo: if models start emitting multiple think blocks, replace with a
    regex substitution: ``re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)``
    """
    open_tag, close_tag = "<think>", "</think>"
    start = text.find(open_tag)
    if start == -1:
        return text
    end = text.find(close_tag, start)
    if end == -1:
        return text
    return (text[:start] + text[end + len(close_tag) :]).strip()


def bootstrap_provider(config_path: str | Path = "config.toml") -> Provider:
    """Initialize the LLM Provider using the user's TOML config file.

    It loads the configuration, checks for placeholder values, instantiates
    the Provider, and validates that the endpoint is working before returning
    the initialized provider instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If placeholder values (e.g. "your-api-key-here") are found.
        ConnectionError: If the API endpoint is unreachable or credentials are invalid.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Configuration file '{path.name}' was not found in "
            f"'{path.parent.absolute()}'.\n"
            f"Please copy the template file 'config.toml.example' from the "
            f"repository root to '{path.absolute()}' and populate it with "
            f"your API details."
        )

    cfg = ProviderConfig.from_toml_file(path)

    # Check for placeholder values
    if cfg.api_key == "your-api-key-here":
        raise ValueError(
            f"Placeholder value detected for 'api_key' in '{path.absolute()}'. "
            f"Please edit the file and replace 'your-api-key-here' with "
            f"your actual API key."
        )

    provider = Provider(cfg)

    if not provider.validate_connection():
        actual_url = str(provider._client.base_url)
        raise ConnectionError(
            f"Failed to verify LLM API connection to '{actual_url}' "
            f"using model '{cfg.model}'. Please check your API key, base URL, "
            f"model name, and network settings."
        )

    return provider
