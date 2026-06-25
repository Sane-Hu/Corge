from unittest.mock import Mock

from corge.agent.specification_agent import SpecificationAgent
from corge.contracts import ChatResponse, ProviderPort, ContextPort, PromptAssemblerPort


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

