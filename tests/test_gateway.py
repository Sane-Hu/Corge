"""Unit tests for the Approval Gateway."""

from unittest.mock import Mock

from corge.approval.gateway import ApprovalGateway
from corge.contracts import (
    ApprovalDecision,
    ApprovalRequest,
    AuditLoggerPort,
    ToolAction,
    UiPort,
)


def test_approve_read_action_auto_approves() -> None:
    ui = Mock(spec=UiPort)
    audit_logger = Mock(spec=AuditLoggerPort)
    gateway = ApprovalGateway(ui=ui, audit_logger=audit_logger)
    
    request = ApprovalRequest(action=ToolAction.READ, target="file.txt", reason="test")
    decision = gateway.approve(request)
    
    assert decision == ApprovalDecision.APPROVED
    ui.request_approval.assert_not_called()
    audit_logger.record_approval.assert_called_once_with(request, ApprovalDecision.APPROVED)


def test_approve_destructive_action_delegates_to_ui() -> None:
    ui = Mock(spec=UiPort)
    ui.request_approval.return_value = ApprovalDecision.APPROVED
    audit_logger = Mock(spec=AuditLoggerPort)
    gateway = ApprovalGateway(ui=ui, audit_logger=audit_logger)
    
    request = ApprovalRequest(action=ToolAction.WRITE, target="file.txt", reason="test")
    decision = gateway.approve(request)
    
    assert decision == ApprovalDecision.APPROVED
    ui.request_approval.assert_called_once_with(request)
    audit_logger.record_approval.assert_called_once_with(request, ApprovalDecision.APPROVED)


def test_approve_destructive_action_handles_rejection() -> None:
    ui = Mock(spec=UiPort)
    ui.request_approval.return_value = ApprovalDecision.REJECTED
    audit_logger = Mock(spec=AuditLoggerPort)
    gateway = ApprovalGateway(ui=ui, audit_logger=audit_logger)
    
    request = ApprovalRequest(action=ToolAction.BASH, target="ls", reason="test")
    decision = gateway.approve(request)
    
    assert decision == ApprovalDecision.REJECTED
    ui.request_approval.assert_called_once_with(request)
    audit_logger.record_approval.assert_called_once_with(request, ApprovalDecision.REJECTED)


def test_reject_forces_rejection() -> None:
    ui = Mock(spec=UiPort)
    audit_logger = Mock(spec=AuditLoggerPort)
    gateway = ApprovalGateway(ui=ui, audit_logger=audit_logger)
    
    request = ApprovalRequest(action=ToolAction.WRITE, target="file.txt", reason="test")
    decision = gateway.reject(request)
    
    assert decision == ApprovalDecision.REJECTED
    ui.request_approval.assert_not_called()
    audit_logger.record_approval.assert_called_once_with(request, ApprovalDecision.REJECTED)
