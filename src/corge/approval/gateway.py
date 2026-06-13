"""Single approval authority boundary."""

from corge.contracts import ApprovalDecision, ApprovalRequest


class ApprovalGateway:
    """Approval responsibilities from docs/04-module-contracts.md."""

    def approve(self, request: ApprovalRequest) -> ApprovalDecision:
        raise NotImplementedError

    def reject(self, request: ApprovalRequest) -> ApprovalDecision:
        raise NotImplementedError

