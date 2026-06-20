"""Argumentation log — satisfies ``contracts.ArgumentationLogPort``.

Spec traceability:
    Argument of Specs RD § 5 — comprehensive logging
    Resolved Design § 2      — immutable canvas snapshots, timestamping

Records Socratic Q&A exchanges and canvas snapshots to
``argumentation_log.json`` for later consumption by the heuristic updater.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from corge.contracts import ArgumentationEntry, CanvasSnapshot


class ArgumentationLog:
    """Concrete argumentation log.  Satisfies ``contracts.ArgumentationLogPort``."""

    def __init__(self, agent_dir: Path) -> None:
        self._log_path = agent_dir / "argumentation_log.json"
        self._entries: list[ArgumentationEntry] = []
        self._snapshots: list[CanvasSnapshot] = []
        self._load()

    def _load(self) -> None:
        if self._log_path.exists():
            data = json.loads(self._log_path.read_text(encoding="utf-8"))
            self._entries = [
                ArgumentationEntry(**e) for e in data.get("entries", [])
            ]
            self._snapshots = [
                CanvasSnapshot(
                    text=s["text"],
                    timestamp=s["timestamp"],
                    concretized_ranges=tuple(
                        tuple(r) for r in s.get("concretized_ranges", [])
                    ),
                )
                for s in data.get("snapshots", [])
            ]

    def _save(self) -> None:
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "entries": [asdict(e) for e in self._entries],
            "snapshots": [asdict(s) for s in self._snapshots],
        }
        self._log_path.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    def record_entry(self, entry: ArgumentationEntry) -> None:
        self._entries.append(entry)
        self._save()

    def record_canvas_snapshot(self, snapshot: CanvasSnapshot) -> None:
        self._snapshots.append(snapshot)
        self._save()

    def get_entries(self) -> tuple[ArgumentationEntry, ...]:
        return tuple(self._entries)
