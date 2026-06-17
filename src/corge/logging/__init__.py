"""Audit logging layer."""

from corge.contracts import AuditLoggerPort
from corge.logging.audit import AuditLogger

__all__ = ["AuditLoggerPort", "AuditLogger"]
