"""Session controller — orchestrates agent transitions."""

from corge.contracts import (
    ContextBundle,
    MemoryEvent,
    Plan,
    PlanStep,
    ProceduralStep,
    SemanticGap,
    Specification,
    TechnicalPlan,
)


class SessionController:
    """Coordinates master phases: Specification, Planning, and Coding."""
    
    def __init__(self) -> None:
        raise NotImplementedError

    def analyze_specification_gaps(self, canvas_text: str) -> tuple[SemanticGap, ...]:
        raise NotImplementedError

    def generate_technical_plan(self, specification: Specification) -> TechnicalPlan:
        raise NotImplementedError

    def generate_procedural_steps(
        self, technical_plan: TechnicalPlan
    ) -> tuple[ProceduralStep, ...]:
        raise NotImplementedError

    def execute_step(self, step: PlanStep, context: ContextBundle) -> None:
        raise NotImplementedError

    def evaluate_completion(self, plan: Plan, context: ContextBundle) -> bool:
        raise NotImplementedError

    def update_memory(self, event: MemoryEvent) -> None:
        raise NotImplementedError
