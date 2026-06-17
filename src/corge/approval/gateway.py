"""Single approval authority — satisfies ``contracts.ApprovalGatewayPort``."""

from corge.contracts import ApprovalDecision, ApprovalRequest


class ApprovalGateway:
    """Concrete approval gateway stub.  Satisfies ``contracts.ApprovalGatewayPort``."""

    def approve(self, request: ApprovalRequest) -> ApprovalDecision:
        raise NotImplementedError

    def reject(self, request: ApprovalRequest) -> ApprovalDecision:
        raise NotImplementedError
