"""Prompt construction — satisfies ``contracts.PromptAssemblerPort``.

Spec traceability:
    docs/02-technical-spec.md  Section 4 "Ephemeral Prompt Tiers"
    docs/02-technical-spec.md  Section 3, step 3 "Assemble Prompt"
    src/corge/contracts/ports.py  PromptAssemblerPort

Open design questions (NOT silently resolved — see comments below):
    1. ``MemoryStorePort`` (contracts/ports.py) exposes only write
       methods (store_event, store_fact, store_scenario,
       update_profile). It has no read/query method, so this module
       cannot yet retrieve persisted scenario memory for Tier 3.
       ``scenario_memory`` is therefore always empty until a read
       method is added to ``MemoryStorePort`` (tracked separately;
       do not invent one here per AGENTS.md "No Placeholders" /
       "Never infer or invent requirements").
    2. The technical spec's architecture diagram and sequence
       diagram disagree on whether ``context`` module or
       ``prompt_assembler`` itself is responsible for calling
       ``KnowledgeGraphPort`` / ``ContextPort``. This implementation
       assumes ``PromptAssembler`` receives those ports via
       constructor injection (consistent with how ``agent.service``
       receives its collaborators). This is a design assumption,
       not a confirmed requirement — flag for review if incorrect.
    3. ``collect_context(step)`` cannot be implemented yet: it must
       call ``ContextPort.retrieve_relevant_context(specification, step)``,
       but ``PlanStep`` carries no reference back to the active
       ``Specification``, and ``PromptAssemblerPort.collect_context``
       only receives a ``PlanStep``. Left raising ``NotImplementedError``
       with an explanatory message rather than guessed.
    4. ``ContextBundle`` has no field identifying which step of
       ``plan.steps`` is "the current plan step", yet
       docs/02-technical-spec.md Section 4 requires Tier 1 to always
       include it. ``contracts/models.py`` was intentionally left
       unmodified for this change (contract edits require team
       coordination per AGENTS.md). As a result, the "Current Plan
       Step" line in Tier 1 is always omitted for now — see
       ``_current_step`` below. Recommend either adding
       ``current_step_index: int`` to ``ContextBundle`` or an
       equivalent field, via a coordinated contract change.
"""

from __future__ import annotations

from corge.contracts import ContextBundle, EngineeringProfile, PlanStep
from corge.contracts.ports import ContextPort, KnowledgeGraphPort

# Rules below this confidence are excluded from Tier 1 prompt output.
# 02-technical-spec.md does not state a numeric threshold; this value
# is a documented assumption, not a confirmed requirement.
_ENGINEERING_PROFILE_CONFIDENCE_THRESHOLD = 0.5


class PromptAssembler:
    """Concrete prompt assembler.  Satisfies ``contracts.PromptAssemblerPort``.

    Builds the five-tier ephemeral prompt described in
    docs/02-technical-spec.md Section 4:

        Tier 1 (always present): spec, acceptance criteria, plan step,
            engineering profile.
        Tier 2 (repository): engineering facts, graph queries, relevant
            file summaries.
        Tier 3 (task memory): scenario memory.
        Tier 4 (history): recent actions.
        Tier 5 (artifacts): artifact URIs and summaries.
    """

    def __init__(
        self,
        context_port: ContextPort | None = None,
        knowledge_graph_port: KnowledgeGraphPort | None = None,
    ) -> None:
        # Both collaborators are optional so this module can be unit
        # tested (and partially used) before context/knowledge_graph
        # are wired in by the agent loop. See open design question #2
        # above re: who owns calling these ports.
        self._context_port = context_port
        self._knowledge_graph_port = knowledge_graph_port

    def collect_context(self, step: PlanStep) -> ContextBundle:
        """Gather a ``ContextBundle`` for the given plan step.

        Delegates repository/relevant-file retrieval to ``ContextPort``
        when available. ``scenario_memory`` is left empty — see module
        docstring, open design question #1.
        """
        if self._context_port is None:
            raise NotImplementedError(
                "PromptAssembler.collect_context requires a ContextPort "
                "collaborator; none was provided to the constructor."
            )

        # ContextPort.retrieve_relevant_context needs a Specification,
        # which PlanStep does not carry. PlanStep only has identifier/
        # description/action/target (see contracts/models.py). Until
        # the spec clarifies how the assembler obtains the active
        # Specification for a given step, this is intentionally left
        # unimplemented rather than guessed.
        raise NotImplementedError(
            "collect_context cannot resolve the active Specification "
            "for this PlanStep — PlanStep does not carry a "
            "specification reference and ContextPort.retrieve_relevant_context "
            "requires one. This is an open spec question, not an oversight."
        )

    def assemble_prompt(self, context: ContextBundle) -> str:
        """Render a ``ContextBundle`` into the ephemeral prompt string.

        Tiers are rendered in the order defined by
        docs/02-technical-spec.md Section 4. A tier section is omitted
        entirely when it has no content, rather than emitted with an
        empty body.
        """
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

        if context.relevant_files:
            lines.append("## Tier 2: Repository")
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
        # ContextBundle.plan carries the FULL plan (all steps), not a
        # pointer to "the step currently being executed". There is no
        # field anywhere in contracts/models.py that identifies which
        # step is current. Falling back to steps[0] would silently
        # render the wrong step's instructions once execution moves
        # past step 1 — worse than omitting the line. Per project
        # rules (AGENTS.md "No Placeholders" / "Never infer or invent
        # requirements"), this is intentionally left unresolved rather
        # than guessed or worked around by editing contracts/models.py
        # unilaterally. Tracked as an open question; see module
        # docstring.
        return None

    def _confident_profile_rules(
        self, profile: EngineeringProfile
    ) -> tuple[str, ...]:
        if not profile.rules:
            return ()
        return tuple(
            rule
            for rule in profile.rules
            if profile.confidence.get(rule, 1.0)
            >= _ENGINEERING_PROFILE_CONFIDENCE_THRESHOLD
        )