"""Tests for DirectorySelectorApp in cli.py."""

from pathlib import Path
from unittest.mock import MagicMock

from corge.ui.cli import DirectorySelectorApp


def test_directory_selector_selects_highlighted(tmp_path: Path) -> None:
    """Verifies DirectorySelectorApp.action_select_current resolves path and exits."""
    app = DirectorySelectorApp()

    tree_mock = MagicMock()

    node_mock = MagicMock()
    node_mock.data.path = tmp_path
    tree_mock.cursor_node = node_mock

    app.query_one = MagicMock(return_value=tree_mock)
    app.exit = MagicMock()

    app.action_select_current()
    app.exit.assert_called_once_with(tmp_path.resolve())


def test_procedural_steps_editor_preserves_identifiers() -> None:
    """Verifies that the procedural steps editor preserves custom bracketed identifiers."""
    from corge.contracts import ProceduralStep
    from corge.ui.cli import CliUi

    app_mock = MagicMock()
    ui = CliUi(app_mock)

    # Mock _run_screen to return custom identifiers, standard text, and bracketed IDs with spaces
    ui._run_screen = MagicMock(
        return_value="[step-auth] Authenticate user\nAnother step description\n  [custom-id] Step with spaces"
    )

    original_steps = (
        ProceduralStep(identifier="step-1", description="Original step"),
    )
    result = ui.show_procedural_steps_editor(original_steps)

    assert result is not None
    assert len(result) == 3
    assert result[0].identifier == "step-auth"
    assert result[0].description == "Authenticate user"
    assert result[1].identifier == "step-2"
    assert result[1].description == "Another step description"
    assert result[2].identifier == "custom-id"
    assert result[2].description == "Step with spaces"


def test_message_screen_back_button() -> None:
    from corge.ui.cli import MessageScreen
    screen = MessageScreen("Title", "Message", show_back=True)
    screen.dismiss = MagicMock()
    screen.action_back()
    screen.dismiss.assert_called_once_with("back")


def test_message_screen_new_spec_button() -> None:
    from corge.ui.cli import MessageScreen
    screen = MessageScreen("Title", "Message", show_back=True, show_new_spec=True)
    screen.dismiss = MagicMock()
    screen.action_new_spec()
    screen.dismiss.assert_called_once_with("new_spec")


def test_canvas_screen_cancel_returns_none() -> None:
    from corge.ui.freestyle_canvas import CanvasScreen
    canvas = CanvasScreen(validator=None)
    canvas.dismiss = MagicMock()
    canvas.action_cancel()
    canvas.dismiss.assert_called_once_with(None)


def test_directory_selector_configure_api(tmp_path: Path) -> None:
    """Verifies DirectorySelectorApp.action_configure_api resolves path and handles config screen save."""
    import tomllib
    app = DirectorySelectorApp()

    # Pre-create config file in tmp_path to prevent fallback to global user config
    local_config = tmp_path / "CorgeAPIConfig.toml"
    local_config.touch()

    # Mock tree
    tree_mock = MagicMock()
    tree_mock.path = str(tmp_path)
    tree_mock.cursor_node = None
    
    app.query_one = MagicMock(return_value=tree_mock)
    
    # Mock push_screen to capture the callback
    pushed_screen = None
    captured_callback = None
    
    def mock_push_screen(screen, callback=None):
        nonlocal pushed_screen, captured_callback
        pushed_screen = screen
        captured_callback = callback

    app.push_screen = mock_push_screen

    # Execute action
    app.action_configure_api()

    # Assert correct screen is pushed
    from corge.ui.provider_config import ProviderConfigScreen
    assert isinstance(pushed_screen, ProviderConfigScreen)
    assert captured_callback is not None

    # Invoke the captured on_save callback with mock config data
    config_data = {
        "model": "test-model-123",
        "api_key": "test-key-123",
        "base_url": "https://api.test-123.com",
    }
    captured_callback(config_data)

    # Check that the config file is written
    assert local_config.exists()
    with open(local_config, "rb") as f:
        data = tomllib.load(f)

    assert data["model"] == "test-model-123"
    assert data["api_key"] == "test-key-123"
    assert data["base_url"] == "https://api.test-123.com"
    assert data["max_tokens"] == 4096
    assert data["keep_alive"] == "-1"
    assert data["timeout"] == 120.0
    assert data["enable_prefix_caching"] is True



