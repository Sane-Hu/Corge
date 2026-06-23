"""Unit tests for the prompt_assembler module."""

from pathlib import Path

import pytest

from corge.contracts import (
    AcceptanceCriteria,
    ArtifactReference,
    ContextBundle,
    EngineeringProfile,
    MemoryEvent,
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
    def retrieve_relevant_context(self, specification: Specification, step: PlanStep) -> ContextBundle:
        return _make_bundle()
    def update_markov_state(self, result: str, correction: str = "") -> None:
        pass


def test_assemble_prompt_includes_tier1_always() -> None:
    assembler = PromptAssembler(DummyContextPort())
    bundle = _make_bundle()

    prompt = assembler.assemble_prompt(bundle)

    assert "Tier 1" in prompt
    assert "Add login endpoint" in prompt
    assert "Returns 200 on valid creds" in prompt


def test_assemble_prompt_omits_current_step_line() -> None:
    assembler = PromptAssembler(DummyContextPort())
    bundle = _make_bundle()

    prompt = assembler.assemble_prompt(bundle)

    assert "Current Plan Step" not in prompt
    assert "Create login route" not in prompt
    assert "Write tests" not in prompt


def test_assemble_prompt_handles_empty_plan() -> None:
    assembler = PromptAssembler(DummyContextPort())
    bundle = _make_bundle(plan=Plan(steps=(), specification_ref=""))

    prompt = assembler.assemble_prompt(bundle)

    assert "Current Plan Step" not in prompt
    assert "Tier 1" in prompt


def test_assemble_prompt_filters_low_confidence_rules() -> None:
    assembler = PromptAssembler(DummyContextPort())
    profile = EngineeringProfile(
        rules=("High confidence rule", "Low confidence rule"),
        confidence={"High confidence rule": 0.9, "Low confidence rule": 0.2},
    )
    bundle = _make_bundle(engineering_profile=profile)

    prompt = assembler.assemble_prompt(bundle)

    assert "High confidence rule" in prompt
    assert "Low confidence rule" not in prompt


def test_assemble_prompt_includes_tier2_when_relevant_files_present() -> None:
    assembler = PromptAssembler(DummyContextPort())
    bundle = _make_bundle(relevant_files=("src/services/auth_service.py",))

    prompt = assembler.assemble_prompt(bundle)

    assert "Tier 2" in prompt
    assert "src/services/auth_service.py" in prompt


def test_assemble_prompt_omits_tier2_when_no_relevant_files() -> None:
    assembler = PromptAssembler(DummyContextPort())
    bundle = _make_bundle()

    prompt = assembler.assemble_prompt(bundle)

    assert "Tier 2" not in prompt


def test_assemble_prompt_includes_tier3_when_scenario_memory_present() -> None:
    assembler = PromptAssembler(DummyContextPort())
    event = MemoryEvent(kind="blocker", payload={"detail": "AuthService not found"})
    bundle = _make_bundle(scenario_memory=(event,))

    prompt = assembler.assemble_prompt(bundle)

    assert "Tier 3" in prompt
    assert "blocker" in prompt


def test_assemble_prompt_omits_tier3_when_no_scenario_memory() -> None:
    assembler = PromptAssembler(DummyContextPort())
    bundle = _make_bundle()

    prompt = assembler.assemble_prompt(bundle)

    assert "Tier 3" not in prompt


def test_assemble_prompt_includes_tier4_when_recent_actions_present() -> None:
    assembler = PromptAssembler(DummyContextPort())
    bundle = _make_bundle(recent_actions=("read src/services/auth_service.py",))

    prompt = assembler.assemble_prompt(bundle)

    assert "Tier 4" in prompt
    assert "read src/services/auth_service.py" in prompt


def test_assemble_prompt_includes_tier5_when_artifacts_present() -> None:
    assembler = PromptAssembler(DummyContextPort())
    ref = ArtifactReference(uri="artifact://abc123", summary="Full test log, 400 lines")
    bundle = _make_bundle(artifact_refs=(ref,))

    prompt = assembler.assemble_prompt(bundle)

    assert "Tier 5" in prompt
    assert "artifact://abc123" in prompt
    assert "Full test log, 400 lines" in prompt


def test_assemble_prompt_tier_order() -> None:
    assembler = PromptAssembler(DummyContextPort())
    bundle = _make_bundle(
        relevant_files=("src/file.py",),
        scenario_memory=(MemoryEvent(kind="discovery", payload={}),),
        recent_actions=("did something",),
        artifact_refs=(ArtifactReference(uri="artifact://x", summary="s"),),
    )

    prompt = assembler.assemble_prompt(bundle)

    tier1_pos = prompt.index("Tier 1")
    tier2_pos = prompt.index("Tier 2")
    tier3_pos = prompt.index("Tier 3")
    tier4_pos = prompt.index("Tier 4")
    tier5_pos = prompt.index("Tier 5")

    assert tier1_pos < tier2_pos < tier3_pos < tier4_pos < tier5_pos


def test_collect_context_delegates() -> None:
    assembler = PromptAssembler(DummyContextPort())
    step = PlanStep(identifier="1", description="Create login route")
    spec = _make_spec()

    bundle = assembler.collect_context(step, spec)
    assert bundle is not None


def test_assemble_prompt_includes_current_step_when_id_matches() -> None:
    assembler = PromptAssembler(DummyContextPort())
    bundle = _make_bundle(current_step_id="1")

    prompt = assembler.assemble_prompt(bundle)

    assert "Current Plan Step: 1 — Create login route" in prompt
    assert "Action: write Target: src/routes/login.py" in prompt


def test_assemble_prompt_includes_engineering_facts() -> None:
    assembler = PromptAssembler(DummyContextPort())
    bundle = _make_bundle(engineering_facts=("Always use strict typing", "No external calls in unit tests"))

    prompt = assembler.assemble_prompt(bundle)

    assert "Tier 2" in prompt
    assert "Always use strict typing" in prompt
    assert "No external calls in unit tests" in prompt