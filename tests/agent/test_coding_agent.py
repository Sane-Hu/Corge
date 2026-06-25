"""Tests for CodingAgent behavior."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from corge.agent.coding_agent import CodingAgent, ToolExecutionError
from corge.contracts import (
    ApprovalDecision,
    ContextBundle,
    Plan,
    PlanStep,
    ToolAction,
    ToolResult,
)


@pytest.fixture
def provider():
    return MagicMock()


@pytest.fixture
def tool_runtime():
    return MagicMock()


@pytest.fixture
def approval_gateway():
    gw = MagicMock()
    gw.approve.return_value = ApprovalDecision.APPROVED
    return gw


@pytest.fixture
def context_service():
    return MagicMock()


@pytest.fixture
def knowledge_graph():
    return MagicMock()


@pytest.fixture
def prompt_assembler():
    pa = MagicMock()
    pa.assemble_coding_prompt.return_value = "Mocked coding prompt"
    return pa


@pytest.fixture
def coding_agent(
    provider, tool_runtime, approval_gateway, context_service, knowledge_graph, prompt_assembler
):
    return CodingAgent(
        provider=provider,
        tool_runtime=tool_runtime,
        approval_gateway=approval_gateway,
        context_service=context_service,
        knowledge_graph=knowledge_graph,
        prompt_assembler=prompt_assembler,
    )


def test_dispatch_write_uses_content(coding_agent, provider, tool_runtime, tmp_path):
    # Mock LLM to return WRITE action with content
    mock_response = MagicMock()
    mock_response.content = (
        "```json\n"
        + json.dumps(
            {
                "done": True,
                "actions": [
                    {
                        "action": "WRITE",
                        "target": str(tmp_path / "test.txt"),
                        "content": "hello world",
                    }
                ],
            }
        )
        + "\n```"
    )
    provider.chat.return_value = mock_response

    # Mock tool runtime
    tool_runtime.write.return_value = ToolResult(
        action=ToolAction.WRITE, output="ok", success=True
    )

    step = PlanStep(identifier="step-1", description="Write a file")
    bundle = ContextBundle(
        specification=MagicMock(),
        plan=Plan(()),
        repository_context=MagicMock(),
        engineering_profile=MagicMock(),
    )

    coding_agent.execute_step(step, bundle)

    tool_runtime.write.assert_called_once_with(
        Path(str(tmp_path / "test.txt")), "hello world"
    )


def test_dispatch_edit_extracts_old_new(coding_agent, provider, tool_runtime, tmp_path):
    mock_response = MagicMock()
    mock_response.content = (
        "```json\n"
        + json.dumps(
            {
                "done": True,
                "actions": [
                    {
                        "action": "EDIT",
                        "target": str(tmp_path / "test.txt"),
                        "old": "old line",
                        "new": "new line",
                    }
                ],
            }
        )
        + "\n```"
    )
    provider.chat.return_value = mock_response

    tool_runtime.edit.return_value = ToolResult(
        action=ToolAction.EDIT, output="ok", success=True
    )

    step = PlanStep(identifier="step-1", description="Edit a file")
    bundle = ContextBundle(
        specification=MagicMock(),
        plan=Plan(()),
        repository_context=MagicMock(),
        engineering_profile=MagicMock(),
    )

    coding_agent.execute_step(step, bundle)

    tool_runtime.edit.assert_called_once_with(
        Path(str(tmp_path / "test.txt")), "old line", "new line"
    )


def test_execute_step_loops_until_done(coding_agent, provider, tool_runtime, tmp_path):
    # First response: WRITE, done=False
    resp1 = MagicMock()
    resp1.content = (
        "```json\n"
        + json.dumps(
            {
                "done": False,
                "actions": [
                    {
                        "action": "WRITE",
                        "target": str(tmp_path / "file1.txt"),
                        "content": "f1",
                    }
                ],
            }
        )
        + "\n```"
    )

    # Second response: WRITE, done=True
    resp2 = MagicMock()
    resp2.content = (
        "```json\n"
        + json.dumps(
            {
                "done": True,
                "actions": [
                    {
                        "action": "WRITE",
                        "target": str(tmp_path / "file2.txt"),
                        "content": "f2",
                    }
                ],
            }
        )
        + "\n```"
    )

    provider.chat.side_effect = [resp1, resp2]
    tool_runtime.write.return_value = ToolResult(
        action=ToolAction.WRITE, output="ok", success=True
    )

    step = PlanStep(identifier="step-1", description="Multiple actions")
    bundle = ContextBundle(
        specification=MagicMock(),
        plan=Plan(()),
        repository_context=MagicMock(),
        engineering_profile=MagicMock(),
    )

    coding_agent.execute_step(step, bundle)

    assert tool_runtime.write.call_count == 2
    assert provider.chat.call_count == 2


def test_execute_step_max_actions_exceeded(
    coding_agent, provider, tool_runtime, tmp_path
):
    resp1 = MagicMock()
    resp1.content = (
        "```json\n"
        + json.dumps(
            {
                "done": False,
                "actions": [
                    {
                        "action": "WRITE",
                        "target": str(tmp_path / "file.txt"),
                        "content": "content",
                    }
                ],
            }
        )
        + "\n```"
    )

    provider.chat.return_value = resp1
    tool_runtime.write.return_value = ToolResult(
        action=ToolAction.WRITE, output="ok", success=True
    )

    step = PlanStep(identifier="step-1", description="Infinite loop")
    bundle = ContextBundle(
        specification=MagicMock(),
        plan=Plan(()),
        repository_context=MagicMock(),
        engineering_profile=MagicMock(),
    )

    with pytest.raises(ToolExecutionError, match="Exceeded max actions per step"):
        coding_agent.execute_step(step, bundle)

    assert provider.chat.call_count == 20


def test_read_deduplication_skips_second_read(
    coding_agent, provider, tool_runtime, tmp_path
):
    resp1 = MagicMock()
    resp1.content = (
        "```json\n"
        + json.dumps(
            {
                "done": False,
                "actions": [
                    {
                        "action": "READ",
                        "target": str(tmp_path / "file.txt"),
                    },
                    {
                        "action": "READ",
                        "target": str(tmp_path / "file.txt"),
                    },
                ],
            }
        )
        + "\n```"
    )

    resp2 = MagicMock()
    resp2.content = "```json\n" + json.dumps({"done": True, "actions": []}) + "\n```"

    provider.chat.side_effect = [resp1, resp2]
    tool_runtime.read.return_value = ToolResult(
        action=ToolAction.READ, output="ok", success=True
    )

    step = PlanStep(identifier="step-1", description="Duplicate reads")
    bundle = ContextBundle(
        specification=MagicMock(),
        plan=Plan(()),
        repository_context=MagicMock(),
        engineering_profile=MagicMock(),
    )

    coding_agent.execute_step(step, bundle)

    # ToolRuntime should only be called once for the first READ
    assert tool_runtime.read.call_count == 1
    coding_agent._context_service.update_markov_state.assert_called()


def test_execute_step_raises_on_rejection(
    coding_agent, provider, tool_runtime, tmp_path, approval_gateway
):
    from corge.agent.coding_agent import ToolExecutionError
    from corge.contracts import ChatResponse

    provider.chat.return_value = ChatResponse(
        content="""```json
{
  "actions": [
    {
      "action": "BASH",
      "target": "rm -rf /"
    }
  ]
}
```""",
        usage={},
    )
    from corge.contracts import ApprovalDecision

    approval_gateway.approve.return_value = ApprovalDecision.REJECTED

    from corge.contracts import PlanStep

    step = PlanStep(identifier="1", description="test")

    import pytest

    with pytest.raises(ToolExecutionError) as exc:
        coding_agent.execute_step(step, MagicMock())
    assert "rejected" in str(exc.value).lower()


def test_evaluate_completion_returns_true_on_satisfied_criteria(coding_agent, provider):
    from corge.contracts import (
        AcceptanceCriteria,
        ChatResponse,
        PlanStep,
        Specification,
    )

    provider.chat.return_value = ChatResponse(
        content="""```json\n{"all_satisfied": true}\n```""", usage={}
    )
    step = PlanStep(identifier="1", description="test")
    spec = Specification(
        title="t", body="b", acceptance_criteria=AcceptanceCriteria(("C1",))
    )
    bundle = ContextBundle(
        specification=spec,
        plan=Plan(()),
        repository_context=MagicMock(),
        engineering_profile=MagicMock(),
    )
    res = coding_agent.evaluate_completion(step, bundle)
    assert res is True


def test_evaluate_completion_returns_false_on_malformed_json(coding_agent, provider):
    from corge.contracts import (
        AcceptanceCriteria,
        ChatResponse,
        PlanStep,
        Specification,
    )

    provider.chat.return_value = ChatResponse(content="Not JSON", usage={})
    step = PlanStep(identifier="1", description="test")
    spec = Specification(
        title="t", body="b", acceptance_criteria=AcceptanceCriteria(("C1",))
    )
    bundle = ContextBundle(
        specification=spec,
        plan=Plan(()),
        repository_context=MagicMock(),
        engineering_profile=MagicMock(),
    )
    res = coding_agent.evaluate_completion(step, bundle)
    assert res is False
