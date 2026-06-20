"""Session controller — orchestrates agent transitions."""

from corge.agent.coding_agent import CodingAgent
from corge.agent.planning_agent import PlanningAgent
from corge.agent.specification_agent import SpecificationAgent
from corge.contracts import (
    ApprovalGatewayPort,
    ContextBundle,
    ContextPort,
    MemoryEvent,
    Plan,
    PlanStep,
    ProceduralStep,
    ProviderPort,
    SemanticGap,
    Specification,
    TechnicalPlan,
    ToolRuntimePort,
)


class SessionController:
    """Coordinates master phases: Specification, Planning, and Coding."""
    
    def __init__(
        self,
        provider: ProviderPort,
        tool_runtime: ToolRuntimePort,
        approval_gateway: ApprovalGatewayPort,
        context_service: ContextPort,
    ) -> None:
        self.spec_agent = SpecificationAgent(provider)
        self.plan_agent = PlanningAgent(provider)
        self.code_agent = CodingAgent(provider, tool_runtime, approval_gateway, context_service)

    def analyze_specification_gaps(self, canvas_text: str) -> tuple[SemanticGap, ...]:
        return self.spec_agent.analyze_specification_gaps(canvas_text)

    def generate_technical_plan(self, specification: Specification) -> TechnicalPlan:
        return self.plan_agent.generate_technical_plan(specification)

    def generate_procedural_steps(
        self, technical_plan: TechnicalPlan
    ) -> tuple[ProceduralStep, ...]:
        return self.plan_agent.generate_procedural_steps(technical_plan)

    def execute_step(self, step: PlanStep, context: ContextBundle) -> None:
        self.code_agent.execute_step(step, context)

    def evaluate_completion(self, plan: Plan, context: ContextBundle) -> bool:
        return self.code_agent.evaluate_completion(plan, context)

    def update_memory(self, event: MemoryEvent) -> None:
        pass
