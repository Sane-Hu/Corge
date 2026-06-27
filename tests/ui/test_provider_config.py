"""Tests for provider config screen and startup configuration updates."""

from __future__ import annotations

import tomllib
from pathlib import Path

from corge.__main__ import RealCorgeApp
from corge.ui.provider_config import ProviderConfigScreen


def test_provider_config_screen_init() -> None:
    """ProviderConfigScreen should initialize fields correctly."""
    screen = ProviderConfigScreen(
        error_message="Test connection error",
        prefill={
            "model": "gpt-4o",
            "api_key": "sk-key",
            "base_url": "https://api.com",
            "reasoning_effort": "medium",
            "max_socratic_questions": "5",
        },
    )
    assert screen.error_message == "Test connection error"
    assert screen.prefill["model"] == "gpt-4o"
    assert screen.prefill["api_key"] == "sk-key"
    assert screen.prefill["base_url"] == "https://api.com"
    assert screen.prefill["reasoning_effort"] == "medium"
    assert screen.prefill["max_socratic_questions"] == "5"


def test_update_config_toml_overwrites_correctly(tmp_path: Path) -> None:
    """_update_config_toml writes fields and type conversions properly."""
    config_file = tmp_path / "config.toml"
    # Create empty app context
    app = RealCorgeApp(target_repo=tmp_path, config_path=config_file, global_dir=tmp_path)

    new_cfg = {
        "model": "deepseek-chat",
        "api_key": "sk-1234",
        "base_url": "https://api.deepseek.com/v1",
        "reasoning_effort": "low",
        "max_socratic_questions": "2",
    }
    app._update_config_toml(new_cfg)

    # Read back and parse
    assert config_file.exists()
    with open(config_file, "rb") as f:
        data = tomllib.load(f)

    assert data["model"] == "deepseek-chat"
    assert data["api_key"] == "sk-1234"
    assert data["base_url"] == "https://api.deepseek.com/v1"
    assert data["reasoning_effort"] == "low"
    assert data["max_socratic_questions"] == 2
    # defaults
    assert data["max_tokens"] == 4096
    assert data["keep_alive"] == "-1"
    assert data["timeout"] == 120.0
    assert data["enable_prefix_caching"] is True


def test_update_config_toml_merges_existing_config(tmp_path: Path) -> None:
    """_update_config_toml merges existing config without destroying custom keys."""
    config_file = tmp_path / "config.toml"
    initial_toml = """
    model = "some-model"
    api_key = "placeholder"
    max_tokens = 2048
    enable_prefix_caching = false
    reasoning_effort = "medium"
    max_socratic_questions = 4
    
    [extra_headers]
    X-Test = "value"
    """
    config_file.write_text(initial_toml, encoding="utf-8")

    app = RealCorgeApp(target_repo=tmp_path, config_path=config_file, global_dir=tmp_path)
    new_cfg = {
        "model": "new-model",
        "api_key": "new-key",
        "base_url": "https://api.new.com",
        "reasoning_effort": "",
        "max_socratic_questions": "3",
    }
    app._update_config_toml(new_cfg)

    with open(config_file, "rb") as f:
        data = tomllib.load(f)

    assert data["model"] == "new-model"
    assert data["api_key"] == "new-key"
    assert data["base_url"] == "https://api.new.com"
    assert "reasoning_effort" not in data
    assert data["max_socratic_questions"] == 3
    # custom fields from initial config must be preserved
    assert data["max_tokens"] == 2048
    assert data["enable_prefix_caching"] is False
    assert data["extra_headers"] == {"X-Test": "value"}
