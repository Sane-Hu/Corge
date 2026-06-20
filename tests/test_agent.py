"""Unit tests for the agent module."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from corge.agent import AgentService, ToolExecutionError
from corge.contracts import (
    AcceptanceCriteria,
    ApprovalDecision,
    ContextBundle,
    EngineeringProfile,
    MemoryEvent,
    Plan,
    PlanStep,
    RepositoryContext,
    Specification,
    ToolAction,
    ToolResult,
)


@pytest.fixture()
def mock_provider() -> Mock:
    return Mock()


@pytest.fixture()
def mock_prompt_assembler() -> Mock:
    return Mock()


@pytest.fixture()
def mock_tool_runtime() -> Mock:
    return Mock()


@pytest.fixture()
def mock_approval_gateway() -> Mock:
    return Mock()


@pytest.fixture()
def mock_memory_store() -> Mock:
    return Mock()


@pytest.fixture()
def agent_service(
    mock_provider: Mock,
    mock_prompt_assembler: Mock,
    mock_tool_runtime: Mock,
    mock_approval_gateway: Mock,
    mock_memory_store: Mock,
) -> AgentService:
    return AgentService(
        provider=mock_provider,
        prompt_assembler=mock_prompt_assembler,
        tool_runtime=mock_tool_runtime,
        approval_gateway=mock_approval_gateway,
        memory_store=mock_memory_store,
    )


def test_generate_plan_parses_json_steps(
    agent_service: AgentService, mock_provider: Mock
) -> None:
    spec = Specification(
        title="Test Feature",
        body="Does a thing.",
        acceptance_criteria=AcceptanceCriteria(items=("Works",)),
    )
    mock_response = Mock()
    mock_response.content = (
        '```json\n{"steps": [{"identifier": "1", "description": "do it"}]}\n```'
    )
    mock_provider.chat.return_value = mock_response

    plan = agent_service.generate_plan(spec)

    assert plan.specification_ref == "Test Feature"
    assert len(plan.steps) == 1
    assert plan.steps[0].identifier == "1"
    assert plan.steps[0].description == "do it"


def test_execute_step_requires_approval_and_executes_write(
    agent_service: AgentService,
    mock_provider: Mock,
    mock_prompt_assembler: Mock,
    mock_tool_runtime: Mock,
    mock_approval_gateway: Mock,
) -> None:
    step = PlanStep(identifier="s1", description="Write file")
    context = ContextBundle(
        specification=Specification(
            title="", body="", acceptance_criteria=AcceptanceCriteria(items=())
        ),
        plan=Plan(steps=()),
        repository_context=RepositoryContext(root=Path("/repo")),
        engineering_profile=EngineeringProfile(),
    )
    
    mock_prompt_assembler.assemble_prompt.return_value = "prompt"
    
    mock_response = Mock()
    mock_response.content = (
        '{"action": "write", "target": "test.txt", "content": "hello"}'
    )
    mock_provider.chat.return_value = mock_response

    mock_approval_gateway.approve.return_value = ApprovalDecision.APPROVED
    mock_tool_runtime.write.return_value = ToolResult(
        action=ToolAction.WRITE, output="ok", success=True
    )

    agent_service.execute_step(step, context)

    # Asserts
    mock_approval_gateway.approve.assert_called_once()
    mock_tool_runtime.write.assert_called_once_with(Path("test.txt"), "hello")


def test_execute_step_raises_on_rejection(
    agent_service: AgentService,
    mock_provider: Mock,
    mock_prompt_assembler: Mock,
    mock_approval_gateway: Mock,
) -> None:
    step = PlanStep(identifier="s1", description="Write file")
    context = ContextBundle(
        specification=Specification(
            title="", body="", acceptance_criteria=AcceptanceCriteria(items=())
        ),
        plan=Plan(steps=()),
        repository_context=RepositoryContext(root=Path("/repo")),
        engineering_profile=EngineeringProfile(),
    )
    
    mock_prompt_assembler.assemble_prompt.return_value = "prompt"
    
    mock_response = Mock()
    mock_response.content = (
        '{"action": "write", "target": "test.txt", "content": "hello"}'
    )
    mock_provider.chat.return_value = mock_response

    mock_approval_gateway.approve.return_value = ApprovalDecision.REJECTED

    with pytest.raises(ToolExecutionError, match="rejected by human approval"):
        agent_service.execute_step(step, context)


def test_execute_step_raises_on_tool_failure(
    agent_service: AgentService,
    mock_provider: Mock,
    mock_prompt_assembler: Mock,
    mock_tool_runtime: Mock,
) -> None:
    step = PlanStep(identifier="s1", description="Read file")
    context = ContextBundle(
        specification=Specification(
            title="", body="", acceptance_criteria=AcceptanceCriteria(items=())
        ),
        plan=Plan(steps=()),
        repository_context=RepositoryContext(root=Path("/repo")),
        engineering_profile=EngineeringProfile(),
    )
    
    mock_prompt_assembler.assemble_prompt.return_value = "prompt"
    
    mock_response = Mock()
    mock_response.content = '{"action": "read", "target": "test.txt"}'
    mock_provider.chat.return_value = mock_response

    # READ does not require approval
    mock_tool_runtime.read.return_value = ToolResult(
        action=ToolAction.READ, output="", success=False, stderr="not found"
    )

    with pytest.raises(ToolExecutionError, match="not found"):
        agent_service.execute_step(step, context)


def test_evaluate_completion(
    agent_service: AgentService, mock_provider: Mock
) -> None:
    plan = Plan(steps=(), specification_ref="Test")
    context = ContextBundle(
        specification=Specification(
            title="", body="", acceptance_criteria=AcceptanceCriteria(items=())
        ),
        plan=plan,
        repository_context=RepositoryContext(root=Path("/repo")),
        engineering_profile=EngineeringProfile(),
    )

    mock_response = Mock()
    mock_response.content = '{"completed": true}'
    mock_provider.chat.return_value = mock_response

    result = agent_service.evaluate_completion(plan, context)
    assert result is True


def test_update_memory(
    agent_service: AgentService, mock_memory_store: Mock
) -> None:
    event = MemoryEvent(kind="test")
    agent_service.update_memory(event)
    mock_memory_store.store_event.assert_called_once_with(event)
