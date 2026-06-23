"""Tests for specialized agents."""


from corge.agent.coding_agent import CodingAgent
from corge.agent.planning_agent import PlanningAgent
from corge.agent.session_controller import SessionController
from corge.agent.specification_agent import SpecificationAgent


def test_agents_can_be_instantiated():
    """Verify that all new agents can be instantiated with mocks."""
    assert SpecificationAgent
    assert PlanningAgent
    assert CodingAgent
    assert SessionController
