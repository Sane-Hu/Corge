"""Memory pyramid storage — satisfies ``contracts.MemoryStorePort``.

Spec traceability:
    FRD FR-006  — engineering profile (L3)
    FRD FR-007  — memory pyramid: L0 session events, L1 engineering facts,
                  L2 scenario memory, L3 engineering profile
    09-context  — storage paths, tier 3 scenario memory, tier 4 recent actions

Storage layout (all under .agent/ per standardized storage rule):
    L0  .agent/memory/l0/<iso-timestamp>.jsonl   — raw session event logs
    L1  .agent/memory.db                         — engineering facts (SQLite)
    L2  .agent/memory/scenarios/<kind>.json      — scenario memory per feature
    L3  .agent/engineering_profile.md            — coding conventions markdown

The MemoryStore requires ``root`` (repository root Path) at construction.
All directories are created on first use.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from corge.contracts import EngineeringProfile, MemoryEvent

# ---------------------------------------------------------------------------
# Schema — L1 Engineering Facts (SQLite)
# ---------------------------------------------------------------------------

_L1_DDL = """\
CREATE TABLE IF NOT EXISTS facts (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    fact      TEXT    NOT NULL UNIQUE,
    source    TEXT    NOT NULL DEFAULT '',
    timestamp TEXT    NOT NULL DEFAULT ''
);
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(UTC).isoformat()


def _stamp(event: MemoryEvent) -> MemoryEvent:
    """Return event with timestamp filled in if empty."""
    if event.timestamp:
        return event
    return MemoryEvent(kind=event.kind, payload=event.payload, timestamp=_now())


# ---------------------------------------------------------------------------
# MemoryStore
# ---------------------------------------------------------------------------


class MemoryStore:
    """Concrete memory pyramid.  Satisfies ``contracts.MemoryStorePort``.

    Layer routing:
        store_event()    → L0 (raw session log, append-only JSONL)
        store_fact()     → L1 (engineering facts, SQLite, deduped)
        store_scenario() → L2 (scenario memory, JSON file per kind)
        update_profile() → L3 (engineering profile, markdown)

    ``root`` is the repository root.  All writes go under ``root/.agent/``.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._agent_dir = root / ".agent"
        self._l0_dir = self._agent_dir / "memory" / "l0"
        self._l1_path = self._agent_dir / "memory.db"
        self._l2_dir = self._agent_dir / "memory" / "scenarios"
        self._l3_path = self._agent_dir / "engineering_profile.md"
        self._conn: sqlite3.Connection | None = None
        self._schema_initialized: bool = False

    def close(self) -> None:
        if getattr(self, "_conn", None) is not None:
            self._conn.close() # type: ignore
            self._conn = None

    def __del__(self) -> None:
        self.close()

    # ------------------------------------------------------------------
    # L0 — Session Events (append-only JSONL, one file per session)
    # ------------------------------------------------------------------

    def store_event(self, event: MemoryEvent) -> None:
        """Append a raw session event to the current L0 log (FR-007 L0).

        One JSONL file is created per session (keyed by session start
        timestamp).  Each line is a self-contained JSON object so the
        file is streamable and crash-safe.
        """
        event = _stamp(event)
        self._l0_dir.mkdir(parents=True, exist_ok=True)

        # Session file: one per process start — keyed by date+hour so
        # replays are easy to find without scanning all lines.
        session_key = datetime.now(UTC).strftime("%Y%m%dT%H")
        log_file = self._l0_dir / f"{session_key}.jsonl"

        line = json.dumps(
            {
                "kind": event.kind,
                "timestamp": event.timestamp,
                "payload": event.payload,
            },
            ensure_ascii=False,
        )

        with log_file.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    # ------------------------------------------------------------------
    # L1 — Engineering Facts (SQLite, deduplicated)
    # ------------------------------------------------------------------

    def store_fact(self, fact: str, source: str = "") -> None:
        """Insert a repository-derived engineering fact (FR-007 L1).

        Duplicates are silently ignored (UNIQUE constraint on ``fact``).
        ``source`` is an optional reference (e.g. a file path) so the
        budget manager can weight facts by proximity to the current task.
        """
        self._agent_dir.mkdir(parents=True, exist_ok=True)
        with self._l1_connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO facts (fact, source, timestamp) VALUES (?,?,?)",
                (fact.strip(), source, _now()),
            )
            conn.commit()

    def get_facts(self, limit: int = 200) -> list[str]:
        """Return up to ``limit`` facts ordered by insertion time (newest first).

        Used by the context engine to populate Tier 2 of the prompt.
        """
        with self._l1_connect() as conn:
            rows = conn.execute(
                "SELECT fact FROM facts ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [r[0] for r in rows]

    @contextmanager
    def _l1_connect(self) -> Iterator[sqlite3.Connection]:
        if self._conn is None:
            self._agent_dir.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._l1_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
        if not self._schema_initialized:
            self._conn.executescript(_L1_DDL)
            self._schema_initialized = True
        yield self._conn

    # ------------------------------------------------------------------
    # L2 — Scenario Memory (JSON file per scenario kind)
    # ------------------------------------------------------------------

    def store_scenario(self, scenario: MemoryEvent) -> None:
        """Persist feature-specific progress/blocker event (FR-007 L2).

        Each unique ``scenario.kind`` maps to its own JSONL file under
        ``.agent/memory/scenarios/<kind>.jsonl``.  The file holds a list
        of timestamped entries so the full history of a scenario is
        available for resume and debugging.

        Schema per entry:
            {
                "timestamp": "<iso>",
                "payload":   { ... }   // discoveries, decisions, blockers
            }
        """
        scenario = _stamp(scenario)
        self._l2_dir.mkdir(parents=True, exist_ok=True)

        # Sanitise kind → safe filename (replace slashes and spaces).
        safe_kind = scenario.kind.replace("/", "_").replace(" ", "_")
        scenario_file = self._l2_dir / f"{safe_kind}.jsonl"

        entry = {
            "timestamp": scenario.timestamp,
            "payload": scenario.payload,
        }

        with scenario_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_scenario(self, kind: str, limit: int = 5) -> list[dict[str, Any]]:
        """Return all entries for a scenario kind, oldest first.

        Returns empty list if the scenario has never been written.
        Used by the context engine to populate Tier 3 of the prompt.
        Bounded by ``limit`` to prevent context window exhaustion.
        """
        safe_kind = kind.replace("/", "_").replace(" ", "_")
        scenario_file = self._l2_dir / f"{safe_kind}.jsonl"

        if not scenario_file.exists():
            return []

        events = []
        try:
            with scenario_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    events.append(json.loads(line))
            return events[-limit:] if limit > 0 else events
        except (json.JSONDecodeError, OSError):
            return []

    # ------------------------------------------------------------------
    # L3 — Engineering Profile (markdown, human-readable)
    # ------------------------------------------------------------------

    def update_profile(self, profile: EngineeringProfile) -> None:
        """Write the engineering profile to markdown (FR-006, FR-007 L3).

        Rules with confidence below 0.5 are excluded — they are too
        uncertain to include in Tier 1 context (09-context § Confidence
        Scoring).

        The file is always fully rewritten so there is one source of
        truth and no append-accumulation drift.

        Format:
            # Engineering profile
            <!-- confidence threshold: 0.5 -->

            - <rule>  <!-- confidence: 0.92 -->
            - <rule>  <!-- confidence: 0.75 -->
        """
        self._agent_dir.mkdir(parents=True, exist_ok=True)

        THRESHOLD = 0.5

        # Filter and sort: highest confidence first.
        qualified = [
            (rule, profile.confidence.get(rule, 1.0))
            for rule in profile.rules
            if profile.confidence.get(rule, 1.0) >= THRESHOLD
        ]
        qualified.sort(key=lambda x: x[1], reverse=True)

        lines: list[str] = [
            "# Engineering profile",
            f"<!-- confidence threshold: {THRESHOLD} -->",
            f"<!-- updated: {_now()} -->",
            "",
        ]

        if qualified:
            for rule, conf in qualified:
                lines.append(f"- {rule}  <!-- confidence: {conf:.2f} -->")
        else:
            lines.append("<!-- no rules above confidence threshold -->")

        lines.append("")  # trailing newline
        self._l3_path.write_text("\n".join(lines), encoding="utf-8")

    def get_profile(self) -> EngineeringProfile:
        """Return the engineering profile parsed from markdown.

        Returns an empty profile if the file has never been written.
        Used by the prompt assembler for Tier 1 context.
        """
        if not self._l3_path.exists():
            return EngineeringProfile()
            
        text = self._l3_path.read_text(encoding="utf-8")
        rules = []
        confidence = {}
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("- ") and "<!-- confidence:" in line:
                # e.g., "- Use DTOs  <!-- confidence: 0.95 -->"
                rule_part = line[2:line.index("<!--")].strip()
                try:
                    conf_str = line.split("<!-- confidence:")[1].split("-->")[0].strip()
                    confidence[rule_part] = float(conf_str)
                except (IndexError, ValueError):
                    confidence[rule_part] = 1.0
                rules.append(rule_part)
                
        return EngineeringProfile(rules=tuple(rules), confidence=confidence)
