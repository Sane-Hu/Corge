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
from datetime import UTC, datetime

from corge.contracts import (
    AcceptanceCriteria,
    ArgumentationEntry,
    ArgumentationLogPort,
    ProviderMessage,
    ProviderPort,
    SemanticGap,
    Specification,
)


class SpecificationAgent:
    """Manages the interactive specification wizard and semantic gaps."""

    def __init__(self, provider: ProviderPort) -> None:
        self._provider = provider

    # ------------------------------------------------------------------
    # CONCRETIZATION sub-state (Tech-spec §3 SpecState)
    # ------------------------------------------------------------------

    def concretize(self, canvas_text: str) -> Specification:
        """Compile raw canvas text into a structured Specification (FR-002).

        Prompts the model to extract the structured wizard fields:
        title, body, acceptance criteria, constraints, testing expectations.
        Returns a best-effort Specification; gaps remain for ARGUMENTATION_DIFF.
        """
        prompt = (
            "You are a strict specification compiler.\n"
            "Extract the following structured fields from the raw "
            "brainstorming text below.\n"
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
        msg = ProviderMessage(role="user", content=prompt)
        response = self._provider.chat((msg,))

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

    def analyze_specification_gaps(self, canvas_text: str) -> tuple[SemanticGap, ...]:
        """Identify semantic gaps in a drafted specification (FR-016).

        Returns a tuple of unresolved SemanticGap objects.
        """
        prompt = (
            "You are a strict system architect.\n"
            "Analyze the following drafted specification for semantic gaps, "
            "missing logic, or undefined edge cases.\n"
            "Return ONLY a JSON array of objects with a 'topic' key.\n\n"
            f"Draft:\n{canvas_text}"
        )
        msg = ProviderMessage(role="user", content=prompt)
        response = self._provider.chat((msg,))

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
    ) -> tuple[Specification, tuple[SemanticGap, ...]]:
        """Iterative Socratic Q&A loop to resolve specification gaps (FR-016).

        For each gap identified in the spec, the agent generates a targeted
        question. The question and the provided answer are both recorded in
        the ArgumentationLog for later consumption by BayesianUpdater.

        This method does NOT interact with the UI directly — it accepts the
        canvas text and the log port. The UI layer drives the Q&A by calling
        this method once per clarification session, passing the canvas text
        assembled from user answers back through the session controller.

        Returns the concretized Specification and any remaining unresolved gaps.
        """
        # Step 1: Concretize canvas into structured spec
        spec = self.concretize(canvas_text)

        # Step 2: Identify gaps in the concretized spec
        gaps = self.analyze_specification_gaps(spec.body or canvas_text)

        # Step 3: For each gap, formulate and log a Socratic question
        now = datetime.now(UTC).isoformat()
        for gap in gaps:
            question = self._formulate_question(gap.topic, spec)
            # Log the question with a placeholder answer — the UI layer
            # will surface this question to the user and record the answer
            # via record_entry() with was_user_override as appropriate.
            argumentation_log.record_entry(
                ArgumentationEntry(
                    question=question,
                    answer="",  # populated by UI when user responds
                    timestamp=now,
                    was_user_override=False,
                )
            )

        return spec, gaps

    def _formulate_question(self, topic: str, spec: Specification) -> str:
        """Ask the model to generate a targeted clarifying question for a gap."""
        prompt = (
            "You are a Socratic specification reviewer.\n"
            f"The following specification has an unresolved gap about: {topic!r}\n"
            f"Specification title: {spec.title}\n"
            f"Specification body: {spec.body[:500]}\n\n"
            "Write ONE concise clarifying question (max 2 sentences) to "
            "resolve this gap.\n"
            "Return ONLY the question, no preamble."
        )
        msg = ProviderMessage(role="user", content=prompt)
        response = self._provider.chat((msg,))
        return response.content.strip()
