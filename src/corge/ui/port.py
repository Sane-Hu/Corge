"""Textual UI boundary — satisfies ``contracts.UiPort`` protocol.

This module contains only the protocol-satisfying stub.  The concrete
CLI implementation lives in ``cli.py``.
"""

from corge.contracts import (
    ApprovalDecision,
    ApprovalRequest,
    ContextBundle,
    EngineeringProfile,
    MemoryEvent,
    Plan,
    RepositoryContext,
    Specification,
)


class UiPortStub:
    """Stub UI that raises on every call.

    Concrete implementations (e.g. ``CliUi``) override all methods.
    Kept as a reference skeleton; production code type-hints against
    ``contracts.UiPort`` protocol, not this class.
    """

    def show_spec_wizard(self) -> Specification:
        raise NotImplementedError

    def show_plan(self, plan: Plan) -> None:
        raise NotImplementedError

    def show_execution(self, context: ContextBundle) -> None:
        raise NotImplementedError

    def show_logs(self) -> None:
        raise NotImplementedError

    def request_approval(self, request: ApprovalRequest) -> ApprovalDecision:
        raise NotImplementedError

    def show_repository_analysis(self, repository_context: RepositoryContext) -> None:
        raise NotImplementedError

    def show_repository_understanding(
        self, repository_context: RepositoryContext
    ) -> None:
        raise NotImplementedError

    def show_engineering_profile(self, profile: EngineeringProfile) -> None:
        raise NotImplementedError

    def show_memory(self, events: tuple[MemoryEvent, ...]) -> None:
        raise NotImplementedError

    def show_completion_review(self, plan: Plan) -> None:
        raise NotImplementedError
