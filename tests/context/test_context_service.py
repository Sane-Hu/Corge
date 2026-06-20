"""Tests for ContextService."""

import pathlib

from corge.context.service import ContextService
from corge.contracts import PlanStep, RepositoryContext, Specification


def test_load_context_strips_layer_1():
    svc = ContextService()
    repo_ctx = RepositoryContext(root=pathlib.Path("."))
    
    # Layer 1 argumentation history is NOT requested or loaded
    bundle = svc.load_context(repo_ctx)
    assert not getattr(bundle, "argumentation_log", None)
    
def test_retrieve_relevant_context_markov_chaining():
    svc = ContextService()
    
    # Setup N-1 state
    svc.update_markov_state(result="Created database module", correction="Actually, use SQLite instead of Postgres")
    
    from corge.contracts import AcceptanceCriteria
    spec = Specification(title="test", body="test", acceptance_criteria=AcceptanceCriteria(()))
    step = PlanStep(identifier="step-2", description="test")
    
    bundle = svc.retrieve_relevant_context(spec, step)
    
    assert bundle.markov_context is not None
    assert bundle.markov_context.agent_proposal == "Created database module"
    assert bundle.markov_context.user_correction == "Actually, use SQLite instead of Postgres"
    assert "Prev step result: Created database module" in bundle.markov_context.compressed_trajectory
    
    # Update state again to test trajectory compression
    svc.update_markov_state(result="Fixed SQLite import", correction="")
    bundle2 = svc.retrieve_relevant_context(spec, step)
    
    assert "Created database module" in bundle2.markov_context.compressed_trajectory
    assert bundle2.markov_context.agent_proposal == "Fixed SQLite import"
