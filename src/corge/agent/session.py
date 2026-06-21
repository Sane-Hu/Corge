"""Session state serializer/deserializer (PRD §POC Exit Criteria #9).

Spec traceability:
    PRD §9  — "Save and resume/recover sessions later"
    CC.4    — no session serialization existed; this implements it

Saves the full mutable session state to ``.agent/session.json`` so a
session can be restored after a crash or deliberate exit.

What is persisted:
    - Current LifecycleState, MasterPhase, SpecState, PlanState
    - Active Specification fields
    - Repository root path

What is NOT persisted (reconstructed from KG/memory on reload):
    - Markov context (in-process only; expires between runs)
    - ContextBundle (always regenerated)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from corge.contracts import (
    AcceptanceCriteria,
    LifecycleState,
    MasterPhase,
    PlanState,
    Specification,
    SpecState,
)

_SESSION_FILE = "session.json"


class SessionState:
    """Lightweight value object for session snapshot data."""

    def __init__(
        self,
        lifecycle_state: LifecycleState = LifecycleState.START,
        master_phase: MasterPhase = MasterPhase.SPECIFICATION,
        spec_state: SpecState | None = None,
        plan_state: PlanState | None = None,
        specification: Specification | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self.lifecycle_state = lifecycle_state
        self.master_phase = master_phase
        self.spec_state = spec_state
        self.plan_state = plan_state
        self.specification = specification
        self.repo_root = repo_root


def save_session(agent_dir: Path, state: SessionState) -> None:
    """Serialize and write session state to ``.agent/session.json``.

    Safe to call at any point in the execution cycle.
    """
    agent_dir.mkdir(parents=True, exist_ok=True)
    path = agent_dir / _SESSION_FILE

    spec_data: dict[str, Any] | None = None
    if state.specification is not None:
        spec = state.specification
        spec_data = {
            "title": spec.title,
            "body": spec.body,
            "acceptance_criteria": list(spec.acceptance_criteria.items),
            "constraints": spec.constraints,
            "testing_expectations": spec.testing_expectations,
        }

    payload = {
        "lifecycle_state": state.lifecycle_state.value,
        "master_phase": state.master_phase.value,
        "spec_state": state.spec_state.value if state.spec_state else None,
        "plan_state": state.plan_state.value if state.plan_state else None,
        "specification": spec_data,
        "repo_root": str(state.repo_root) if state.repo_root else None,
    }

    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_session(agent_dir: Path) -> SessionState | None:
    """Deserialize session state from ``.agent/session.json``.

    Returns ``None`` if no session file exists (fresh start).
    Returns a ``SessionState`` with defaults for any missing keys so
    the caller can safely resume without validating every field.
    """
    path = agent_dir / _SESSION_FILE
    if not path.exists():
        return None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None  # corrupt file → treat as fresh start

    # Parse enums defensively — fall back to START on unknown values
    try:
        lifecycle_state = LifecycleState(raw.get("lifecycle_state", "START"))
    except ValueError:
        lifecycle_state = LifecycleState.START

    try:
        master_phase = MasterPhase(raw.get("master_phase", "SPECIFICATION"))
    except ValueError:
        master_phase = MasterPhase.SPECIFICATION

    spec_state: SpecState | None = None
    if raw.get("spec_state"):
        try:
            spec_state = SpecState(raw["spec_state"])
        except ValueError:
            pass

    plan_state: PlanState | None = None
    if raw.get("plan_state"):
        try:
            plan_state = PlanState(raw["plan_state"])
        except ValueError:
            pass

    specification: Specification | None = None
    if raw.get("specification"):
        sd = raw["specification"]
        try:
            specification = Specification(
                title=sd.get("title", ""),
                body=sd.get("body", ""),
                acceptance_criteria=AcceptanceCriteria(
                    items=tuple(sd.get("acceptance_criteria", []))
                ),
                constraints=sd.get("constraints", ""),
                testing_expectations=sd.get("testing_expectations", ""),
            )
        except Exception:
            pass

    repo_root: Path | None = None
    if raw.get("repo_root"):
        repo_root = Path(raw["repo_root"])

    return SessionState(
        lifecycle_state=lifecycle_state,
        master_phase=master_phase,
        spec_state=spec_state,
        plan_state=plan_state,
        specification=specification,
        repo_root=repo_root,
    )
