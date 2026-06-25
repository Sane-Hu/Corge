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
from typing import Any, Callable

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
    PromptAssemblerPort,
    AuditLoggerPort,
    ArtifactStorePort,
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
        prompt_assembler: PromptAssemblerPort,
        audit_logger: AuditLoggerPort,
        artifact_store: ArtifactStorePort,
    ) -> None:
        self._provider = provider
        self._tool_runtime = tool_runtime
        self._approval_gateway = approval_gateway
        self._context_service = context_service
        self._knowledge_graph = knowledge_graph
        self._prompt_assembler = prompt_assembler
        self._audit_logger = audit_logger
        self._artifact_store = artifact_store

    # ------------------------------------------------------------------
    # Steps 1–9 (Tech-spec §3 §9-Step Execution Cycle)
    # ------------------------------------------------------------------

    _MAX_ACTIONS_PER_STEP = 20

    def execute_step(
        self, step: PlanStep, context: ContextBundle, on_token: Callable[[str], None] | None = None
    ) -> None:
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

            prompt = self._prompt_assembler.assemble_coding_prompt(context)

            # Step 4: Reason & action selection
            msg = ProviderMessage(role="user", content=prompt)
            self._audit_logger.record_prompt(prompt)
            response = self._provider.chat((msg,), on_token=on_token)

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
                    raise ToolExecutionError(f"Unknown action: {action_str!r}") from exc

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
                self._audit_logger.record_tool_call(result)

                # Step 7: Verify progress
                if not result.success:
                    raise ToolExecutionError(
                        f"Step {step.identifier!r}: tool {action.value!r} failed.\n"
                        f"stderr: {result.stderr}"
                    )

                # Step 8: Update Markov state for the next step's context
                # Truncate output to prevent context window explosion or offload to artifact
                if len(result.output) > 3000:
                    try:
                        # Path structure for artifacts: use step identifier
                        artifact_path = Path(f"{step.identifier}_{action.value}.out")
                        summary = f"Truncated output from {action.value} on {target}"
                        ref = self._artifact_store.store_artifact(artifact_path, result.output)
                        safe_output = result.output[:3000] + f"\n...[output truncated, see artifact: {ref.uri}]"
                    except Exception as e:
                        safe_output = result.output[:3000] + f"\n...[output truncated, artifact store failed: {e}]"
                else:
                    safe_output = result.output

                self._context_service.update_markov_state(
                    result=safe_output, correction=""
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

    def evaluate_completion(
        self, plan: Plan, context: ContextBundle, on_token: Callable[[str], None] | None = None
    ) -> bool:
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
        response = self._provider.chat((msg,), on_token=on_token)

        match = re.search(r"\{.*\}", response.content, re.DOTALL)
        if match:
            try:
                import json

                data = json.loads(match.group(0))
                return bool(data.get("all_satisfied", False))
            except json.JSONDecodeError as exc:
                # Log JSON parsing error and return False to allow retry
                print(f"Warning: JSON decode error in evaluate_completion: {exc}")
                return False

        # Conservative fallback: if we can't parse the answer, don't claim done
        return False
