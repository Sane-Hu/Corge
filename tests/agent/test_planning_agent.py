from unittest.mock import Mock

from corge.agent.planning_agent import PlanningAgent
from corge.contracts import (
    AcceptanceCriteria,
    ChatResponse,
    ContextBundle,
    ContextPort,
    Plan,
    PromptAssemblerPort,
    ProviderPort,
    Specification,
    TechnicalPlan,
)


def _mock_context() -> ContextBundle:
    return ContextBundle(
        specification=Specification(
            title="T",
            body="B",
            acceptance_criteria=AcceptanceCriteria(items=()),
        ),
        plan=Plan(steps=(), specification_ref="T"),
        repository_context=None,
        engineering_profile=None,
        scenario_memory=(),
        engineering_facts=(),
        recent_actions=(),
    )


def _mock_technical_plan() -> TechnicalPlan:
    return TechnicalPlan(content="Test plan", specification_ref="T")


def test_draft_technical_plan_parses_json():
    mock_provider = Mock(spec=ProviderPort)
    mock_provider.chat.return_value = ChatResponse(content="Test content", usage={})
    mock_ctx = Mock(spec=ContextPort)
    mock_ctx.refresh_context.return_value = _mock_context()
    mock_pa = Mock(spec=PromptAssemblerPort)
    agent = PlanningAgent(mock_provider, mock_ctx, mock_pa)
    plan = agent.generate_technical_plan(_mock_context().specification)
    assert plan.content == "Test content"
    assert plan.specification_ref == "T"


def test_draft_technical_plan_fallback():
    mock_provider = Mock(spec=ProviderPort)
    mock_provider.chat.return_value = ChatResponse(content="No JSON here", usage={})
    mock_ctx = Mock(spec=ContextPort)
    mock_ctx.refresh_context.return_value = _mock_context()
    mock_pa = Mock(spec=PromptAssemblerPort)
    agent = PlanningAgent(mock_provider, mock_ctx, mock_pa)
    plan = agent.generate_technical_plan(_mock_context().specification)
    assert plan.content == "No JSON here"
    assert plan.specification_ref == "T"


def test_draft_procedural_steps_parses_json():
    mock_provider = Mock(spec=ProviderPort)
    mock_provider.chat.return_value = ChatResponse(
        content="STEP: Test step 1\nSTEP: Test step 2", usage={}
    )
    mock_ctx = Mock(spec=ContextPort)
    mock_ctx.refresh_context.return_value = _mock_context()
    mock_pa = Mock(spec=PromptAssemblerPort)
    agent = PlanningAgent(mock_provider, mock_ctx, mock_pa)
    steps = agent.generate_procedural_steps(_mock_technical_plan())
    assert len(steps) == 2
    assert steps[0].identifier == "step-1"
    assert steps[0].description == "Test step 1"
    assert steps[1].identifier == "step-2"
    assert steps[1].description == "Test step 2"


def test_draft_procedural_steps_fallback():
    mock_provider = Mock(spec=ProviderPort)
    mock_provider.chat.return_value = ChatResponse(content="No JSON here", usage={})
    mock_ctx = Mock(spec=ContextPort)
    mock_ctx.refresh_context.return_value = _mock_context()
    mock_pa = Mock(spec=PromptAssemblerPort)
    agent = PlanningAgent(mock_provider, mock_ctx, mock_pa)
    steps = agent.generate_procedural_steps(_mock_technical_plan())
    assert len(steps) == 1
    assert steps[0].identifier == "step-1"
    assert steps[0].description == "Execute technical plan"
