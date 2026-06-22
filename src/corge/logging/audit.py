"""Audit logging — satisfies ``contracts.AuditLoggerPort``."""

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from corge.contracts import ApprovalDecision, ApprovalRequest, AuditEvent, ToolResult


class AuditLogger:
    """Concrete audit logger.  Satisfies ``contracts.AuditLoggerPort``."""

    def __init__(self, agent_dir: Path) -> None:
        self._log_path = agent_dir / "audit.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def _append(self, event: AuditEvent) -> None:
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event)) + "\n")

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def record_prompt(self, prompt: str) -> None:
        self._append(
            AuditEvent(
                kind="prompt",
                payload={"prompt": prompt},
                timestamp=self._now(),
            )
        )

    def record_tool_call(self, result: ToolResult) -> None:
        self._append(
            AuditEvent(
                kind="tool_call",
                payload=asdict(result),
                timestamp=self._now(),
            )
        )

    def record_approval(
        self, request: ApprovalRequest, decision: ApprovalDecision
    ) -> None:
        self._append(
            AuditEvent(
                kind="approval",
                payload={
                    "request": asdict(request),
                    "decision": decision.value,
                },
                timestamp=self._now(),
            )
        )

    def record_completion(self, event: AuditEvent) -> None:
        if not event.timestamp:
            event = AuditEvent(
                kind=event.kind, payload=event.payload, timestamp=self._now()
            )
        self._append(event)
