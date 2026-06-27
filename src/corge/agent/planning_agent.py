from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from corge.contracts import (
    ContextPort,
    MasterPhase,
    PlanState,
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
        controller: Any = None,
    ) -> None:
        self._provider = provider
        self._context_service = context_service
        self._prompt_assembler = prompt_assembler
        self._controller = controller

    def generate_technical_plan(
        self,
        specification: Specification,
        on_token: Callable[[str], None] | None = None,
    ) -> TechnicalPlan:
        if self._controller:
            if self._controller.phase != MasterPhase.PLANNING:
                raise ValueError("PlanningAgent operations are only allowed in PLANNING phase.")
            self._controller.advance_plan_state(PlanState.TECH_PLAN_REITERATION)

        instruction = (
            "Create an architectural blueprint for the specification provided in the context.\n"
            "Focus STRICTLY on system architecture, database schema changes, "
            "and API contracts. Ensure you respect the engineering profile and repository facts.\n"
            "Analyze <relevant_files> to ensure your design integrates properly without duplicating existing modules.\n"
            "Do NOT provide procedural steps or bash scripts here.\n\n"
            "Design Rules for Cost & Time Efficiency:\n"
            "1. YAGNI: Design the simplest, most direct architecture that satisfies requirements. Avoid speculative abstractions.\n"
            "2. Locality: Keep changes localized to the fewest files possible to minimize execution complexity and edit iterations.\n"
            "3. Reuse: Reuse existing utilities, dependencies, and code patterns instead of introducing new ones."
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
        if self._controller:
            if self._controller.phase != MasterPhase.PLANNING:
                raise ValueError("PlanningAgent operations are only allowed in PLANNING phase.")
            self._controller.advance_plan_state(PlanState.STEPS_REITERATION)

        instruction = (
            "Break down the technical plan below into strict procedural steps.\n"
            "Each step must be an actionable, sequential chunk of work aligned with repository facts.\n"
            "Reference specific paths from <relevant_files> when proposing modifications.\n"
            "Output each step on a new line starting with STEP: \n\n"
            "Planning Rules for Cost & Time Efficiency:\n"
            "1. Grouping: Group related file changes into a single logical step to minimize agent transition overhead.\n"
            "2. Linearity: Order steps logically to avoid reading or editing the same file multiple times across different steps.\n"
            "3. Conciseness: Keep the total number of steps minimal (aim for 3-7 steps). Fewer steps mean faster execution.\n\n"
            f"Plan:\n{technical_plan.content}"
        )

        ctx_bundle = self._context_service.refresh_context(
            RepositoryContext(root=Path(".")), technical_plan
        )
        if self._controller and self._controller.specification:
            ctx_bundle = replace(ctx_bundle, specification=self._controller.specification)
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
