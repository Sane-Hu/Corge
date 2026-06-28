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
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from corge.contracts import (
    AcceptanceCriteria,
    ArgumentationEntry,
    ArgumentationLogPort,
    ContextPort,
    MasterPhase,
    PromptAssemblerPort,
    ProviderMessage,
    ProviderPort,
    RepositoryContext,
    SemanticGap,
    Specification,
    SpecState,
    UiPort,
)


class SpecificationAgent:
    """Manages the interactive specification wizard and semantic gaps."""

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

    # ------------------------------------------------------------------
    # CONCRETIZATION sub-state (Tech-spec §3 SpecState)
    # ------------------------------------------------------------------

    def concretize(
        self, canvas_text: str, on_token: Callable[[str], None] | None = None
    ) -> Specification:
        """Compile raw canvas text into a structured Specification (FR-002).

        Prompts the model to extract the structured wizard fields:
        title, body, acceptance criteria, constraints, testing expectations.
        Returns a best-effort Specification; gaps remain for ARGUMENTATION_DIFF.
        """
        if self._controller:
            if self._controller.phase != MasterPhase.SPECIFICATION:
                raise ValueError("SpecificationAgent operations are only allowed in SPECIFICATION phase.")
            self._controller.advance_spec_state(SpecState.CONCRETIZATION)

        instruction = (
            "Extract the following structured fields from the raw "
            "brainstorming text below. Ensure you respect the engineering profile and repository scope from <relevant_files>.\n"
            "Return ONLY a JSON object with these exact keys:\n"
            '  "title": string — the main business goal (one sentence)\n'
            '  "body": string — narrative of user stories and functional requirements\n'
            '  "acceptance_criteria": list of strings — verifiable pass/fail criteria\n'
            '  "constraints": string — technical or business constraints\n'
            '  "testing_expectations": string — what tests are required\n\n'
            "Guidelines for Speed & Cost Efficiency:\n"
            "- Scope Minimization: Focus ONLY on the immediate user request. Do not extrapolate or add 'nice-to-have' requirements.\n"
            "- Direct Acceptance Criteria: Keep acceptance criteria concise and highly testable.\n"
            "- Workspace vs. Output: The user input comes from a UI screen called the 'canvas'. Do not refer to the target outputs "
            "as 'canvas_draft.py' or 'canvas' unless the user explicitly named them so. The title and body should describe the requested "
            "feature, not the UI workspace.\n\n"
            "If a field cannot be determined from the text, use an empty "
            "string or empty list.\n\n"
            f"<brainstorming_text>\n{canvas_text}\n</brainstorming_text>"
        )
        ctx_bundle = self._context_service.load_context(
            RepositoryContext(root=Path("."))
        )
        prompt = self._prompt_assembler.assemble_spec_prompt(ctx_bundle, instruction)
        msg = ProviderMessage(role="user", content=prompt)
        response = self._provider.chat((msg,), on_token=on_token)

        start_idx = response.content.find("{")
        if start_idx != -1:
            try:
                data, _ = json.JSONDecoder().raw_decode(response.content[start_idx:])
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

    def analyze_specification_gaps(
        self, canvas_text: str, on_token: Callable[[str], None] | None = None
    ) -> tuple[SemanticGap, ...]:
        """Identify semantic gaps in a drafted specification (FR-016).

        Returns a tuple of unresolved SemanticGap objects.
        """
        if self._controller:
            if self._controller.phase != MasterPhase.SPECIFICATION:
                raise ValueError("SpecificationAgent operations are only allowed in SPECIFICATION phase.")

        instruction = (
            "Analyze the following drafted specification for critical semantic gaps or missing logic "
            "that would prevent basic implementation within the current repository scope.\n"
            "Review the existing architecture via <relevant_files> and <repository_facts> to ensure the draft integrates logically.\n"
            "CRITICAL LIFECYCLE BOUNDARY:\n"
            "- You are currently operating in the SPECIFICATION phase. Your ONLY responsibility is to identify missing BUSINESS LOGIC or missing ACCEPTANCE CRITERIA.\n"
            "- The subsequent PLANNING phase is responsible for deciding ALL implementation details, architectural choices, file naming, and whether to modify or create files.\n"
            "- The user input originates from a UI workspace called the 'canvas'. This is just an input screen. Do NOT assume it means modifying 'canvas_draft.py'.\n"
            "- DO NOT generate any semantic gaps for implementation-level ambiguities (e.g., file names, punctuation/string differences, code structure, new file vs. existing file). Assume the Planning Agent will make sensible choices for those.\n"
            "- You MUST return an empty array `[]` if the specification is a simple, self-contained task that lacks no business logic. Do NOT invent implementation gaps just to be thorough.\n"
            "Return ONLY a JSON array of objects with a 'topic' key, or `[]` if there are no missing business logic gaps.\n\n"
            f"<draft_text>\n{canvas_text}\n</draft_text>"
        )
        ctx_bundle = self._context_service.load_context(
            RepositoryContext(root=Path("."))
        )
        prompt = self._prompt_assembler.assemble_spec_prompt(ctx_bundle, instruction)
        msg = ProviderMessage(role="user", content=prompt)
        response = self._provider.chat((msg,), on_token=on_token)

        start_idx = response.content.find("[")
        if start_idx != -1:
            try:
                gaps, _ = json.JSONDecoder().raw_decode(response.content[start_idx:])
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
        max_questions: int = 3,
    ) -> tuple[Specification, tuple[SemanticGap, ...]]:
        """Iterative Socratic Q&A loop to resolve specification gaps (FR-016).

        For each gap identified in the spec, the agent generates a targeted
        question. The question is presented to the user via the UI port.
        The question and the user's answer are then recorded in the
        ArgumentationLog for later consumption by BayesianUpdater.

        Returns the concretized Specification and any remaining unresolved gaps.
        """
        if self._controller:
            if self._controller.phase != MasterPhase.SPECIFICATION:
                raise ValueError("SpecificationAgent operations are only allowed in SPECIFICATION phase.")

        # Step 1 & 2: Concretize canvas and identify gaps
        ui.show_loading("Concretizing specification...")
        try:
            spec = self.concretize(canvas_text, on_token=ui.stream_token)
            gaps = self.analyze_specification_gaps(
                spec.body or canvas_text, on_token=ui.stream_token
            )
        finally:
            ui.hide_loading()

        while gaps:
            if self._controller:
                self._controller.advance_spec_state(SpecState.ARGUMENTATION_DIFF)
            # Enforce max_questions cap
            gaps_to_ask = gaps[:max_questions]
            remaining_gaps_count = len(gaps) - len(gaps_to_ask)

            # UX-002: Make Socratic questions opt-in rather than mandatory
            prompt_msg = (
                f"The agent detected {len(gaps)} potential semantic gap(s) in your specification.\n\n"
                f"Would you like to run the Socratic Spec Wizard to answer clarifying questions for the top {len(gaps_to_ask)} gap(s)?"
            )
            if remaining_gaps_count > 0:
                prompt_msg += f" (The remaining {remaining_gaps_count} gap(s) will be refined manually later.)"
            prompt_msg += "\n\n(Select 'No' to skip and proceed directly to manual refinement.)"

            opt_in = ui.show_confirm(
                "Socratic Spec Wizard",
                prompt_msg
            )
            if not opt_in:
                now = datetime.now(UTC).isoformat()
                topics = ", ".join(gap.topic for gap in gaps_to_ask)
                argumentation_log.record_entry(
                    ArgumentationEntry(
                        question=f"Socratic Spec Wizard for gaps: {topics}",
                        answer="Skipped/Opted out",
                        timestamp=now,
                        was_user_override=True,
                    )
                )
                break

            # Step 3: Formulate and log bulk Socratic questions
            now = datetime.now(UTC).isoformat()
            ui.show_loading("Formulating clarifying questions...")
            try:
                questions = self._formulate_bulk_questions(
                    gaps_to_ask, spec, on_token=ui.stream_token
                )
            finally:
                ui.hide_loading()

            answers = ui.show_question(questions, canvas_text)

            is_skipped = not answers.strip() or "<Enter answer here>" in answers
            argumentation_log.record_entry(
                ArgumentationEntry(
                    question=questions,
                    answer=answers,
                    timestamp=now,
                    was_user_override=is_skipped,
                )
            )

            if answers.strip():
                ui.show_loading("Refining specification with answers...")
                try:
                    spec = self.refine_spec_with_answers(
                        spec, questions, answers, on_token=ui.stream_token
                    )
                    gaps = self.analyze_specification_gaps(
                        spec.body, on_token=ui.stream_token
                    )
                finally:
                    ui.hide_loading()
            else:
                break

        return spec, gaps

    def format_spec_to_text(
        self, spec: Specification, gaps: tuple[SemanticGap, ...]
    ) -> str:
        """Format a Specification and unresolved gaps into a clean markdown template for manual editing."""
        lines = []
        lines.append(f"# Title: {spec.title}")
        lines.append("")
        lines.append("# Requirements & User Stories")
        lines.append(spec.body)
        lines.append("")
        if spec.constraints:
            lines.append("# Constraints")
            lines.append(spec.constraints)
            lines.append("")
        if spec.testing_expectations:
            lines.append("# Testing Expectations")
            lines.append(spec.testing_expectations)
            lines.append("")
        if spec.acceptance_criteria.items:
            lines.append("# Acceptance Criteria")
            for item in spec.acceptance_criteria.items:
                lines.append(f"- {item}")
            lines.append("")
        if gaps:
            lines.append("=== UNRESOLVED SEMANTIC GAPS ===")
            lines.append("Please resolve the following gaps by editing the text below:")
            lines.append("")
            for gap in gaps:
                lines.append(f"[GAP: {gap.topic}]")
                lines.append("Resolution: <Enter details here>")
                lines.append("")
        return "\n".join(lines)

    def merge_templated_responses(
        self,
        spec: Specification,
        edited_text: str,
        on_token: Callable[[str], None] | None = None,
    ) -> Specification:
        """Merge inline manual gap responses back into structured specification fields."""
        if self._controller:
            if self._controller.phase != MasterPhase.SPECIFICATION:
                raise ValueError("SpecificationAgent operations are only allowed in SPECIFICATION phase.")
            self._controller.advance_spec_state(SpecState.SPEC_METASTABLE)

        instruction = (
            "You are finalizing a structured specification. The user has filled in inline gap resolution templates "
            "and possibly edited the specification text. Merge their edits and any filled-in gap sections back into "
            "the structured specification fields.\n"
            "Do NOT include the '=== UNRESOLVED SEMANTIC GAPS ===' section header, instructions, or any raw '[GAP: ...]' "
            "or 'Resolution: ...' lines in the finalized fields (especially 'body'). Instead, integrate their details "
            "cleanly into the requirements narrative.\n"
            "Return ONLY a JSON object with these exact keys:\n"
            '  "title": string — finalized business goal\n'
            '  "body": string — finalized narrative of user stories and requirements\n'
            '  "acceptance_criteria": list of strings — finalized verifiable criteria\n'
            '  "constraints": string — finalized constraints\n'
            '  "testing_expectations": string — finalized testing expectations\n\n'
            f"<original_specification>\n"
            f"Original Title: {spec.title}\n"
            f"Original Constraints: {spec.constraints}\n"
            f"Original Testing Expectations: {spec.testing_expectations}\n"
            f"</original_specification>\n\n"
            f"<user_edited_text>\n{edited_text}\n</user_edited_text>"
        )
        ctx_bundle = self._context_service.load_context(
            RepositoryContext(root=Path("."))
        )
        prompt = self._prompt_assembler.assemble_spec_prompt(ctx_bundle, instruction)
        msg = ProviderMessage(role="user", content=prompt)
        response = self._provider.chat((msg,), on_token=on_token)

        start_idx = response.content.find("{")
        if start_idx != -1:
            try:
                data, _ = json.JSONDecoder().raw_decode(response.content[start_idx:])
                criteria_items = tuple(
                    str(c) for c in data.get("acceptance_criteria", [])
                )
                body = str(data.get("body", spec.body)).strip()
                if "=== UNRESOLVED SEMANTIC GAPS ===" in body:
                    body = body.split("=== UNRESOLVED SEMANTIC GAPS ===")[0].strip()
                import re
                body = re.sub(r"\[GAP: [^\]]+\]", "", body)
                body = re.sub(r"Resolution:.*", "", body)
                body = re.sub(r"\n{3,}", "\n\n", body).strip()

                return Specification(
                    title=str(data.get("title", spec.title)).strip(),
                    body=body,
                    acceptance_criteria=AcceptanceCriteria(items=criteria_items),
                    constraints=str(data.get("constraints", spec.constraints)).strip(),
                    testing_expectations=str(
                        data.get("testing_expectations", spec.testing_expectations)
                    ).strip(),
                )
            except Exception:
                pass

        body = edited_text
        if "=== UNRESOLVED SEMANTIC GAPS ===" in body:
            body = body.split("=== UNRESOLVED SEMANTIC GAPS ===")[0].strip()
        import re
        body = re.sub(r"\[GAP: [^\]]+\]", "", body)
        body = re.sub(r"Resolution:.*", "", body)
        body = re.sub(r"\n{3,}", "\n\n", body).strip()

        return Specification(
            title=spec.title,
            body=body,
            acceptance_criteria=spec.acceptance_criteria,
            constraints=spec.constraints,
            testing_expectations=spec.testing_expectations,
        )

    def refine_spec_with_answers(
        self,
        spec: Specification,
        questions: str,
        answers: str,
        on_token: Callable[[str], None] | None = None,
    ) -> Specification:
        """Use the provider to refine the specification incorporating user answers."""
        if self._controller:
            if self._controller.phase != MasterPhase.SPECIFICATION:
                raise ValueError("SpecificationAgent operations are only allowed in SPECIFICATION phase.")
        instruction = (
            "You are refining a structured specification based on the user's answers to clarifying questions.\n"
            "Integrate the answers below into the specification fields.\n"
            "Return ONLY a JSON object with these exact keys:\n"
            '  "title": string — updated business goal (one sentence)\n'
            '  "body": string — updated narrative of user stories and functional requirements\n'
            '  "acceptance_criteria": list of strings — updated verifiable pass/fail criteria\n'
            '  "constraints": string — updated technical or business constraints\n'
            '  "testing_expectations": string — updated testing expectations\n\n'
            f"<original_specification>\n"
            f"Title: {spec.title}\n"
            f"Body: {spec.body}\n"
            f"Acceptance Criteria:\n" + "\n".join(f"- {c}" for c in spec.acceptance_criteria.items) + "\n"
            f"Constraints: {spec.constraints}\n"
            f"Testing Expectations: {spec.testing_expectations}\n"
            f"</original_specification>\n\n"
            f"<clarifying_questions>\n{questions}\n</clarifying_questions>\n\n"
            f"<user_answers>\n{answers}\n</user_answers>"
        )
        ctx_bundle = self._context_service.load_context(
            RepositoryContext(root=Path("."))
        )
        prompt = self._prompt_assembler.assemble_spec_prompt(ctx_bundle, instruction)
        msg = ProviderMessage(role="user", content=prompt)
        response = self._provider.chat((msg,), on_token=on_token)

        start_idx = response.content.find("{")
        if start_idx != -1:
            try:
                data, _ = json.JSONDecoder().raw_decode(response.content[start_idx:])
                criteria_items = tuple(
                    str(c) for c in data.get("acceptance_criteria", [])
                )
                return Specification(
                    title=str(data.get("title", spec.title)).strip(),
                    body=str(data.get("body", spec.body)).strip(),
                    acceptance_criteria=AcceptanceCriteria(items=criteria_items),
                    constraints=str(data.get("constraints", spec.constraints)).strip(),
                    testing_expectations=str(
                        data.get("testing_expectations", spec.testing_expectations)
                    ).strip(),
                )
            except Exception:
                pass
        return spec

    def _formulate_bulk_questions(
        self,
        gaps: tuple[SemanticGap, ...],
        spec: Specification,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        """Ask the model to generate a targeted clarifying question for all gaps."""
        if self._controller:
            if self._controller.phase != MasterPhase.SPECIFICATION:
                raise ValueError("SpecificationAgent operations are only allowed in SPECIFICATION phase.")

        topics = "\n".join(f"- {gap.topic}" for gap in gaps)
        instruction = (
            "The following specification has unresolved gaps:\n"
            f"{topics}\n\n"
            f"Specification title: {spec.title}\n"
            "<specification_body_snippet>\n"
            f"{spec.body[:500]}\n"
            "</specification_body_snippet>\n\n"
            "Write a concise numbered list of clarifying questions to resolve these gaps. "
            "Formulate the questions to be concrete and specific to the detected framework (if provided in <framework_schema>). "
            "Return ONLY the questions, no preamble."
        )
        ctx_bundle = self._context_service.load_context(
            RepositoryContext(root=Path("."))
        )
        prompt = self._prompt_assembler.assemble_spec_prompt(ctx_bundle, instruction)
        msg = ProviderMessage(role="user", content=prompt)
        response = self._provider.chat((msg,), on_token=on_token)
        return response.content.strip()
