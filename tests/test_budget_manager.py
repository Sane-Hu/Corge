from corge.budget_manager.manager import BudgetManager
from corge.contracts import (
    AcceptanceCriteria,
    ContextBundle,
    EngineeringProfile,
    Plan,
    Specification,
)


def test_budget_manager():
    bm = BudgetManager()
    
    spec = Specification(
        title="Test Title",
        body="This is a test body.",
        acceptance_criteria=AcceptanceCriteria(items=("Item 1", "Item 2")),
    )
    plan = Plan(steps=())
    profile = EngineeringProfile(rules=("Rule 1", "Rule 2"))
    
    context = ContextBundle(
        specification=spec,
        plan=plan,
        repository_context=None,
        engineering_profile=profile,
        scenario_memory=(),
        engineering_facts=("Fact 1", "Fact 1", "Fact 2"),
        recent_actions=("Action 1", "Action 2", "Action 1"),
    )
    
    # Test estimate
    tokens = bm.estimate_tokens(context)
    assert tokens > 0, "Estimate should be > 0"
    
    # Test deduplicate
    deduped = bm.deduplicate(context)
    assert len(deduped.engineering_facts) == 2, "Should deduplicate facts"
    assert len(deduped.recent_actions) == 2, "Should deduplicate recent_actions"
    
    # Test clip (with a very small limit to force clipping)
    clipped = bm.clip(context, token_limit=0)
    assert clipped is not None
    # The output of clipped logic depends on how it's implemented.
    # Currently it limits to the last 10, but we will test it after modification.
    
    assert bm.summarize(context) is not None
