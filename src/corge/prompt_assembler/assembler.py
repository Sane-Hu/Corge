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
    TechnicalPlan,
)

# Rules below this confidence are excluded from prompt output.
# Defined in 02-technical-spec.md Section 4 (Engineering Profile).
_ENGINEERING_PROFILE_CONFIDENCE_THRESHOLD = 0.5
_TOKEN_BUDGET = 100_000


class PromptAssembler:
    """Builds the ephemeral execution prompt from a context bundle using semantic tagging."""

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
        self, step: PlanStep, specification: Specification, technical_plan: TechnicalPlan | None = None
    ) -> ContextBundle:
        """Fetch all required context layers for the current plan step."""
        return self._context_port.retrieve_relevant_context(specification, step, technical_plan)

    def assemble_spec_prompt(self, context: ContextBundle, instruction: str) -> str:
        """Assemble the objective/constraint-based prompt for the Specification phase."""
        context = self._enforce_budget(context)
        sections = [
            self._render_schema(context),
            self._render_engineering_profile(context),
            self._render_argumentation_entries(context),
            f"<objective>\n{instruction}\n</objective>",
        ]
        return "\n\n".join(filter(bool, sections))

    def assemble_plan_prompt(self, context: ContextBundle, instruction: str) -> str:
        """Assemble the objective/constraint-based prompt for the Planning phase."""
        context = self._enforce_budget(context)
        sections = [
            self._render_schema(context),
            self._render_engineering_profile(context),
            self._render_repository_facts(context),
            self._render_specification(context),
            self._render_relevant_files(context),
            f"<objective>\n{instruction}\n</objective>",
        ]
        return "\n\n".join(filter(bool, sections))

    def assemble_coding_prompt(self, context: ContextBundle) -> str:
        """Assemble the semantic prompt for the Coding phase (9-step execution)."""
        context = self._enforce_budget(context)
        
        step = self._current_step(context)
        step_desc = step.description if step else "Execute step"
        step_id = step.identifier if step else "unknown"
        
        static_instruction = (
            "You are a coding agent executing a precise implementation plan.\n\n"
            "Determine the next tool action required. Respond with a JSON block:\n"
            "```json\n"
            "{\n"
            '  "done": false,\n'
            '  "actions": [\n'
            "    {\n"
            '      "action": "READ|WRITE|EDIT|BASH",\n'
            '      "target": "<path or shell command>",\n'
            '      "content": "<full file content for WRITE>",\n'
            '      "old": "<exact substring to replace for EDIT '
            '— include 3+ lines of context>",\n'
            '      "new": "<replacement substring for EDIT>"\n'
            "    }\n"
            "  ],\n"
            '  "facts_learned": ["<optional list of new repository facts discovered>"],\n'
            '  "profile_rules_learned": ["<optional list of new coding style rules discovered>"]\n'
            "}\n"
            "```\n"
            "Rules:\n"
            "- 'content' is required for WRITE.\n"
            "- 'old' and 'new' are required for EDIT. 'old' must be unique in the file.\n"
            "- For BASH, 'target' is the command string.\n"
            "- Tool Selection Guidelines: Prefer EDIT over WRITE for modifying existing files. Only use WRITE to create new files or completely rewrite small files. This minimizes token consumption and output latency.\n"
            "- Deduplication/Batching: Request all needed files at once in a single READ action to minimize turn count.\n"
            "- Testing/Verification: Run verification tests (e.g. pytest or compile checks) immediately after editing/writing code, before completing the step.\n"
            "- Bash Safety: Ensure that bash commands you run return exit code 0. Running commands that return non-zero exit codes will trigger a ToolExecutionError and halt execution.\n"
            "- JSON Formatting: Respond strictly with the JSON block. Do not include verbose explanations or text outside the json block.\n"
            "- Set 'done': true when the step is complete."
        )
        
        # Prevent noise: do not include reasoning logs in coding phase,
        # but the approved architectural blueprint (TechnicalPlan) is highly useful.
        
        dynamic_step = (
            f"Current step: {step_desc}\n"
            f"Step identifier: {step_id}"
        )

        sections = [
            self._render_schema(context),
            self._render_engineering_profile(context),
            self._render_repository_facts(context),
            self._render_specification(context),
            self._render_technical_plan(context),
            self._render_relevant_files(context),
            f"<coding_instructions>\n{static_instruction}\n</coding_instructions>",
            f"<current_step>\n{dynamic_step}\n</current_step>",
            self._render_scenario_memory(context),
            self._render_recent_activity(context),
            self._render_artifacts(context),
        ]
        return "\n\n".join(filter(bool, sections))

    # -- Internal Renderers ---------------------------------------------

    def _enforce_budget(self, context: ContextBundle) -> ContextBundle:
        """Ensure context fits within the token limit."""
        context = self._budget_manager.rank_context(context)
        if self._budget_manager.estimate_tokens(context) > _TOKEN_BUDGET:
            return self._budget_manager.compact(context)
        return context

    def _render_specification(self, context: ContextBundle) -> str:
        spec = context.specification
        if not spec or not spec.title:
            return ""

        lines = [
            "<specification>",
            f"Title: {spec.title}",
            f"Requirements & User Stories:\n{spec.body}",
        ]
        if spec.constraints:
            lines.append(f"Constraints:\n{spec.constraints}")
        if spec.testing_expectations:
            lines.append(f"Testing Expectations:\n{spec.testing_expectations}")
        if spec.acceptance_criteria.items:
            lines.append("Acceptance Criteria:")
            for item in spec.acceptance_criteria.items:
                lines.append(f"- {item}")
        lines.append("</specification>")
        return "\n".join(lines)

    def _render_schema(self, context: ContextBundle) -> str:
        framework_id = self._schema_tailor.detect_framework()
        schema = self._schema_tailor.fetch_schema(framework_id)
        if not schema:
            return ""
        
        lines = ["<framework_schema>"]
        for key, val in schema.items():
            lines.append(f"  {key}: {val}")
        lines.append("</framework_schema>")
        return "\n".join(lines)

    def _render_engineering_profile(self, context: ContextBundle) -> str:
        profile_rules = self._confident_profile_rules(context.engineering_profile)
        if not profile_rules:
            return ""

        lines = ["<engineering_profile>"]
        for rule in profile_rules:
            lines.append(f"- {rule}")
        lines.append("</engineering_profile>")
        return "\n".join(lines)

    def _render_repository_facts(self, context: ContextBundle) -> str:
        if not context.engineering_facts:
            return ""

        lines = ["<repository_facts>"]
        for fact in context.engineering_facts:
            lines.append(f"- {fact}")
        lines.append("</repository_facts>")
        return "\n".join(lines)

    def _render_relevant_files(self, context: ContextBundle) -> str:
        if not context.relevant_files:
            return ""

        lines = ["<relevant_files>"]
        for path in context.relevant_files:
            lines.append(f"- {path}")
        lines.append("</relevant_files>")
        return "\n".join(lines)

    def _render_scenario_memory(self, context: ContextBundle) -> str:
        if not context.scenario_memory:
            return ""

        lines = ["<task_memory>"]
        for event in context.scenario_memory:
            lines.append(f"- [{event.kind}] {event.payload}")
        lines.append("</task_memory>")
        return "\n".join(lines)

    def _render_recent_activity(self, context: ContextBundle) -> str:
        lines = []
        if context.markov_context:
            lines.append("<markov_context>")
            lines.append(f"Agent proposal: {context.markov_context.agent_proposal}")
            lines.append(f"User correction: {context.markov_context.user_correction}")
            lines.append(f"Prior trajectory: {context.markov_context.compressed_trajectory}")
            lines.append("</markov_context>")

        if context.recent_actions:
            lines.append("<recent_actions>")
            for action in context.recent_actions:
                lines.append(f"- {action}")
            lines.append("</recent_actions>")
            
        return "\n".join(lines)

    def _render_artifacts(self, context: ContextBundle) -> str:
        if not context.artifact_refs:
            return ""

        lines = ["<artifacts>"]
        for ref in context.artifact_refs:
            lines.append(f"- {ref.uri}: {ref.summary}")
        lines.append("</artifacts>")
        return "\n".join(lines)

    def _render_argumentation_entries(self, context: ContextBundle) -> str:
        if not context.argumentation_entries:
            return ""
        lines = ["<argumentation_history>"]
        for entry in context.argumentation_entries:
            lines.append(f"Question: {entry.question}")
            lines.append(f"Answer: {entry.answer}")
        lines.append("</argumentation_history>")
        return "\n".join(lines)

    def _render_technical_plan(self, context: ContextBundle) -> str:
        if not context.technical_plan or not context.technical_plan.content:
            return ""
        return f"<technical_plan>\n{context.technical_plan.content}\n</technical_plan>"

    # -- Helpers --------------------------------------------------------

    def _current_step(self, context: ContextBundle) -> PlanStep | None:
        if not context.current_step_id or not context.plan:
            return None
        for step in context.plan.steps:
            if step.identifier == context.current_step_id:
                return step
        return None

    def _confident_profile_rules(self, profile: EngineeringProfile) -> tuple[str, ...]:
        if not profile or not profile.rules:
            return ()
        return tuple(
            rule
            for rule in profile.rules
            if profile.confidence.get(rule, 1.0)
            >= _ENGINEERING_PROFILE_CONFIDENCE_THRESHOLD
        )
