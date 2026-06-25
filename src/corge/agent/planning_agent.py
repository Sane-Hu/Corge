"""Planning agent — handles PlanState reiterations."""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from corge.contracts import (
    ContextPort,
    ProceduralStep,
    PromptAssemblerPort,
    ProviderMessage,
    ProviderPort,
    RepositoryContext,
    Specification,
    TechnicalPlan,
)


class PlanningAgent:
    """Translates specifications into Technical and Procedural plans."""

    def __init__(
        self,
        provider: ProviderPort,
        context_service: ContextPort,
        prompt_assembler: PromptAssemblerPort,
    ) -> None:
        self._provider = provider
        self._context_service = context_service
        self._prompt_assembler = prompt_assembler

    def generate_technical_plan(
        self,
        specification: Specification,
        on_token: Callable[[str], None] | None = None,
    ) -> TechnicalPlan:
        instruction = (
            "Create an architectural blueprint for the specification provided in the context.\n"
            "Focus STRICTLY on system architecture, database schema changes, "
            "and API contracts. Ensure you respect the engineering profile and repository facts.\n"
            "Do NOT provide procedural steps or bash scripts here."
        )

        ctx_bundle = self._context_service.refresh_context(
            RepositoryContext(root=Path("."))
        )
        ctx_bundle = replace(ctx_bundle, specification=specification)
        prompt = self._prompt_assembler.assemble_plan_prompt(ctx_bundle, instruction)
        msg = ProviderMessage(role="user", content=prompt)
        response = self._provider.chat((msg,), on_token=on_token)
        return TechnicalPlan(
            content=response.content, specification_ref=specification.title
        )

    def generate_procedural_steps(
        self,
        technical_plan: TechnicalPlan,
        on_token: Callable[[str], None] | None = None,
    ) -> tuple[ProceduralStep, ...]:
        instruction = (
            "Break down the technical plan below into strict procedural steps.\n"
            "Each step must be an actionable, sequential chunk of work aligned with repository facts.\n"
            "Output each step on a new line starting with STEP: \n\n"
            f"Plan:\n{technical_plan.content}"
        )

        ctx_bundle = self._context_service.refresh_context(
            RepositoryContext(root=Path("."))
        )
        prompt = self._prompt_assembler.assemble_plan_prompt(ctx_bundle, instruction)
        msg = ProviderMessage(role="user", content=prompt)
        response = self._provider.chat((msg,), on_token=on_token)

        steps = []
        step_count = 0
        for line in response.content.split("\n"):
            if line.strip().startswith("STEP:"):
                step_count += 1
                steps.append(
                    ProceduralStep(
                        identifier=f"step-{step_count}",
                        description=line.replace("STEP:", "").strip(),
                    )
                )

        if not steps:
            steps.append(
                ProceduralStep(
                    identifier="step-1", description="Execute technical plan"
                )
            )

        return tuple(steps)
