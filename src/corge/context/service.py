"""Context retrieval and refresh — satisfies ``contracts.ContextPort``.

Spec traceability:
    Tech-spec §4 §Context Service & Isolation Policies
        — 3-Layer isolation: spec / planning / coding
        — Markov Context Chaining: N-1 injection, compressed trajectory
    Tech-spec §4 §Ephemeral Prompt Tiers
        — Tier 1: spec, plan, profile  (always present)
        — Tier 2: repo facts, graph    (repository understanding)
        — Tier 3: scenario memory      (task memory)
    Sysdesign flow steps 5–8: CTX_ENG → CTX_ASM → CTX_BUD
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from corge.contracts import (
    AcceptanceCriteria,
    ContextBundle,
    EngineeringProfile,
    GraphQuery,
    KnowledgeGraphPort,
    MarkovStepContext,
    MasterPhase,
    MemoryEvent,
    MemoryStorePort,
    Plan,
    PlanStep,
    RepositoryContext,
    Specification,
    TechnicalPlan,
)

# ---------------------------------------------------------------------------
# Layer isolation: which context layers are visible per master phase
# (Tech-spec §4 §3-Layer Isolation)
# ---------------------------------------------------------------------------

# Coding phase omits argumentation logs, AST graph relations, and
# architectural plans.  This is enforced by simply not querying those
# sources when building a coding-phase bundle.
_CODING_EXCLUDED_GRAPH_KINDS = frozenset({"argumentation", "architecture"})

_COMPRESSED_HISTORY_LIMIT = 5  # max N-2…N-Start entries to keep


_log = logging.getLogger(__name__)


class ContextService:
    """Concrete context service.  Satisfies ``contracts.ContextPort``.

    Wires together the Knowledge Graph and Memory Pyramid to build
    layered ContextBundle objects for each master phase.

    Args:
        knowledge_graph: KG port for Tier 2 repository queries.
        memory_store:    Memory pyramid for Tier 2 facts and Tier 3 scenarios.
    """

    def __init__(
        self,
        knowledge_graph: KnowledgeGraphPort,
        memory_store: MemoryStorePort,
        root: Path,
    ) -> None:
        self._kg = knowledge_graph
        self._memory = memory_store
        self._root = root

        # Markov chaining state (Tier 4 / coding phase)
        self._last_step_result: str = ""
        self._last_user_correction: str = ""
        self._compressed_history: list[str] = []
        self._last_step_id: str | None = None
        self._recent_actions: list[str] = []

        # Context query caching (N-1 caching)
        self._cached_profile: EngineeringProfile | None = None
        self._cached_facts: tuple[str, ...] | None = None
        self._cached_files: tuple[str, ...] | None = None

    def clear_cache(self) -> None:
        """Clear query cache."""
        self._cached_profile = None
        self._cached_facts = None
        self._cached_files = None

    def record_action(self, action_summary: str) -> None:
        """Record an executed action for recent_actions context."""
        self._recent_actions.append(action_summary)

    # ------------------------------------------------------------------
    # ContextPort interface
    # ------------------------------------------------------------------

    def load_context(self, repository_context: RepositoryContext) -> ContextBundle:
        """Load initial context for the Specification phase (Layer 1).

        Tier 2 (repo understanding) is populated from KG and facts.
        Argumentation history and architectural plans are excluded
        (3-Layer isolation — spec phase does not need coding artefacts).
        """
        self.clear_cache()
        return self._build_bundle(
            specification=_empty_spec(),
            plan=Plan(()),
            repository_context=repository_context,
            phase=MasterPhase.SPECIFICATION,
        )

    def refresh_context(
        self, repository_context: RepositoryContext, technical_plan: TechnicalPlan | None = None
    ) -> ContextBundle:
        """Refresh context for the Planning phase (Layer 2)."""
        self.clear_cache()
        return self._build_bundle(
            specification=_empty_spec(),
            plan=Plan(()),
            repository_context=repository_context,
            phase=MasterPhase.PLANNING,
            technical_plan=technical_plan,
        )

    def retrieve_relevant_context(
        self, specification: Specification, step: PlanStep, technical_plan: TechnicalPlan | None = None, rotate: bool = True
    ) -> ContextBundle:
        """Retrieve Coding-phase context with Markov chaining (Layer 3).

        Injects Step N-1 outputs and compresses older history.
        Argumentation logs and AST graph relations are excluded
        (3-Layer isolation — coding prompt must stay focused).
        """
        if rotate:
            # Rotate Markov history: push N-1 into compressed trajectory
            if self._last_step_result:
                truncated = self._last_step_result[:200]
                self._compressed_history.append(f"Prev: {truncated}")
                if len(self._compressed_history) > _COMPRESSED_HISTORY_LIMIT:
                    self._compressed_history.pop(0)
            self._recent_actions.clear()

        self._last_step_id = step.identifier

        markov_ctx = MarkovStepContext(
            agent_proposal=self._last_step_result,
            user_correction=self._last_user_correction,
            compressed_trajectory=" | ".join(self._compressed_history),
        )

        plan_for_step = Plan((step,), specification_ref=specification.title)

        return self._build_bundle(
            specification=specification,
            plan=plan_for_step,
            repository_context=RepositoryContext(root=self._root),
            phase=MasterPhase.CODING,
            markov_context=markov_ctx,
            current_step_id=step.identifier,
            technical_plan=technical_plan,
        )

    def update_markov_state(self, result: str, correction: str = "") -> None:
        """Update the N-1 Markov state after a step completes."""
        self._last_step_result = result
        self._last_user_correction = correction
        self.clear_cache()

    # ------------------------------------------------------------------
    # Internal bundle builder
    # ------------------------------------------------------------------

    def _build_bundle(
        self,
        specification: Specification,
        plan: Plan,
        repository_context: RepositoryContext,
        phase: MasterPhase,
        markov_context: MarkovStepContext | None = None,
        current_step_id: str | None = None,
        technical_plan: TechnicalPlan | None = None,
    ) -> ContextBundle:
        """Assemble a ContextBundle using KG and memory for Tiers 2–3.

        3-Layer isolation is enforced here: the coding phase excludes
        graph kinds that pollute its context window.
        """
        # Tier 1 — profile
        if self._cached_profile is None:
            self._cached_profile = self._memory.get_profile()
        engineering_profile = self._cached_profile

        # Tier 2a — repo file list from KG
        relevant_files: tuple[str, ...] = ()
        if self._cached_files is None:
            try:
                result = self._kg.query_graph(GraphQuery(expression="files"))
                self._cached_files = tuple(sorted(n.node_id for n in result.nodes[:50]))
            except (RuntimeError, sqlite3.OperationalError, ValueError) as exc:
                _log.warning("KG query failed during context assembly: %s", exc)
                self._cached_files = ()
        relevant_files = self._cached_files

        # Tier 2 — repo conventions + local rules
        engineering_facts: tuple[str, ...] = ()
        if self._cached_facts is None:
            try:
                facts = self._memory.get_facts(limit=50)
                self._cached_facts = tuple(facts) if facts else ()
            except (sqlite3.OperationalError, FileNotFoundError, OSError) as exc:
                _log.warning("Failed to load engineering facts: %s", exc)
                self._cached_facts = ()
        engineering_facts = self._cached_facts

        # Argumentation entries (SPECIFICATION phase only)
        argumentation_entries: tuple[ArgumentationEntry, ...] = ()
        if phase == MasterPhase.SPECIFICATION:
            log_path = self._root / ".agent" / "argumentation_log.json"
            if log_path.exists():
                try:
                    from corge.contracts import ArgumentationEntry
                    data = json.loads(log_path.read_text(encoding="utf-8"))
                    entries = []
                    for e in data.get("entries", []):
                        try:
                            entries.append(ArgumentationEntry(**e))
                        except (TypeError, KeyError):
                            pass
                    argumentation_entries = tuple(entries)
                except Exception as exc:
                    _log.warning("Failed to load argumentation log: %s", exc)

        # Tier 3 — scenario memory (coding phase only; excluded from spec/plan)
        scenario_memory: tuple[MemoryEvent, ...] = ()
        if phase == MasterPhase.CODING:
            if specification and specification.title:
                try:
                    raw = self._memory.get_scenario(specification.title, limit=5)
                    scenario_memory = tuple(
                        MemoryEvent(
                            kind=specification.title,
                            payload=entry.get("payload", {}),
                            timestamp=entry.get("timestamp", ""),
                        )
                        for entry in raw
                    )
                except (
                    json.JSONDecodeError,
                    FileNotFoundError,
                    OSError,
                    KeyError,
                ) as exc:
                    _log.warning("Failed to load scenario memory: %s", exc)

        return ContextBundle(
            specification=specification,
            plan=plan,
            repository_context=repository_context,
            engineering_profile=engineering_profile,
            relevant_files=relevant_files,
            scenario_memory=scenario_memory,
            markov_context=markov_context,
            current_step_id=current_step_id,
            engineering_facts=engineering_facts,
            argumentation_entries=argumentation_entries,
            technical_plan=technical_plan,
            recent_actions=tuple(self._recent_actions),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_spec() -> Specification:
    return Specification(
        title="", body="", acceptance_criteria=AcceptanceCriteria(items=())
    )
