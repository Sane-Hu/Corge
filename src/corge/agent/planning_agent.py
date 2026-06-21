"""Planning agent — handles PlanState reiterations."""

from corge.contracts import (
    ProceduralStep,
    ProviderMessage,
    ProviderPort,
    Specification,
    TechnicalPlan,
)


class PlanningAgent:
    """Translates specifications into Technical and Procedural plans."""
    
    def __init__(self, provider: ProviderPort) -> None:
        self.provider = provider

    def generate_technical_plan(self, specification: Specification) -> TechnicalPlan:
        prompt = (
            "You are a technical planner.\n"
            "Create an architectural blueprint for the following specification.\n"
            "Focus STRICTLY on system architecture, database schema changes, "
            "and API contracts. Do NOT provide procedural steps or bash scripts here.\n"
            f"Title: {specification.title}\n"
            f"Body: {specification.body}"
        )
        msg = ProviderMessage(role="user", content=prompt)
        response = self.provider.chat((msg,))
        return TechnicalPlan(
            content=response.content, specification_ref=specification.title
        )

    def generate_procedural_steps(
        self, technical_plan: TechnicalPlan
    ) -> tuple[ProceduralStep, ...]:
        prompt = (
            "You are an execution planner.\n"
            "Break down the following technical plan into strict procedural steps.\n"
            "Each step must be an actionable, sequential chunk of work. "
            "Output each step on a new line starting with STEP: \n\n"
            f"Plan:\n{technical_plan.content}"
        )
        msg = ProviderMessage(role="user", content=prompt)
        response = self.provider.chat((msg,))
        
        steps = []
        step_count = 0
        for line in response.content.split("\n"):
            if line.strip().startswith("STEP:"):
                step_count += 1
                steps.append(ProceduralStep(
                    identifier=f"step-{step_count}",
                    description=line.replace("STEP:", "").strip()
                ))
        
        if not steps:
            steps.append(
                ProceduralStep(
                    identifier="step-1", description="Execute technical plan"
                )
            )
            
        return tuple(steps)
