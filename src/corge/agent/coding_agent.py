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
from typing import Any

from corge.contracts import (
    ApprovalDecision,
    ApprovalGatewayPort,
    ApprovalRequest,
    ContextBundle,
    ContextPort,
    GraphUpdate,
    KnowledgeGraphPort,
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
# CodingAgent
# ---------------------------------------------------------------------------


class CodingAgent:
    """Runs the 9-step execution cycle for each approved plan step."""

    def __init__(
        self,
        provider: ProviderPort,
        tool_runtime: ToolRuntimePort,
        approval_gateway: ApprovalGatewayPort,
        context_service: ContextPort,
        knowledge_graph: KnowledgeGraphPort,
    ) -> None:
        self._provider = provider
        self._tool_runtime = tool_runtime
        self._approval_gateway = approval_gateway
        self._context_service = context_service
        self._knowledge_graph = knowledge_graph

    # ------------------------------------------------------------------
    # Steps 1–9 (Tech-spec §3 §9-Step Execution Cycle)
    # ------------------------------------------------------------------

    _MAX_ACTIONS_PER_STEP = 20

    def execute_step(self, step: PlanStep, context: ContextBundle) -> None:
        """Execute a single plan step through the full 9-step cycle.

        Raises:
            ToolExecutionError: If the tool returns a failure result or if
                the model proposes an unrecognized action.
        """
        import json

        read_dedup: set[str] = set()

        for _ in range(self._MAX_ACTIONS_PER_STEP):
            if getattr(step, "completed", False):
                return

            # Step 2-3: Assemble ephemeral prompt with Markov context
            markov_text = ""
            if context.markov_context:
                markov_text = (
                    f"\nN-1 Markov Context:\n"
                    f"  Agent proposal: {context.markov_context.agent_proposal}\n"
                    f"  User correction: {context.markov_context.user_correction}\n"
                    f"  Prior trajectory: "
                    f"{context.markov_context.compressed_trajectory}"
                )

            prompt = (
                "You are a coding agent executing a precise implementation plan.\n"
                f"Current step: {step.description}\n"
                f"Step identifier: {step.identifier}\n"
                f"{markov_text}\n\n"
                "Determine the next tool action required. Respond with a JSON block:\n"
                "```json\n"
                "{\n"
                '  "done": false,\n'
                '  "actions": [\n'
                "    {\n"
                '      "action": "READ|WRITE|EDIT|BASH",\n'
                '      "target": "<path or shell command>",\n'
                '      "content": "<full file content for WRITE>",\n'
                '      "old": "<exact substring to replace for EDIT '
                '— include 3+ lines of context>",\n'
                '      "new": "<replacement substring for EDIT>"\n'
                "    }\n"
                "  ]\n"
                "}\n"
                "```\n"
                "Rules:\n"
                "- 'content' is required for WRITE.\n"
                "- 'old' and 'new' are required for EDIT. "
                "'old' must be unique in the file.\n"
                "- For BASH, 'target' is the command string.\n"
                "- For READ, request all needed files at once.\n"
                "- Set 'done': true when the step is complete."
            )

            # Step 4: Reason & action selection
            msg = ProviderMessage(role="user", content=prompt)
            response = self._provider.chat((msg,))

            match = re.search(r"```json\s*(.*?)\s*```", response.content, re.DOTALL)
            if not match:
                raise ToolExecutionError(
                    f"Model response for step {step.identifier!r} "
                    "contained no JSON block."
                )

            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError as exc:
                raise ToolExecutionError(
                    f"Malformed JSON in action block: {exc}"
                ) from exc

            actions = data.get("actions", [])

            for action_dict in actions:
                action_str = action_dict.get("action", "").lower()
                try:
                    action = ToolAction(action_str)
                except ValueError as exc:
                    raise ToolExecutionError(
                        f"Unknown action: {action_str!r}"
                    ) from exc

                target = action_dict.get("target", "")

                if action == ToolAction.READ:
                    if target in read_dedup:
                        self._context_service.update_markov_state(
                            result=(
                                f"Note: {target} was already read this step. "
                                "Its content is in your context."
                            ),
                            correction="",
                        )
                        continue
                    read_dedup.add(target)

                # Step 5: Approval gateway
                req = ApprovalRequest(
                    action=action,
                    target=target,
                    reason=step.description,
                    step_ref=step.identifier,
                )
                decision = self._approval_gateway.approve(req)
                if decision == ApprovalDecision.REJECTED:
                    raise ToolExecutionError(
                        f"Step {step.identifier!r}: action {action.value!r} "
                        f"on {target!r} was rejected."
                    )

                # Step 6: Execute tool
                result = self._dispatch(action_dict)

                # Step 7: Verify progress
                if not result.success:
                    raise ToolExecutionError(
                        f"Step {step.identifier!r}: tool {action.value!r} failed.\n"
                        f"stderr: {result.stderr}"
                    )

                # Step 8: Update Markov state for the next step's context
                self._context_service.update_markov_state(
                    result=result.output, correction=""
                )

                if action in (ToolAction.WRITE, ToolAction.EDIT):
                    self._knowledge_graph.update_graph(
                        GraphUpdate(paths=(Path(target),))
                    )

            if data.get("done"):
                return
            if not actions:
                return

        raise ToolExecutionError("Exceeded max actions per step")

    def _dispatch(self, action_dict: dict[str, Any]) -> ToolResult:
        """Route an authorized action to the appropriate ToolRuntime primitive."""
        action = ToolAction(action_dict["action"].lower())
        target = action_dict["target"]
        path = Path(target)
        if action == ToolAction.READ:
            return self._tool_runtime.read(path)
        if action == ToolAction.BASH:
            return self._tool_runtime.bash(target, Path("."))
        if action == ToolAction.WRITE:
            content = action_dict.get("content", "")
            return self._tool_runtime.write(path, content)
        if action == ToolAction.EDIT:
            old = action_dict.get("old", "")
            new = action_dict.get("new", "")
            return self._tool_runtime.edit(path, old, new)
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
