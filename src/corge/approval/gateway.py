"""Single approval authority — satisfies ``contracts.ApprovalGatewayPort``."""

from corge.contracts import (
    ApprovalDecision,
    ApprovalRequest,
    AuditLoggerPort,
    ToolAction,
    UiPort,
)


class ApprovalGateway:
    """Concrete approval gateway.  Satisfies ``contracts.ApprovalGatewayPort``."""

    def __init__(self, ui: UiPort, audit_logger: AuditLoggerPort) -> None:
        self._ui = ui
        self._audit_logger = audit_logger

    def approve(self, request: ApprovalRequest) -> ApprovalDecision:
        if request.action == ToolAction.READ:
            decision = ApprovalDecision.APPROVED
        else:
            decision = self._ui.request_approval(request)
        
        self._audit_logger.record_approval(request, decision)
        return decision

    def reject(self, request: ApprovalRequest) -> ApprovalDecision:
        decision = ApprovalDecision.REJECTED
        self._audit_logger.record_approval(request, decision)
        return decision
