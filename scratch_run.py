# Save this as `scratch_run.py` in your project root
from pathlib import Path

from corge.contracts import (
    ApprovalRequest,
    ContextBundle,
    EngineeringProfile,
    MemoryEvent,
    Plan,
    PlanStep,
    RepositoryContext,
    Specification,
)
from corge.ui.cli import CliUi

def main():
    ui = CliUi()
    
    # 1. Show the spec wizard (Prompts you for input)
    print("\n--- Testing show_spec_wizard ---")
    spec = ui.show_spec_wizard()
    print(f"\nCreated Specification: {spec.title}")
    
    # 2. Show a dummy plan
    print("\n--- Testing show_plan ---")
    plan = Plan(steps=(
        PlanStep(identifier="step-1", description="Create service layer"),
        PlanStep(identifier="step-2", description="Update controller"),
    ))
    ui.show_plan(plan)
    
    # 3. Test approval request
    print("\n--- Testing request_approval ---")
    req = ApprovalRequest(action="write", target="app/Service.py", reason="Step 1 of plan")
    decision = ui.request_approval(req)
    print(f"You decided to: {decision}")
    
    # 4. Show repository understanding
    print("\n--- Testing show_repository_understanding ---")
    repo_ctx = RepositoryContext(root=Path("/projects/my-app"))
    ui.show_repository_understanding(repo_ctx)

if __name__ == "__main__":
    main()
