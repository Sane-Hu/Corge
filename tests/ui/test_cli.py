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
