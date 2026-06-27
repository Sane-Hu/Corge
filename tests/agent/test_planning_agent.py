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


def test_draft_procedural_steps_injects_specification():
    mock_provider = Mock(spec=ProviderPort)
    mock_provider.chat.return_value = ChatResponse(content="STEP: Test", usage={})
    mock_ctx = Mock(spec=ContextPort)
    
    dummy_bundle = _mock_context()
    mock_ctx.refresh_context.return_value = dummy_bundle
    
    mock_pa = Mock(spec=PromptAssemblerPort)
    from corge.contracts import MasterPhase
    mock_controller = Mock()
    mock_controller.phase = MasterPhase.PLANNING
    mock_controller.specification = dummy_bundle.specification
    
    agent = PlanningAgent(mock_provider, mock_ctx, mock_pa, controller=mock_controller)
    agent.generate_procedural_steps(_mock_technical_plan())
    
    # Verify mock_ctx.refresh_context was called
    mock_ctx.refresh_context.assert_called_once()
    # And mock_pa.assemble_plan_prompt was called with context containing specification
    mock_pa.assemble_plan_prompt.assert_called_once()
    context_passed = mock_pa.assemble_plan_prompt.call_args[0][0]
    assert context_passed.specification == dummy_bundle.specification
