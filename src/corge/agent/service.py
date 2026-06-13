"""Planning and execution orchestration boundaries."""

from corge.contracts import ContextBundle, MemoryEvent, Plan, PlanStep, Specification


class AgentService:
    """Agent responsibilities from docs/04-module-contracts.md."""

    def generate_plan(self, specification: Specification) -> Plan:
        raise NotImplementedError

    def execute_step(self, step: PlanStep, context: ContextBundle) -> None:
        raise NotImplementedError

    def evaluate_completion(self, plan: Plan, context: ContextBundle) -> bool:
        raise NotImplementedError

    def update_memory(self, event: MemoryEvent) -> None:
        raise NotImplementedError

