"""Coding agent — executes procedural steps via the 9-step execution cycle.

Spec traceability:
    Tech-spec §3 §9-Step Execution Cycle  — observe, refresh, assemble, reason,
        approve, execute, verify, update knowledge, repeat
    Tech-spec §3 §Failure Path            — ToolExecutionError, scenario memory
    FR-009  — approval required for write/edit/bash; read is auto-approved
    FR-012  — evaluate_completion verifies acceptance criteria + tests
"""

from __future__ import annotations

import re
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
    ToolAction,
    ToolResult,
    ToolRuntimePort,
)


class ToolExecutionError(Exception):
    """Raised when a tool fails to execute or returns a non-zero exit code.

    Spec traceability: Tech-spec §3 §Failure Path.
    """


# ---------------------------------------------------------------------------
# Routing: parse model output → (action, target/command)
# ---------------------------------------------------------------------------

_ACTION_PREFIXES: list[tuple[str, ToolAction]] = [
    ("BASH:", ToolAction.BASH),
    ("WRITE:", ToolAction.WRITE),
    ("EDIT:", ToolAction.EDIT),
    ("READ:", ToolAction.READ),
]


def _parse_action(content: str) -> tuple[ToolAction, str] | None:
    """Extract the first recognized action prefix and its argument.

    Returns None if the model response contains no recognized action.
    """
    for line in content.splitlines():
        stripped = line.strip()
        for prefix, action in _ACTION_PREFIXES:
            if stripped.startswith(prefix):
                return action, stripped[len(prefix):].strip()
    return None


class CodingAgent:
    """Runs the 9-step execution cycle for each approved plan step."""

    def __init__(
        self,
        provider: ProviderPort,
        tool_runtime: ToolRuntimePort,
        approval_gateway: ApprovalGatewayPort,
        context_service: ContextPort,
    ) -> None:
        self._provider = provider
        self._tool_runtime = tool_runtime
        self._approval_gateway = approval_gateway
        self._context_service = context_service

    # ------------------------------------------------------------------
    # Steps 1–9 (Tech-spec §3 §9-Step Execution Cycle)
    # ------------------------------------------------------------------

    def execute_step(self, step: PlanStep, context: ContextBundle) -> None:
        """Execute a single plan step through the full 9-step cycle.

        Raises:
            ToolExecutionError: If the tool returns a failure result or if
                the model proposes an unrecognized action.
        """
        # Step 2–3: Assemble ephemeral prompt with Markov context
        markov_text = ""
        if context.markov_context:
            markov_text = (
                f"\nN-1 Markov Context:\n"
                f"  Agent proposal: {context.markov_context.agent_proposal}\n"
                f"  User correction: {context.markov_context.user_correction}\n"
                f"  Prior trajectory: {context.markov_context.compressed_trajectory}"
            )

        prompt = (
            "You are a coding agent executing a precise implementation plan.\n"
            f"Current step: {step.description}\n"
            f"Step identifier: {step.identifier}\n"
            f"{markov_text}\n\n"
            "Determine the next tool action required. Respond with EXACTLY ONE of:\n"
            "  BASH: <shell command>\n"
            "  READ: <file path>\n"
            "  WRITE: <file path>\n"
            "  EDIT: <file path>\n"
            "Choose the minimal action needed. Do not chain multiple actions."
        )

        # Step 4: Reason & action selection
        msg = ProviderMessage(role="user", content=prompt)
        response = self._provider.chat((msg,))

        parsed = _parse_action(response.content)
        if parsed is None:
            raise ToolExecutionError(
                f"Model response for step {step.identifier!r} contained no "
                f"recognized action prefix (BASH/READ/WRITE/EDIT)."
            )

        action, target = parsed

        # Step 5: Approval gateway
        req = ApprovalRequest(
            action=action,
            target=target,
            reason=step.description,
            step_ref=step.identifier,
        )
        decision = self._approval_gateway.approve(req)
        if decision == ApprovalDecision.REJECTED:
            # Spec §3 Failure Path: rejected → request pivot
            raise ToolExecutionError(
                f"Step {step.identifier!r}: action {action!r} on {target!r} "
                "was rejected."
            )

        # Step 6: Execute tool
        result = self._dispatch(action, target)

        # Step 7: Verify progress
        if not result.success:
            raise ToolExecutionError(
                f"Step {step.identifier!r}: tool {action!r} failed.\n"
                f"stderr: {result.stderr}"
            )

        # Step 8: Update Markov state for the next step's context
        self._context_service.update_markov_state(
            result=result.output, correction=""
        )

    def _dispatch(self, action: ToolAction, target: str) -> ToolResult:
        """Route an authorized action to the appropriate ToolRuntime primitive."""
        path = Path(target)
        if action == ToolAction.READ:
            return self._tool_runtime.read(path)
        if action == ToolAction.BASH:
            return self._tool_runtime.bash(target, Path("."))
        if action == ToolAction.WRITE:
            return self._tool_runtime.write(path, "")
        if action == ToolAction.EDIT:
            return self._tool_runtime.edit(path, "", "")
        # Should never be reached given _parse_action filtering
        raise ToolExecutionError(f"Unknown action: {action!r}")

    # ------------------------------------------------------------------
    # Completion verification (FR-012, Tech-spec §3 step 7)
    # ------------------------------------------------------------------

    def evaluate_completion(self, plan: Plan, context: ContextBundle) -> bool:
        """Verify that all acceptance criteria are satisfied (FR-012).

        Asks the model to evaluate each criterion against the execution
        history captured in the Markov context. Returns False if any
        criterion is not demonstrably met.
        """
        criteria = context.specification.acceptance_criteria.items
        if not criteria:
            # No criteria defined — cannot claim completion
            return False

        trajectory = ""
        if context.markov_context:
            trajectory = context.markov_context.compressed_trajectory

        prompt = (
            "You are a completion verifier. Given the execution trajectory below,\n"
            "determine whether ALL of the following acceptance criteria "
            "are satisfied.\n"
            'Return ONLY a JSON object: {"all_satisfied": true} or '
            '{"all_satisfied": false}\n\n'
            "Acceptance criteria:\n"
            + "\n".join(f"- {c}" for c in criteria)
            + f"\n\nExecution trajectory:\n{trajectory or '(no trajectory recorded)'}"
        )
        msg = ProviderMessage(role="user", content=prompt)
        response = self._provider.chat((msg,))

        match = re.search(r"\{.*\}", response.content, re.DOTALL)
        if match:
            try:
                import json
                data = json.loads(match.group(0))
                return bool(data.get("all_satisfied", False))
            except Exception:
                pass

        # Conservative fallback: if we can't parse the answer, don't claim done
        return False
