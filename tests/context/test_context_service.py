"""Tests for ContextService."""

import pathlib
from unittest.mock import MagicMock

from corge.context.service import ContextService
from corge.contracts import (
    AcceptanceCriteria,
    GraphResult,
    PlanStep,
    RepositoryContext,
    Specification,
)


def _make_context_service(root: pathlib.Path | None = None) -> ContextService:
    """Return a ContextService with mocked ports that return safe empty data."""
    if root is None:
        root = pathlib.Path(".")
    kg = MagicMock()
    # query_graph returns an empty GraphResult by default
    kg.query_graph.return_value = GraphResult(nodes=())

    memory = MagicMock()
    # get_facts and get_scenario return empty lists by default
    memory.get_facts.return_value = []
    memory.get_scenario.return_value = []

    return ContextService(knowledge_graph=kg, memory_store=memory, root=root)


def test_load_context_strips_layer_1() -> None:
    svc = _make_context_service()
    repo_ctx = RepositoryContext(root=pathlib.Path("."))

    # Layer 1 argumentation history must never appear in a coding bundle
    bundle = svc.load_context(repo_ctx)
    assert not getattr(bundle, "argumentation_log", None)


def test_retrieve_uses_injected_root(tmp_path: pathlib.Path) -> None:
    svc = _make_context_service(root=tmp_path)
    spec = Specification(
        title="test", body="test", acceptance_criteria=AcceptanceCriteria(())
    )
    step = PlanStep(identifier="step-1", description="test")
    bundle = svc.retrieve_relevant_context(spec, step)
    assert bundle.repository_context.root == tmp_path


def test_retrieve_relevant_context_markov_chaining() -> None:
    svc = _make_context_service()

    # Establish N-1 state
    svc.update_markov_state(
        result="Created database module",
        correction="Actually, use SQLite instead of Postgres",
    )

    spec = Specification(
        title="test", body="test", acceptance_criteria=AcceptanceCriteria(())
    )
    step = PlanStep(identifier="step-2", description="test")

    bundle = svc.retrieve_relevant_context(spec, step)

    assert bundle.markov_context is not None
    assert bundle.markov_context.tool_result == "Created database module"
    assert (
        bundle.markov_context.user_correction
        == "Actually, use SQLite instead of Postgres"
    )
    assert "Created database module" in bundle.markov_context.compressed_trajectory

    # Second call: N-2 gets compressed, N-1 updates
    svc.update_markov_state(result="Fixed SQLite import", correction="")
    bundle2 = svc.retrieve_relevant_context(spec, step)

    assert "Created database module" in bundle2.markov_context.compressed_trajectory
    assert bundle2.markov_context.tool_result == "Fixed SQLite import"


def test_context_service_query_caching() -> None:
    kg = MagicMock()
    kg.query_graph.return_value = GraphResult(nodes=())
    memory = MagicMock()
    memory.get_facts.return_value = ["fact1"]
    memory.get_profile.return_value = MagicMock()

    svc = ContextService(knowledge_graph=kg, memory_store=memory, root=pathlib.Path("."))
    spec = Specification(title="test", body="test", acceptance_criteria=AcceptanceCriteria(()))
    step = PlanStep(identifier="step-1", description="test")

    # First call hydrates the cache
    svc.retrieve_relevant_context(spec, step, rotate=True)
    assert kg.query_graph.call_count == 1
    assert memory.get_facts.call_count == 1
    assert memory.get_profile.call_count == 1

    # Second call with rotate=False retrieves from cache (no extra DB calls)
    svc.retrieve_relevant_context(spec, step, rotate=False)
    assert kg.query_graph.call_count == 1
    assert memory.get_facts.call_count == 1
    assert memory.get_profile.call_count == 1

    # Updating markov state clears cache
    svc.update_markov_state("done")
    svc.retrieve_relevant_context(spec, step, rotate=False)
    assert kg.query_graph.call_count == 2
    assert memory.get_facts.call_count == 2
    assert memory.get_profile.call_count == 2


def test_context_service_spec_isolation() -> None:
    kg = MagicMock()
    memory = MagicMock()
    memory.get_facts.return_value = ["secret_repo_fact"]
    memory.get_profile.return_value = MagicMock()

    svc = ContextService(knowledge_graph=kg, memory_store=memory, root=pathlib.Path("."))
    repo_ctx = RepositoryContext(root=pathlib.Path("."))

    bundle = svc.load_context(repo_ctx)
    # Repo facts and files are now available during SPECIFICATION phase
    assert len(bundle.engineering_facts) == 1
    assert bundle.engineering_facts[0] == "secret_repo_fact"


def test_context_service_argumentation_log(tmp_path: pathlib.Path) -> None:
    # Create a dummy argumentation log JSON
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()
    log_file = agent_dir / "argumentation_log.json"
    import json
    log_file.write_text(json.dumps({
        "entries": [
            {"question": "Q1", "answer": "A1", "timestamp": "now", "was_user_override": False}
        ],
        "snapshots": []
    }), encoding="utf-8")

    svc = ContextService(knowledge_graph=MagicMock(), memory_store=MagicMock(), root=tmp_path)
    repo_ctx = RepositoryContext(root=tmp_path)

    bundle = svc.load_context(repo_ctx)
    assert len(bundle.argumentation_entries) == 1
    assert bundle.argumentation_entries[0].question == "Q1"
    assert bundle.argumentation_entries[0].answer == "A1"
