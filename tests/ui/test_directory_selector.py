"""Tests for the interactive CLI directory selector."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from corge.ui.directory_selector import choose_directory_cli


def test_choose_directory_cli_confirm_current(tmp_path: Path) -> None:
    """Option 0 confirms and returns the current directory."""
    with patch("builtins.input", side_effect=["0"]):
        res = choose_directory_cli(tmp_path)
        assert res == tmp_path


def test_choose_directory_cli_navigate_up(tmp_path: Path) -> None:
    """Option 1 navigates to parent directory, then option 0 selects it."""
    child = tmp_path / "child"
    child.mkdir()
    with patch("builtins.input", side_effect=["1", "0"]):
        res = choose_directory_cli(child)
        assert res == tmp_path


def test_choose_directory_cli_create_new(tmp_path: Path) -> None:
    """Option 2 creates a new directory, navigates to it, and option 0 selects it."""
    with patch("builtins.input", side_effect=["2", "new_folder", "0"]):
        res = choose_directory_cli(tmp_path)
        assert res == tmp_path / "new_folder"
        assert (tmp_path / "new_folder").is_dir()


def test_choose_directory_cli_navigate_into_subdir(tmp_path: Path) -> None:
    """Choosing index 4 navigates into the first listed subdirectory."""
    child1 = tmp_path / "subdir_a"
    child1.mkdir()
    child2 = tmp_path / "subdir_b"
    child2.mkdir()
    
    # subdir_a will be index 4, subdir_b index 5
    with patch("builtins.input", side_effect=["4", "0"]):
        res = choose_directory_cli(tmp_path)
        assert res == child1


def test_choose_directory_cli_manual_path_existing(tmp_path: Path) -> None:
    """Option 3 lets the user enter an existing directory path directly."""
    target_dir = tmp_path / "existing_dir"
    target_dir.mkdir()
    with patch("builtins.input", side_effect=["3", str(target_dir), "0"]):
        res = choose_directory_cli(tmp_path)
        assert res == target_dir


def test_choose_directory_cli_manual_path_create_missing(tmp_path: Path) -> None:
    """Option 3 prompts to create the directory if it is missing."""
    target_dir = tmp_path / "missing_dir"
    with patch("builtins.input", side_effect=["3", str(target_dir), "y", "0"]):
        res = choose_directory_cli(tmp_path)
        assert res == target_dir
        assert target_dir.is_dir()


def test_choose_directory_cli_invalid_input_retry(tmp_path: Path) -> None:
    """Invalid input prompts for retry until a valid option is selected."""
    # "abc" (invalid), "99" (out of bounds), "0" (confirm)
    with patch("builtins.input", side_effect=["abc", "99", "0"]):
        res = choose_directory_cli(tmp_path)
        assert res == tmp_path


def test_choose_directory_cli_keyboard_interrupt(tmp_path: Path) -> None:
    """KeyboardInterrupt triggers graceful exit."""
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        with pytest.raises(SystemExit) as exc_info:
            choose_directory_cli(tmp_path)
        assert exc_info.value.code == 0
