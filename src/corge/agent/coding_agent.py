"""Coding agent — executes procedural steps."""

from pathlib import Path

from corge.contracts import (
    ApprovalDecision,
    ApprovalGatewayPort,
    ApprovalRequest,
    ContextBundle,
    ContextPort,
    Plan,
    PlanStep,
    ProviderMessage,
    ProviderPort,
    ToolRuntimePort,
)


class ToolExecutionError(Exception):
    """Raised when a tool fails to execute or returns a non-zero exit code."""


class CodingAgent:
    """Runs the execution cycle using tool context bundles."""
    
    def __init__(
        self,
        provider: ProviderPort,
        tool_runtime: ToolRuntimePort,
        approval_gateway: ApprovalGatewayPort,
        context_service: ContextPort,
    ) -> None:
        self.provider = provider
        self.tool_runtime = tool_runtime
        self.approval_gateway = approval_gateway
        self.context_service = context_service

    def execute_step(self, step: PlanStep, context: ContextBundle) -> None:
        markov_text = ""
        if context.markov_context:
            markov_text = f"N-1 Markov Context: {context.markov_context.agent_proposal}"
            
        prompt = (
            "You are a coding agent.\n"
            f"Execute step: {step.description}\n"
            f"{markov_text}\n"
            "Return a bash command to run prefixed with BASH:"
        )
        msg = ProviderMessage(role="user", content=prompt)
        response = self.provider.chat((msg,))
        
        for line in response.content.split("\n"):
            if line.strip().startswith("BASH:"):
                cmd = line.replace("BASH:", "").strip()
                req = ApprovalRequest(action=ToolAction.BASH, target=cmd, reason=step.description)
                
                if self.approval_gateway.approve(req) == ApprovalDecision.APPROVED:
                    result = self.tool_runtime.bash(cmd, Path("."))
                    
                    if hasattr(self.context_service, "update_markov_state"):
                        self.context_service.update_markov_state(  # type: ignore[attr-defined]
                            result=result.output, correction=""
                        )
                break

    def evaluate_completion(self, plan: Plan, context: ContextBundle) -> bool:
        return True
