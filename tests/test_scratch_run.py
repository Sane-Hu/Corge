from unittest.mock import MagicMock

from corge.contracts import (
    AcceptanceCriteria,
    ApprovalDecision,
    Specification,
    TechnicalPlan,
)


def test_scratch_orchestration_loop(monkeypatch, tmp_path):
    import scratch_run

    monkeypatch.chdir(tmp_path)

    # Mock the UI so it doesn't block
    mock_ui = MagicMock()
    mock_ui.show_spec_wizard.return_value = Specification(
        "Test Title", "Test Body", AcceptanceCriteria(())
    )
    mock_ui.show_tech_plan_editor.return_value = TechnicalPlan("content", "Test Title")
    mock_ui.show_argumentation_diff.return_value = "Test Body"
    mock_ui.show_procedural_steps_editor.return_value = ()
    mock_ui.request_approval.return_value = ApprovalDecision.APPROVED
    mock_ui.show_question.return_value = "mock answer"

    # Patch the CliUi instantiation to return our mock
    monkeypatch.setattr(scratch_run, "CliUi", lambda *args, **kwargs: mock_ui)

    # Disable threading and app UI loop
    app = scratch_run.ScratchApp()

    # Run the loop synchronously in the main thread bypassing @work
    scratch_run.ScratchApp.run_scratch.__wrapped__(app)
