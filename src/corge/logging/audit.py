"""Audit logging boundaries."""

from corge.contracts import ApprovalDecision, ApprovalRequest, AuditEvent, ToolResult


class AuditLogger:
    """Logging responsibilities from docs/04-module-contracts.md."""

    def record_prompt(self, prompt: str) -> None:
        raise NotImplementedError

    def record_tool_call(self, result: ToolResult) -> None:
        raise NotImplementedError

    def record_approval(
        self, request: ApprovalRequest, decision: ApprovalDecision
    ) -> None:
        raise NotImplementedError

    def record_completion(self, event: AuditEvent) -> None:
        raise NotImplementedError

