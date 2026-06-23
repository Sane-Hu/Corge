"""Prompt construction — satisfies ``contracts.PromptAssemblerPort``."""

from __future__ import annotations

from corge.contracts import (
    BudgetManagerPort,
    ContextBundle,
    ContextPort,
    EngineeringProfile,
    PlanStep,
    SchemaTailorPort,
    Specification,
)

# Rules below this confidence are excluded from Tier 1 prompt output.
# Defined in 02-technical-spec.md Section 4 (Engineering Profile).
_ENGINEERING_PROFILE_CONFIDENCE_THRESHOLD = 0.5
_TOKEN_BUDGET = 100_000


class PromptAssembler:
    """Builds the ephemeral execution prompt from a context bundle."""

    def __init__(
        self,
        context_port: ContextPort,
        schema_tailor: SchemaTailorPort,
        budget_manager: BudgetManagerPort,
    ) -> None:
        self._context_port = context_port
        self._schema_tailor = schema_tailor
        self._budget_manager = budget_manager

    def collect_context(
        self, step: PlanStep, specification: Specification
    ) -> ContextBundle:
        """Fetch all required context layers for the current plan step."""
        return self._context_port.retrieve_relevant_context(specification, step)

    def assemble_prompt(self, context: ContextBundle) -> str:
        """Render the structured context bundle into the ephemeral markdown prompt."""
        if self._budget_manager.estimate_tokens(context) > _TOKEN_BUDGET:
            context = self._budget_manager.compact(context)

        sections: list[str] = []

        tier1 = self._render_tier1(context)
        if tier1:
            sections.append(tier1)

        tier2 = self._render_tier2(context)
        if tier2:
            sections.append(tier2)

        tier3 = self._render_tier3(context)
        if tier3:
            sections.append(tier3)

        tier4 = self._render_tier4(context)
        if tier4:
            sections.append(tier4)

        tier5 = self._render_tier5(context)
        if tier5:
            sections.append(tier5)

        return "\n\n".join(sections)

    # -- Tier renderers -----------------------------------------------

    def _render_tier1(self, context: ContextBundle) -> str:
        spec = context.specification
        step = self._current_step(context)

        lines = [
            "## Tier 1: Specification",
            f"Title: {spec.title}",
            f"Goal: {spec.body}",
        ]

        framework_id = self._schema_tailor.detect_framework()
        schema = self._schema_tailor.fetch_schema(framework_id)
        if schema:
            lines.append("Schema:")
            for key, val in schema.items():
                lines.append(f"  {key}: {val}")

        if spec.constraints:
            lines.append(f"Constraints: {spec.constraints}")
        if spec.testing_expectations:
            lines.append(f"Testing Expectations: {spec.testing_expectations}")

        if spec.acceptance_criteria.items:
            lines.append("Acceptance Criteria:")
            for item in spec.acceptance_criteria.items:
                lines.append(f"- {item}")

        if step is not None:
            lines.append(f"Current Plan Step: {step.identifier} — {step.description}")
            if step.action is not None:
                lines.append(f"Action: {step.action.value} Target: {step.target}")

        profile_rules = self._confident_profile_rules(context.engineering_profile)
        if profile_rules:
            lines.append("Engineering Profile:")
            for rule in profile_rules:
                lines.append(f"- {rule}")

        return "\n".join(lines)

    def _render_tier2(self, context: ContextBundle) -> str:
        lines: list[str] = []

        if context.engineering_facts or context.relevant_files:
            lines.append("## Tier 2: Repository")
            if context.engineering_facts:
                lines.append("Engineering Facts:")
                for fact in context.engineering_facts:
                    lines.append(f"- {fact}")
            if context.relevant_files:
                lines.append("Relevant Files:")
                for path in context.relevant_files:
                    lines.append(f"- {path}")

        return "\n".join(lines)

    def _render_tier3(self, context: ContextBundle) -> str:
        if not context.scenario_memory:
            return ""

        lines = ["## Tier 3: Task Memory"]
        for event in context.scenario_memory:
            lines.append(f"- [{event.kind}] {event.payload}")
        return "\n".join(lines)

    def _render_tier4(self, context: ContextBundle) -> str:
        if not context.recent_actions:
            return ""

        lines = ["## Tier 4: Recent Activity"]
        for action in context.recent_actions:
            lines.append(f"- {action}")
        return "\n".join(lines)

    def _render_tier5(self, context: ContextBundle) -> str:
        if not context.artifact_refs:
            return ""

        lines = ["## Tier 5: Artifacts"]
        for ref in context.artifact_refs:
            lines.append(f"- {ref.uri}: {ref.summary}")
        return "\n".join(lines)

    # -- Helpers --------------------------------------------------------

    def _current_step(self, context: ContextBundle) -> PlanStep | None:
        if not context.current_step_id:
            return None
        for step in context.plan.steps:
            if step.identifier == context.current_step_id:
                return step
        return None

    def _confident_profile_rules(self, profile: EngineeringProfile) -> tuple[str, ...]:
        if not profile.rules:
            return ()
        return tuple(
            rule
            for rule in profile.rules
            if profile.confidence.get(rule, 1.0)
            >= _ENGINEERING_PROFILE_CONFIDENCE_THRESHOLD
        )
