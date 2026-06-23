coding_agent_tests = """
def test_execute_step_raises_on_rejection(coding_agent, provider, tool_runtime, tmp_path, approval_gateway):
    from corge.contracts import ChatResponse, ToolExecutionError
    provider.chat.return_value = ChatResponse(
        content='```json\\n{\\n  "actions": [\\n    {\\n      "action": "BASH",\\n      "target": "rm -rf /"\\n    }\\n  ]\\n}\\n```',
        usage={}
    )
    from corge.contracts import ApprovalDecision
    approval_gateway.request_approval.return_value = ApprovalDecision.REJECTED
    
    from corge.contracts import PlanStep
    step = PlanStep(identifier="1", description="test")
    
    import pytest
    with pytest.raises(ToolExecutionError) as exc:
        coding_agent.execute_step(step)
    assert "rejected" in str(exc.value).lower()

def test_evaluate_completion_returns_true_on_satisfied_criteria(coding_agent, provider):
    from corge.contracts import ChatResponse, PlanStep, Specification, AcceptanceCriteria
    provider.chat.return_value = ChatResponse(
        content='```json\\n{"all_satisfied": true}\\n```',
        usage={}
    )
    step = PlanStep(identifier="1", description="test")
    spec = Specification(title="t", body="b", acceptance_criteria=AcceptanceCriteria(()))
    res = coding_agent.evaluate_completion(step, spec)
    assert res is True

def test_evaluate_completion_returns_false_on_malformed_json(coding_agent, provider):
    from corge.contracts import ChatResponse, PlanStep, Specification, AcceptanceCriteria
    provider.chat.return_value = ChatResponse(content='Not JSON', usage={})
    step = PlanStep(identifier="1", description="test")
    spec = Specification(title="t", body="b", acceptance_criteria=AcceptanceCriteria(()))
    res = coding_agent.evaluate_completion(step, spec)
    assert res is False
"""

with open("tests/agent/test_coding_agent.py", "a") as f:
    f.write(coding_agent_tests)

context_service_tests = """
def test_trajectory_compressed_after_limit() -> None:
    svc = _make_context_service()
    spec = Specification(title="t", body="b", acceptance_criteria=AcceptanceCriteria(()))
    step = PlanStep(identifier="s", description="d")
    
    for i in range(6):
        svc.update_markov_state(result=f"res {i}", correction="")
    
    bundle = svc.retrieve_relevant_context(spec, step)
    assert bundle.markov_context is not None
    assert bundle.markov_context.compressed_trajectory != ""
    assert "res 0" in bundle.markov_context.compressed_trajectory

def test_trajectory_truncated_at_limit() -> None:
    svc = _make_context_service()
    for i in range(15):
        svc.update_markov_state(result=f"res {i}", correction="")
    
    assert len(svc._history) <= 10  # Because _COMPRESSED_HISTORY_LIMIT is 10
"""

with open("tests/context/test_context_service.py", "a") as f:
    f.write(context_service_tests)
