from unittest.mock import Mock

from corge.agent.specification_agent import SpecificationAgent
from corge.contracts import ChatResponse, ContextPort, PromptAssemblerPort, ProviderPort


def test_draft_specification_parses_json():
    mock_provider = Mock(spec=ProviderPort)
    mock_provider.chat.return_value = ChatResponse(
        content="""```json
{
  "title": "Test Title",
  "body": "Test Body",
  "acceptance_criteria": ["1", "2"],
  "constraints": "Test constraints",
  "testing_expectations": "Test expectations"
}
```""",
        usage={},
    )
    mock_ctx = Mock(spec=ContextPort)
    mock_pa = Mock(spec=PromptAssemblerPort)
    agent = SpecificationAgent(mock_provider, mock_ctx, mock_pa)
    spec = agent.concretize("canvas")
    assert spec.title == "Test Title"
    assert spec.body == "Test Body"
    assert len(spec.acceptance_criteria.items) == 2
    assert spec.constraints == "Test constraints"
    assert spec.testing_expectations == "Test expectations"


def test_draft_specification_fallback():
    mock_provider = Mock(spec=ProviderPort)
    mock_provider.chat.return_value = ChatResponse(content="No JSON here", usage={})
    mock_ctx = Mock(spec=ContextPort)
    mock_pa = Mock(spec=PromptAssemblerPort)
    agent = SpecificationAgent(mock_provider, mock_ctx, mock_pa)
    spec = agent.concretize("canvas text")
    assert spec.title == "Untitled Feature"
    assert spec.body == "canvas text"
    assert len(spec.acceptance_criteria.items) == 0


def test_analyze_specification_gaps_parses_json():
    mock_provider = Mock(spec=ProviderPort)
    mock_provider.chat.return_value = ChatResponse(
        content="""```json
  [
    {
      "topic": "Missing auth logic"
    }
  ]
```""",
        usage={},
    )
    mock_ctx = Mock(spec=ContextPort)
    mock_pa = Mock(spec=PromptAssemblerPort)
    agent = SpecificationAgent(mock_provider, mock_ctx, mock_pa)
    gaps = agent.analyze_specification_gaps("canvas")
    assert len(gaps) == 1
    assert gaps[0].topic == "Missing auth logic"


def test_analyze_specification_gaps_fallback():
    mock_provider = Mock(spec=ProviderPort)
    mock_provider.chat.return_value = ChatResponse(content="No JSON here", usage={})
    mock_ctx = Mock(spec=ContextPort)
    mock_pa = Mock(spec=PromptAssemblerPort)
    agent = SpecificationAgent(mock_provider, mock_ctx, mock_pa)
    gaps = agent.analyze_specification_gaps("canvas")
    assert gaps == ()


def test_socratic_loop_records_real_answer():
    from corge.contracts import ArgumentationLogPort, UiPort

    mock_provider = Mock(spec=ProviderPort)
    mock_provider.chat.side_effect = [
        ChatResponse(content='{"title": "Title"}', usage={}),
        ChatResponse(content='[{"topic": "Auth"}]', usage={}),
        ChatResponse(content="Question 1?", usage={}),
        ChatResponse(content='{"title": "Title", "body": "Body"}', usage={}),
        ChatResponse(content='[]', usage={}),
    ]

    mock_ui = Mock(spec=UiPort)
    mock_ui.show_confirm.return_value = True
    mock_ui.show_question.return_value = "My answer"

    mock_arg_log = Mock(spec=ArgumentationLogPort)

    mock_ctx = Mock(spec=ContextPort)
    mock_pa = Mock(spec=PromptAssemblerPort)
    agent = SpecificationAgent(mock_provider, mock_ctx, mock_pa)
    agent.run_socratic_loop("canvas", mock_arg_log, mock_ui)

    mock_arg_log.record_entry.assert_called_once()
    entry = mock_arg_log.record_entry.call_args[0][0]
    assert entry.answer == "My answer"
    assert entry.question == "Question 1?"


def test_socratic_loop_opt_out():
    from corge.contracts import ArgumentationLogPort, UiPort

    mock_provider = Mock(spec=ProviderPort)
    mock_provider.chat.side_effect = [
        ChatResponse(content='{"title": "Title"}', usage={}),
        ChatResponse(content='[{"topic": "Auth"}]', usage={}),
    ]

    mock_ui = Mock(spec=UiPort)
    mock_ui.show_confirm.return_value = False

    mock_arg_log = Mock(spec=ArgumentationLogPort)
    mock_ctx = Mock(spec=ContextPort)
    mock_pa = Mock(spec=PromptAssemblerPort)

    agent = SpecificationAgent(mock_provider, mock_ctx, mock_pa)
    spec, gaps = agent.run_socratic_loop("canvas", mock_arg_log, mock_ui)

    assert spec.title == "Title"
    assert len(gaps) == 1
    assert gaps[0].topic == "Auth"
    mock_ui.show_confirm.assert_called_once()
    mock_ui.show_question.assert_not_called()
    mock_arg_log.record_entry.assert_called_once()
    entry = mock_arg_log.record_entry.call_args[0][0]
    assert entry.was_user_override is True
    assert entry.answer == "Skipped/Opted out"


def test_socratic_loop_skipped_questions():
    from corge.contracts import ArgumentationLogPort, UiPort

    mock_provider = Mock(spec=ProviderPort)
    mock_provider.chat.side_effect = [
        ChatResponse(content='{"title": "Title"}', usage={}),
        ChatResponse(content='[{"topic": "Auth"}]', usage={}),
        ChatResponse(content="Question 1?", usage={}),
    ]

    mock_ui = Mock(spec=UiPort)
    mock_ui.show_confirm.return_value = True
    mock_ui.show_question.return_value = ""

    mock_arg_log = Mock(spec=ArgumentationLogPort)
    mock_ctx = Mock(spec=ContextPort)
    mock_pa = Mock(spec=PromptAssemblerPort)

    agent = SpecificationAgent(mock_provider, mock_ctx, mock_pa)
    spec, gaps = agent.run_socratic_loop("canvas", mock_arg_log, mock_ui)

    mock_arg_log.record_entry.assert_called_once()
    entry = mock_arg_log.record_entry.call_args[0][0]
    assert entry.was_user_override is True
    assert entry.answer == ""
    assert entry.question == "Question 1?"


def test_socratic_loop_cap():
    from corge.contracts import ArgumentationLogPort, UiPort

    mock_provider = Mock(spec=ProviderPort)
    mock_provider.chat.side_effect = [
        ChatResponse(content='{"title": "Title"}', usage={}),
        ChatResponse(content='[{"topic": "Gap1"}, {"topic": "Gap2"}, {"topic": "Gap3"}]', usage={}),
        ChatResponse(content="Questions?", usage={}),
        ChatResponse(content='{"title": "Title", "body": "Refined spec"}', usage={}),
        ChatResponse(content='[]', usage={}),
    ]

    mock_ui = Mock(spec=UiPort)
    mock_ui.show_confirm.return_value = True
    mock_ui.show_question.return_value = "Answers"

    mock_arg_log = Mock(spec=ArgumentationLogPort)
    mock_ctx = Mock(spec=ContextPort)
    mock_pa = Mock(spec=PromptAssemblerPort)
    mock_pa.assemble_spec_prompt.side_effect = lambda ctx, inst: inst

    agent = SpecificationAgent(mock_provider, mock_ctx, mock_pa)
    spec, gaps = agent.run_socratic_loop("canvas", mock_arg_log, mock_ui, max_questions=2)

    # Verify that only the first 2 gaps were formulated/asked
    args = mock_provider.chat.call_args_list[2][0][0]
    prompt_content = args[0].content
    assert "Gap1" in prompt_content
    assert "Gap2" in prompt_content
    assert "Gap3" not in prompt_content


def test_format_spec_to_text():
    from corge.contracts import AcceptanceCriteria, SemanticGap, Specification

    mock_provider = Mock(spec=ProviderPort)
    mock_ctx = Mock(spec=ContextPort)
    mock_pa = Mock(spec=PromptAssemblerPort)
    agent = SpecificationAgent(mock_provider, mock_ctx, mock_pa)

    spec = Specification(
        title="Title",
        body="Body Text",
        acceptance_criteria=AcceptanceCriteria(items=("Crit A",)),
        constraints="Constraint Text",
        testing_expectations="Testing Expect Text"
    )
    gaps = (SemanticGap(topic="Gap X"),)

    text = agent.format_spec_to_text(spec, gaps)
    assert "# Title: Title" in text
    assert "# Requirements & User Stories\nBody Text" in text
    assert "# Constraints\nConstraint Text" in text
    assert "# Testing Expectations\nTesting Expect Text" in text
    assert "# Acceptance Criteria\n- Crit A" in text
    assert "=== UNRESOLVED SEMANTIC GAPS ===" in text
    assert "[GAP: Gap X]" in text


def test_merge_templated_responses():
    from corge.contracts import AcceptanceCriteria, Specification

    mock_provider = Mock(spec=ProviderPort)
    mock_provider.chat.return_value = ChatResponse(
        content="""{
          "title": "Merged Title",
          "body": "Merged Body\\n=== UNRESOLVED SEMANTIC GAPS ===\\nPlease resolve the following gaps by editing the text below:\\n\\n[GAP: output string mismatch]\\nResolution: <Enter details here>",
          "acceptance_criteria": ["Merged Crit"],
          "constraints": "Merged Constraint",
          "testing_expectations": "Merged Test"
        }""",
        usage={}
    )
    mock_ctx = Mock(spec=ContextPort)
    mock_pa = Mock(spec=PromptAssemblerPort)
    agent = SpecificationAgent(mock_provider, mock_ctx, mock_pa)

    spec = Specification(title="Orig", body="Orig body", acceptance_criteria=AcceptanceCriteria(items=()))
    updated = agent.merge_templated_responses(spec, "Some edited text")
    assert updated.title == "Merged Title"
    assert updated.body == "Merged Body"
    assert updated.constraints == "Merged Constraint"
    assert updated.testing_expectations == "Merged Test"
    assert updated.acceptance_criteria.items == ("Merged Crit",)

