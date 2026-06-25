"""Unit tests for the prompt_assembler module."""

from pathlib import Path

from corge.contracts import (
    AcceptanceCriteria,
    ContextBundle,
    EngineeringProfile,
    Plan,
    PlanStep,
    RepositoryContext,
    Specification,
    ToolAction,
)
from corge.prompt_assembler import PromptAssembler


def _make_spec(**overrides: object) -> Specification:
    defaults: dict[str, object] = {
        "title": "Add login endpoint",
        "body": "Implement POST /login with JWT response.",
        "acceptance_criteria": AcceptanceCriteria(
            items=("Returns 200 on valid creds", "Returns 401 on invalid creds")
        ),
    }
    defaults.update(overrides)
    return Specification(**defaults)  # type: ignore[arg-type]


def _make_plan() -> Plan:
    step1 = PlanStep(
        identifier="1",
        description="Create login route",
        action=ToolAction.WRITE,
        target="src/routes/login.py",
    )
    step2 = PlanStep(
        identifier="2",
        description="Write tests",
        action=ToolAction.WRITE,
        target="tests/test_login.py",
    )
    return Plan(steps=(step1, step2), specification_ref="Add login endpoint")


def _make_bundle(**overrides: object) -> ContextBundle:
    defaults: dict[str, object] = {
        "specification": _make_spec(),
        "plan": _make_plan(),
        "repository_context": RepositoryContext(root=Path("/tmp/repo")),
        "engineering_profile": EngineeringProfile(),
    }
    defaults.update(overrides)
    return ContextBundle(**defaults)  # type: ignore[arg-type]


class DummyContextPort:
    def load_context(self, repository_context: RepositoryContext) -> ContextBundle:
        return _make_bundle()

    def refresh_context(self, repository_context: RepositoryContext) -> ContextBundle:
        return _make_bundle()

    def retrieve_relevant_context(
        self, specification: Specification, step: PlanStep
    ) -> ContextBundle:
        return _make_bundle()

    def update_markov_state(self, result: str, correction: str = "") -> None:
        pass


class DummySchemaTailor:
    def detect_framework(self) -> str | None:
        return None

    def fetch_schema(self, framework_id: str | None) -> dict[str, object]:
        return {}


class DummyBudgetManager:
    def estimate_tokens(self, context: ContextBundle) -> int:
        return 10

    def rank_context(self, context: ContextBundle) -> ContextBundle:
        return context

    def clip(self, context: ContextBundle, token_limit: int) -> ContextBundle:
        return context

    def deduplicate(self, context: ContextBundle) -> ContextBundle:
        return context

    def summarize(self, context: ContextBundle) -> str:
        return ""

    def compact(self, context: ContextBundle) -> ContextBundle:
        return context


def _make_assembler() -> PromptAssembler:
    return PromptAssembler(
        DummyContextPort(), DummySchemaTailor(), DummyBudgetManager()
    )


def test_assemble_coding_prompt_includes_spec() -> None:
    assembler = _make_assembler()
    bundle = _make_bundle()
    prompt = assembler.assemble_coding_prompt(bundle)
    assert "<specification>" in prompt
    assert "Add login endpoint" in prompt




def test_assemble_coding_prompt_includes_current_step() -> None:
    assembler = _make_assembler()
    bundle = _make_bundle(current_step_id="1")
    prompt = assembler.assemble_coding_prompt(bundle)
    assert "Current step: Create login route" in prompt
    assert "Step identifier: 1" in prompt


def test_assemble_coding_prompt_filters_low_confidence_rules() -> None:
    assembler = _make_assembler()
    profile = EngineeringProfile(
        rules=("High confidence rule", "Low confidence rule"),
        confidence={"High confidence rule": 0.9, "Low confidence rule": 0.2},
    )
    bundle = _make_bundle(engineering_profile=profile)
    prompt = assembler.assemble_coding_prompt(bundle)
    assert "High confidence rule" in prompt
    assert "Low confidence rule" not in prompt


def test_assemble_coding_prompt_includes_relevant_files() -> None:
    assembler = _make_assembler()
    bundle = _make_bundle(relevant_files=("src/services/auth_service.py",))
    prompt = assembler.assemble_coding_prompt(bundle)
    assert "<relevant_files>" in prompt
    assert "src/services/auth_service.py" in prompt


def test_assemble_coding_prompt_includes_engineering_facts() -> None:
    assembler = _make_assembler()
    bundle = _make_bundle(
        engineering_facts=(
            "Always use strict typing",
        )
    )
    prompt = assembler.assemble_coding_prompt(bundle)
    assert "<repository_facts>" in prompt
    assert "Always use strict typing" in prompt


def test_assemble_coding_prompt_calls_schema_tailor() -> None:
    from unittest.mock import MagicMock
    st = MagicMock(spec=DummySchemaTailor)
    st.detect_framework.return_value = "react"
    st.fetch_schema.return_value = {"key": "value"}
    assembler = PromptAssembler(DummyContextPort(), st, DummyBudgetManager())
    bundle = _make_bundle()
    prompt = assembler.assemble_coding_prompt(bundle)
    st.detect_framework.assert_called_once()
    st.fetch_schema.assert_called_once_with("react")
    assert "<framework_schema>" in prompt


def test_assemble_coding_prompt_calls_compact_when_over_budget() -> None:
    from unittest.mock import MagicMock

    from corge.prompt_assembler.assembler import _TOKEN_BUDGET
    bundle = _make_bundle()
    bm = MagicMock(spec=DummyBudgetManager)
    bm.rank_context.return_value = bundle
    bm.estimate_tokens.return_value = _TOKEN_BUDGET + 1
    bm.compact.return_value = _make_bundle()
    assembler = PromptAssembler(DummyContextPort(), DummySchemaTailor(), bm)
    assembler.assemble_coding_prompt(bundle)
    bm.rank_context.assert_called_once_with(bundle)
    bm.estimate_tokens.assert_called_once()
    bm.compact.assert_called_once_with(bundle)


def test_collect_context_delegates() -> None:
    assembler = _make_assembler()
    step = PlanStep(identifier="1", description="Create login route")
    spec = _make_spec()
    bundle = assembler.collect_context(step, spec)
    assert bundle is not None
