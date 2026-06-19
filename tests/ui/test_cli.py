"""Tests for the CLI UI."""

from unittest.mock import patch

from corge.contracts import Plan, PlanStep
from corge.ui.cli import CliUi


def test_cli_ui_show_plan_renders_without_crashing() -> None:
    """One runnable check to ensure the UI can render basic objects."""
    ui = CliUi()
    plan = Plan(steps=(PlanStep(identifier="test", description="Test step"),))
    
    with patch("rich.console.Console.print") as mock_print:
        ui.show_plan(plan)
        
    assert mock_print.called
