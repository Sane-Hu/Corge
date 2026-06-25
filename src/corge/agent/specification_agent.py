"""Specification agent — handles SpecState reiterations.

Spec traceability:
    FR-002   — guided spec wizard fields
    FR-016   — Socratic specification wizard
    Tech-spec §3 §Nested State Machines item 1
        CANVAS_FREESTYLE → CONCRETIZATION → ARGUMENTATION_DIFF → SPEC_METASTABLE
"""

from __future__ import annotations

import json
import re
from typing import Callable
from datetime import UTC, datetime

from corge.contracts import (
    AcceptanceCriteria,
    ArgumentationEntry,
    ArgumentationLogPort,
    ProviderMessage,
    ProviderPort,
    SemanticGap,
    Specification,
    UiPort,
    ContextPort,
    PromptAssemblerPort,
    RepositoryContext,
)
from pathlib import Path


class SpecificationAgent:
    """Manages the interactive specification wizard and semantic gaps."""

    def __init__(self, provider: ProviderPort, context_service: ContextPort, prompt_assembler: PromptAssemblerPort) -> None:
        self._provider = provider
        self._context_service = context_service
        self._prompt_assembler = prompt_assembler

    # ------------------------------------------------------------------
    # CONCRETIZATION sub-state (Tech-spec §3 SpecState)
    # ------------------------------------------------------------------

    def concretize(self, canvas_text: str, on_token: Callable[[str], None] | None = None) -> Specification:
        """Compile raw canvas text into a structured Specification (FR-002).

        Prompts the model to extract the structured wizard fields:
        title, body, acceptance criteria, constraints, testing expectations.
        Returns a best-effort Specification; gaps remain for ARGUMENTATION_DIFF.
        """
        instruction = (
            "Extract the following structured fields from the raw "
            "brainstorming text below. Ensure you respect the engineering profile and repository facts.\n"
            "Return ONLY a JSON object with these exact keys:\n"
            '  "title": string — the main business goal (one sentence)\n'
            '  "body": string — narrative of user stories and functional requirements\n'
            '  "acceptance_criteria": list of strings — verifiable pass/fail criteria\n'
            '  "constraints": string — technical or business constraints\n'
            '  "testing_expectations": string — what tests are required\n\n'
            "If a field cannot be determined from the text, use an empty "
            "string or empty list.\n\n"
            f"Brainstorming text:\n{canvas_text}"
        )
        ctx_bundle = self._context_service.load_context(RepositoryContext(root=Path(".")))
        prompt = self._prompt_assembler.assemble_spec_prompt(ctx_bundle, instruction)
        msg = ProviderMessage(role="user", content=prompt)
        response = self._provider.chat((msg,), on_token=on_token)

        match = re.search(r"\{.*\}", response.content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                criteria_items = tuple(
                    str(c) for c in data.get("acceptance_criteria", [])
                )
                return Specification(
                    title=str(data.get("title", "")).strip(),
                    body=str(data.get("body", "")).strip(),
                    acceptance_criteria=AcceptanceCriteria(items=criteria_items),
                    constraints=str(data.get("constraints", "")).strip(),
                    testing_expectations=str(
                        data.get("testing_expectations", "")
                    ).strip(),
                )
            except Exception:
                pass

        # Fallback: treat entire canvas as body with no structured fields
        return Specification(
            title="Untitled Feature",
            body=canvas_text,
            acceptance_criteria=AcceptanceCriteria(items=()),
        )

    # ------------------------------------------------------------------
    # ARGUMENTATION_DIFF sub-state (Tech-spec §3 SpecState)
    # ------------------------------------------------------------------

    def analyze_specification_gaps(self, canvas_text: str, on_token: Callable[[str], None] | None = None) -> tuple[SemanticGap, ...]:
        """Identify semantic gaps in a drafted specification (FR-016).

        Returns a tuple of unresolved SemanticGap objects.
        """
        instruction = (
            "Analyze the following drafted specification for semantic gaps, "
            "missing logic, or undefined edge cases. Apply rules from the engineering profile.\n"
            "Return ONLY a JSON array of objects with a 'topic' key.\n\n"
            f"Draft:\n{canvas_text}"
        )
        ctx_bundle = self._context_service.load_context(RepositoryContext(root=Path(".")))
        prompt = self._prompt_assembler.assemble_spec_prompt(ctx_bundle, instruction)
        msg = ProviderMessage(role="user", content=prompt)
        response = self._provider.chat((msg,), on_token=on_token)

        match = re.search(r"\[.*\]", response.content, re.DOTALL)
        if match:
            try:
                gaps = json.loads(match.group(0))
                return tuple(
                    SemanticGap(topic=g["topic"])
                    for g in gaps
                    if isinstance(g, dict) and "topic" in g
                )
            except Exception:
                pass
        return ()

    def run_socratic_loop(
        self,
        canvas_text: str,
        argumentation_log: ArgumentationLogPort,
        ui: UiPort,
    ) -> tuple[Specification, tuple[SemanticGap, ...]]:
        """Iterative Socratic Q&A loop to resolve specification gaps (FR-016).

        For each gap identified in the spec, the agent generates a targeted
        question. The question is presented to the user via the UI port.
        The question and the user's answer are then recorded in the
        ArgumentationLog for later consumption by BayesianUpdater.

        Returns the concretized Specification and any remaining unresolved gaps.
        """
        # Step 1 & 2: Concretize canvas and identify gaps
        ui.show_loading("Concretizing specification...")
        try:
            spec = self.concretize(canvas_text, on_token=ui.stream_token)
            gaps = self.analyze_specification_gaps(spec.body or canvas_text, on_token=ui.stream_token)
        finally:
            ui.hide_loading()

        if not gaps:
            return spec, gaps

        # Step 3: Formulate and log bulk Socratic questions
        now = datetime.now(UTC).isoformat()
        ui.show_loading("Formulating clarifying questions...")
        try:
            questions = self._formulate_bulk_questions(gaps, spec, on_token=ui.stream_token)
        finally:
            ui.hide_loading()

        answers = ui.show_question(questions, canvas_text)

        argumentation_log.record_entry(
            ArgumentationEntry(
                question=questions,
                answer=answers,
                timestamp=now,
                was_user_override=False,
            )
        )

        return spec, gaps

    def _formulate_bulk_questions(
        self, gaps: tuple[SemanticGap, ...], spec: Specification, on_token: Callable[[str], None] | None = None
    ) -> str:
        """Ask the model to generate a targeted clarifying question for all gaps."""
        topics = "\n".join(f"- {gap.topic}" for gap in gaps)
        instruction = (
            f"The following specification has unresolved gaps:\n{topics}\n\n"
            f"Specification title: {spec.title}\n"
            f"Specification body: {spec.body[:500]}\n\n"
            "Write a concise numbered list of clarifying questions to resolve these gaps.\n"
            "Return ONLY the questions, no preamble."
        )
        ctx_bundle = self._context_service.load_context(RepositoryContext(root=Path(".")))
        prompt = self._prompt_assembler.assemble_spec_prompt(ctx_bundle, instruction)
        msg = ProviderMessage(role="user", content=prompt)
        response = self._provider.chat((msg,), on_token=on_token)
        return response.content.strip()
