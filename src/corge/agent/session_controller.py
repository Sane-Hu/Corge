"""Session controller — orchestrates master-phase state machine.

Spec traceability:
    Tech-spec §3  — MasterPhase, LifecycleState, SpecState, PlanState
    Sysdesign     — AG_CTRL manages transitions; AG_CTRL → AG_LEARN batch update
    FR-001        — spec gate: block until approved specification exists
    FR-008        — plan gate: block execution until plan approved
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC
from pathlib import Path

from corge.agent.coding_agent import CodingAgent
from corge.agent.planning_agent import PlanningAgent
from corge.agent.session import SessionState
from corge.agent.specification_agent import SpecificationAgent
from corge.contracts import (
    ApprovalGatewayPort,
    ArgumentationLogPort,
    ArtifactStorePort,
    AuditLoggerPort,
    BudgetManagerPort,
    ContextBundle,
    ContextPort,
    HeuristicConfig,
    HeuristicUpdaterPort,
    KnowledgeGraphPort,
    LifecycleState,
    MasterPhase,
    MemoryEvent,
    MemoryStorePort,
    Plan,
    PlanState,
    PlanStep,
    ProceduralStep,
    ProviderPort,
    SchemaTailorPort,
    SemanticGap,
    Specification,
    SpecState,
    TechnicalPlan,
    ToolRuntimePort,
    UiPort,
    PromptAssemblerPort,
)

# ---------------------------------------------------------------------------
# Valid lifecycle transitions (Tech-spec §3 state diagram)
# ---------------------------------------------------------------------------

_TRANSITIONS: dict[LifecycleState, LifecycleState] = {
    LifecycleState.START: LifecycleState.REPOSITORY_SELECTION,
    LifecycleState.REPOSITORY_SELECTION: LifecycleState.REPOSITORY_ANALYSIS,
    LifecycleState.REPOSITORY_ANALYSIS: LifecycleState.SPEC_ENTRY,
    LifecycleState.SPEC_ENTRY: LifecycleState.SPEC_VALIDATION,
    LifecycleState.SPEC_VALIDATION: LifecycleState.SPEC_APPROVAL,
    LifecycleState.SPEC_APPROVAL: LifecycleState.PLAN_GENERATION,
    LifecycleState.PLAN_GENERATION: LifecycleState.PLAN_REVIEW,
    LifecycleState.PLAN_REVIEW: LifecycleState.PLAN_APPROVAL,
    LifecycleState.PLAN_APPROVAL: LifecycleState.EXECUTION,
    LifecycleState.EXECUTION: LifecycleState.VERIFICATION,
    LifecycleState.VERIFICATION: LifecycleState.COMPLETION_REVIEW,
    LifecycleState.COMPLETION_REVIEW: LifecycleState.DONE,
}

# Which lifecycle state belongs to which master phase
_STATE_PHASE: dict[LifecycleState, MasterPhase] = {
    LifecycleState.START: MasterPhase.SPECIFICATION,
    LifecycleState.REPOSITORY_SELECTION: MasterPhase.SPECIFICATION,
    LifecycleState.REPOSITORY_ANALYSIS: MasterPhase.SPECIFICATION,
    LifecycleState.SPEC_ENTRY: MasterPhase.SPECIFICATION,
    LifecycleState.SPEC_VALIDATION: MasterPhase.SPECIFICATION,
    LifecycleState.SPEC_APPROVAL: MasterPhase.SPECIFICATION,
    LifecycleState.PLAN_GENERATION: MasterPhase.PLANNING,
    LifecycleState.PLAN_REVIEW: MasterPhase.PLANNING,
    LifecycleState.PLAN_APPROVAL: MasterPhase.PLANNING,
    LifecycleState.EXECUTION: MasterPhase.CODING,
    LifecycleState.VERIFICATION: MasterPhase.CODING,
    LifecycleState.COMPLETION_REVIEW: MasterPhase.CODING,
    LifecycleState.DONE: MasterPhase.CODING,
}


class InvalidTransitionError(Exception):
    """Raised when a requested state transition is not permitted."""


class SessionController:
    """Coordinates master phases: Specification, Planning, and Coding.

    Owns the lifecycle state machine and drives sub-agent transitions.
    Sub-agents (SpecificationAgent, PlanningAgent, CodingAgent) are
    intra-module; their concrete classes are imported directly because
    the modular monolith boundary governs *cross-module* coupling only.

    Construction dependencies (all ports, never concrete classes):
        provider           — LLM adapter
        tool_runtime       — stateless execution primitives
        approval_gateway   — human-in-the-loop gate
        context_service    — context hydration
        memory_store       — memory pyramid persistence
        heuristic_updater  — post-spec Bayesian batch learning
        prompt_assembler   — context template rendering
    """

    def __init__(
        self,
        provider: ProviderPort,
        tool_runtime: ToolRuntimePort,
        approval_gateway: ApprovalGatewayPort,
        context_service: ContextPort,
        memory_store: MemoryStorePort,
        heuristic_updater: HeuristicUpdaterPort,
        knowledge_graph: KnowledgeGraphPort,
        audit_logger: AuditLoggerPort,
        artifact_store: ArtifactStorePort,
        prompt_assembler: PromptAssemblerPort,
    ) -> None:
        # Sub-agents (intra-module wiring)
        self._prompt_assembler = prompt_assembler

        self._spec_agent = SpecificationAgent(
            provider, context_service, self._prompt_assembler, controller=self
        )
        self._plan_agent = PlanningAgent(
            provider, context_service, self._prompt_assembler, controller=self
        )
        self._code_agent = CodingAgent(
            provider,
            tool_runtime,
            approval_gateway,
            context_service,
            knowledge_graph,
            self._prompt_assembler,
            audit_logger,
            artifact_store,
            controller=self,
            on_knowledge_extracted=self._handle_extracted_knowledge,
        )

        self._context_service = context_service
        self._knowledge_graph = knowledge_graph
        self._memory_store = memory_store
        self._heuristic_updater = heuristic_updater

        # State machine
        self._state: LifecycleState = LifecycleState.START
        self._phase: MasterPhase = MasterPhase.SPECIFICATION
        self._spec_state: SpecState | None = None
        self._plan_state: PlanState | None = None

        self._specification: Specification | None = None
        self._plan: Plan | None = None
        self._technical_plan: TechnicalPlan | None = None
        self._procedural_steps: tuple[ProceduralStep, ...] = ()
        self._pending_gaps: tuple[SemanticGap, ...] = ()

        # Repository bootstrapping flag (CC.2)
        self._is_empty_repo: bool = False

    # ------------------------------------------------------------------
    # State machine accessors
    # ------------------------------------------------------------------

    @property
    def specification(self) -> Specification | None:
        """The active specification (FR-001)."""
        return self._specification

    @specification.setter
    def specification(self, value: Specification | None) -> None:
        self._specification = value

    @property
    def plan(self) -> Plan | None:
        """The active execution plan (FR-008)."""
        return self._plan

    @property
    def current_step_idx(self) -> int:
        """Get the index of the first uncompleted step."""
        if not self._plan:
            return 0
        for i, step in enumerate(self._plan.steps):
            if not getattr(step, "completed", False):
                return i
        return len(self._plan.steps)

    @property
    def current_step(self) -> PlanStep | None:
        """Get the current uncompleted step."""
        if not self._plan:
            return None
        idx = self.current_step_idx
        if idx < len(self._plan.steps):
            return self._plan.steps[idx]
        return None

    def mark_step_completed(self) -> None:
        """Mark the current step as completed."""
        import dataclasses
        if not self._plan:
            return
        idx = self.current_step_idx
        if idx < len(self._plan.steps):
            steps = list(self._plan.steps)
            steps[idx] = dataclasses.replace(steps[idx], completed=True)
            self._plan = dataclasses.replace(self._plan, steps=tuple(steps))

    def uncomplete_previous_step(self) -> bool:
        """Uncomplete the previous step to navigate back. Returns True if successful."""
        import dataclasses
        if not self._plan:
            return False
        idx = self.current_step_idx
        if idx > 0:
            steps = list(self._plan.steps)
            steps[idx - 1] = dataclasses.replace(steps[idx - 1], completed=False)
            self._plan = dataclasses.replace(self._plan, steps=tuple(steps))
            return True
        return False

    @property
    def technical_plan(self) -> TechnicalPlan | None:
        """The active technical architecture plan."""
        return self._technical_plan

    @technical_plan.setter
    def technical_plan(self, value: TechnicalPlan | None) -> None:
        self._technical_plan = value

    @property
    def procedural_steps(self) -> tuple[ProceduralStep, ...]:
        """The active procedural steps."""
        return self._procedural_steps

    @procedural_steps.setter
    def procedural_steps(self, value: tuple[ProceduralStep, ...]) -> None:
        self._procedural_steps = value

    def set_approved_plan(self, plan: Plan) -> None:
        """Set the approved execution plan."""
        self._plan = plan

    @property
    def state(self) -> LifecycleState:
        """Current lifecycle state (read-only)."""
        return self._state

    @property
    def phase(self) -> MasterPhase:
        """Current master phase (read-only)."""
        return self._phase

    @property
    def active_agent_name(self) -> str:
        """User-friendly name of the currently active agent."""
        if self._phase == MasterPhase.SPECIFICATION:
            return "Specification Agent"
        elif self._phase == MasterPhase.PLANNING:
            return "Planning Agent"
        elif self._phase == MasterPhase.CODING:
            return "Coding Agent"
        return "System"

    @property
    def spec_state(self) -> SpecState | None:
        """Active nested spec sub-state, or None outside spec phase."""
        return self._spec_state

    @property
    def plan_state(self) -> PlanState | None:
        """Active nested plan sub-state, or None outside plan phase."""
        return self._plan_state

    @property
    def is_empty_repo(self) -> bool:
        """True when the selected repository contains no source files (CC.2, FR-015).

        When True, the Planning phase generates project structure from
        the approved specification rather than analyzing existing code.
        """
        return self._is_empty_repo

    def set_empty_repo(self, empty: bool) -> None:
        """Set by REPOSITORY_ANALYSIS phase after scanning the selected directory."""
        self._is_empty_repo = empty

    def load_from_session(self, state: SessionState) -> None:
        """Restore internal state from a SessionState object."""
        self._state = state.lifecycle_state
        self._phase = state.master_phase
        self._spec_state = state.spec_state
        self._plan_state = state.plan_state
        self._specification = state.specification
        self._plan = state.plan
        self._technical_plan = state.technical_plan
        self._procedural_steps = state.procedural_steps
        if state.repo_root:
            pass  # Currently repo_root is handled elsewhere

    def advance(self) -> None:
        """Move to the next logical phase in the lifecycle.

        Raises InvalidTransitionError if the current state cannot advance.
        """
        if self._state not in _TRANSITIONS:
            raise InvalidTransitionError(f"Cannot advance from terminal state {self._state}")
        self.transition_to(_TRANSITIONS[self._state])

    def analyze_repository(self, target_repo: Path) -> ContextBundle:
        """Analyze repository structure and build knowledge graph."""
        from corge.contracts.models import RepositoryContext
        bundle = self._context_service.load_context(
            RepositoryContext(root=target_repo)
        )
        if not self.is_empty_repo:
            self._knowledge_graph.build_graph(bundle.repository_context)
        return bundle

    def transition_to(self, target_state: LifecycleState) -> LifecycleState:
        """Manually transition to a specific state (supports backward transitions)."""
        if target_state == LifecycleState.SPEC_APPROVAL:
            unresolved = [g for g in self._pending_gaps if not g.resolved]
            if unresolved:
                raise InvalidTransitionError(
                    f"Cannot transition to SPEC_APPROVAL: {len(unresolved)} unresolved gaps exist."
                )
        self._state = target_state
        self._phase = _STATE_PHASE[target_state]
        self._sync_nested_states()
        return self._state

    def _sync_nested_states(self) -> None:
        """Keep nested state machines aligned with the primary lifecycle."""
        if self._phase == MasterPhase.SPECIFICATION:
            if self._state == LifecycleState.SPEC_ENTRY:
                self._spec_state = SpecState.CANVAS_FREESTYLE
            elif self._state == LifecycleState.SPEC_VALIDATION:
                self._spec_state = SpecState.CONCRETIZATION
                if self._pending_gaps:
                    self._spec_state = SpecState.ARGUMENTATION_DIFF
            elif self._state == LifecycleState.SPEC_APPROVAL:
                self._spec_state = SpecState.SPEC_METASTABLE
            self._plan_state = None
        elif self._phase == MasterPhase.PLANNING:
            if self._state == LifecycleState.PLAN_GENERATION:
                self._plan_state = PlanState.TECH_PLAN_REITERATION
            elif self._state == LifecycleState.PLAN_REVIEW:
                self._plan_state = PlanState.STEPS_REITERATION
            self._spec_state = None
        else:
            self._spec_state = None
            self._plan_state = None

    def advance_spec_state(self, next_spec: SpecState) -> None:
        """Manually advance the nested spec sub-state.

        Used by the UI loop during the Socratic argumentation cycle to
        signal gap resolution before triggering SPEC_METASTABLE.
        """
        self._spec_state = next_spec

    def advance_plan_state(self, next_plan: PlanState) -> None:
        """Manually advance the nested plan sub-state."""
        self._plan_state = next_plan

    # ------------------------------------------------------------------
    # AgentPort delegation — Specification phase
    # ------------------------------------------------------------------

    def analyze_specification_gaps(self, canvas_text: str) -> tuple[SemanticGap, ...]:
        self._pending_gaps = self._spec_agent.analyze_specification_gaps(canvas_text)
        return self._pending_gaps

    def concretize(self, canvas_text: str) -> Specification:
        """Compile raw canvas text into a structured Specification."""
        spec = self._spec_agent.concretize(canvas_text)
        self._specification = spec
        return spec

    def run_socratic_loop(
        self,
        canvas_text: str,
        argumentation_log: ArgumentationLogPort,
        ui: UiPort,
        max_questions: int = 3,
    ) -> tuple[Specification, tuple[SemanticGap, ...]]:
        """Run the interactive specification refinement loop.

        Delegates to the internal SpecificationAgent and returns the updated
        specification and any unresolved gaps.
        """
        from datetime import datetime

        from corge.contracts.models import CanvasSnapshot

        snapshot = CanvasSnapshot(
            text=canvas_text, timestamp=datetime.now(UTC).isoformat()
        )
        argumentation_log.record_canvas_snapshot(snapshot)

        spec, gaps = self._spec_agent.run_socratic_loop(
            canvas_text, argumentation_log, ui, max_questions=max_questions
        )
        self._specification = spec
        self._pending_gaps = gaps
        return spec, gaps

    def load_heuristic_config(self) -> HeuristicConfig:
        """Load heuristic configuration settings."""
        return self._heuristic_updater.load_config()

    def format_spec_to_text(
        self, spec: Specification, gaps: tuple[SemanticGap, ...]
    ) -> str:
        """Format specification and gaps into a markdown template."""
        return self._spec_agent.format_spec_to_text(spec, gaps)

    def merge_templated_responses(
        self, spec: Specification, edited_text: str
    ) -> Specification:
        """Merge resolved gap templates back into structured specification fields."""
        updated_spec = self._spec_agent.merge_templated_responses(spec, edited_text)
        self._specification = updated_spec
        
        # Check deterministically which of the pending gaps were resolved by looking for their placeholder in edited_text
        import dataclasses
        resolved_gaps = []
        normalized_text = edited_text.replace("\r\n", "\n")
        for gap in self._pending_gaps:
            placeholder = f"[GAP: {gap.topic}]"
            default_res = "Resolution: <Enter details here>"
            
            # If the placeholder is completely removed, it is resolved
            if placeholder not in normalized_text:
                resolved_gaps.append(dataclasses.replace(gap, resolved=True))
                continue
                
            # If the placeholder is present, check if the default resolution line is still there
            unresolved_block = f"{placeholder}\n{default_res}"
            if unresolved_block in normalized_text:
                resolved_gaps.append(gap)  # Still unresolved
            else:
                resolved_gaps.append(dataclasses.replace(gap, resolved=True))
                
        self._pending_gaps = tuple(resolved_gaps)
        return updated_spec

    # ------------------------------------------------------------------
    # AgentPort delegation — Planning phase
    # ------------------------------------------------------------------

    def generate_technical_plan(
        self,
        specification: Specification,
        on_token: Callable[[str], None] | None = None,
    ) -> TechnicalPlan:
        plan = self._plan_agent.generate_technical_plan(
            specification, on_token=on_token
        )
        self._technical_plan = plan
        return plan

    def generate_procedural_steps(
        self,
        technical_plan: TechnicalPlan,
        on_token: Callable[[str], None] | None = None,
    ) -> tuple[ProceduralStep, ...]:
        steps = self._plan_agent.generate_procedural_steps(
            technical_plan, on_token=on_token
        )
        self._procedural_steps = steps
        return steps

    # ------------------------------------------------------------------
    # AgentPort delegation — Coding phase
    # ------------------------------------------------------------------

    def collect_context(
        self, step: PlanStep, specification: Specification
    ) -> ContextBundle:
        return self._prompt_assembler.collect_context(step, specification, self._technical_plan)

    def execute_step(
        self,
        step: PlanStep,
        context: ContextBundle,
        on_token: Callable[[str], None] | None = None,
    ) -> None:
        self._code_agent.execute_step(step, context, on_token=on_token)

    def evaluate_completion(
        self,
        plan: Plan,
        context: ContextBundle,
        on_token: Callable[[str], None] | None = None,
    ) -> bool:
        return self._code_agent.evaluate_completion(plan, context, on_token=on_token)

    # ------------------------------------------------------------------
    # Memory persistence (AgentPort)
    # ------------------------------------------------------------------

    def update_memory(self, event: MemoryEvent) -> None:
        """Persist a memory event to the pyramid (spec §3 step 8)."""
        self._memory_store.store_event(event)

    def _handle_extracted_knowledge(self, facts: list[str], rules: list[str]) -> None:
        """Process knowledge extracted by the coding agent during execution."""
        for fact in facts:
            if isinstance(fact, str) and fact.strip():
                self._memory_store.store_fact(fact.strip(), source="execution")
        if rules:
            from corge.contracts.models import EngineeringProfile

            profile = EngineeringProfile(rules=tuple(rules))
            self._memory_store.update_profile(profile)

    # ------------------------------------------------------------------
    # Heuristic learning (sysdesign AG_CTRL → AG_LEARN)
    # ------------------------------------------------------------------

    def finalize_spec_phase(self, abandoned: bool = False) -> None:
        """Trigger batch heuristic update after spec completion or abandonment.

        Called by the orchestrating UI loop when the spec phase ends
        (either with an approved spec or when the user abandons).
        """
        self._heuristic_updater.run_batch_update(abandoned=abandoned)
