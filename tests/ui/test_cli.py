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
    from corge.ui.cli import CliUi
    from corge.contracts import ProceduralStep

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

