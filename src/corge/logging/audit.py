"""Audit logging — satisfies ``contracts.AuditLoggerPort``."""

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from corge.contracts import ApprovalDecision, ApprovalRequest, AuditEvent, ToolResult


class AuditLogger:
    """Concrete audit logger.  Satisfies ``contracts.AuditLoggerPort``."""

    def __init__(self, agent_dir: Path, global_dir: Path | None = None) -> None:
        self._log_path = agent_dir / "audit.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._global_log_path = global_dir / "global_audit.jsonl" if global_dir else None
        if self._global_log_path:
            self._global_log_path.parent.mkdir(parents=True, exist_ok=True)
            self._append_global(AuditEvent(kind="session_start", payload={"repo": str(agent_dir.parent)}, timestamp=self._now()))

    def _append(self, event: AuditEvent) -> None:
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event)) + "\n")

    def _append_global(self, event: AuditEvent) -> None:
        if self._global_log_path:
            with self._global_log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(event)) + "\n")

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

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
        self._append_global(event)
