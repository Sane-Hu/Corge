"""Tests for the memory pyramid implementation.

Tests are fully isolated — each test gets a fresh temp directory via
pytest's ``tmp_path`` fixture.  No LLM calls, no agent loop, no network.

Run:
    pytest test_memory.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from corge.contracts import EngineeringProfile, MemoryEvent
from corge.memory import MemoryStore

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path: Path) -> MemoryStore:
    """Fresh MemoryStore backed by a temp directory."""
    return MemoryStore(root=tmp_path)


@pytest.fixture
def agent_dir(tmp_path: Path) -> Path:
    return tmp_path / ".agent"


# ---------------------------------------------------------------------------
# L0 — Session Events
# ---------------------------------------------------------------------------


class TestL0SessionEvents:
    def test_creates_jsonl_file_on_first_event(
        self, store: MemoryStore, agent_dir: Path
    ) -> None:
        store.store_event(MemoryEvent(kind="tool_call", payload={"tool": "read"}))
        l0_dir = agent_dir / "memory" / "l0"
        files = list(l0_dir.glob("*.jsonl"))
        assert len(files) == 1

    def test_each_line_is_valid_json(self, store: MemoryStore, agent_dir: Path) -> None:
        store.store_event(MemoryEvent(kind="tool_call", payload={"tool": "read"}))
        store.store_event(MemoryEvent(kind="tool_result", payload={"output": "ok"}))
        l0_dir = agent_dir / "memory" / "l0"
        log_file = next(l0_dir.glob("*.jsonl"))
        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 2
        for line in lines:
            obj = json.loads(line)
            assert "kind" in obj
            assert "timestamp" in obj
            assert "payload" in obj

    def test_appends_not_overwrites(self, store: MemoryStore, agent_dir: Path) -> None:
        for i in range(5):
            store.store_event(MemoryEvent(kind="step", payload={"i": i}))
        l0_dir = agent_dir / "memory" / "l0"
        log_file = next(l0_dir.glob("*.jsonl"))
        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 5

    def test_stamps_empty_timestamp(self, store: MemoryStore, agent_dir: Path) -> None:
        # event has no timestamp — store should fill it
        store.store_event(MemoryEvent(kind="tool_call", payload={}))
        l0_dir = agent_dir / "memory" / "l0"
        log_file = next(l0_dir.glob("*.jsonl"))
        obj = json.loads(log_file.read_text().strip())
        assert obj["timestamp"] != ""

    def test_preserves_existing_timestamp(
        self, store: MemoryStore, agent_dir: Path
    ) -> None:
        ts = "2024-01-01T00:00:00+00:00"
        store.store_event(MemoryEvent(kind="tool_call", payload={}, timestamp=ts))
        l0_dir = agent_dir / "memory" / "l0"
        log_file = next(l0_dir.glob("*.jsonl"))
        obj = json.loads(log_file.read_text().strip())
        assert obj["timestamp"] == ts

    def test_payload_preserved(self, store: MemoryStore, agent_dir: Path) -> None:
        store.store_event(
            MemoryEvent(
                kind="approval", payload={"action": "write", "target": "main.py"}
            )
        )
        l0_dir = agent_dir / "memory" / "l0"
        log_file = next(l0_dir.glob("*.jsonl"))
        obj = json.loads(log_file.read_text().strip())
        assert obj["payload"]["action"] == "write"
        assert obj["payload"]["target"] == "main.py"


# ---------------------------------------------------------------------------
# L1 — Engineering Facts
# ---------------------------------------------------------------------------


class TestL1EngineeringFacts:
    def test_stores_fact(self, store: MemoryStore) -> None:
        store.store_fact("Uses service layer pattern")
        facts = store.get_facts()
        assert "Uses service layer pattern" in facts

    def test_deduplicates_same_fact(self, store: MemoryStore) -> None:
        store.store_fact("Uses service layer pattern")
        store.store_fact("Uses service layer pattern")
        store.store_fact("Uses service layer pattern")
        facts = store.get_facts()
        assert facts.count("Uses service layer pattern") == 1

    def test_stores_multiple_different_facts(self, store: MemoryStore) -> None:
        store.store_fact("Uses service layer pattern")
        store.store_fact("DTOs are frozen dataclasses")
        store.store_fact("Tests live under tests/")
        facts = store.get_facts()
        assert len(facts) == 3

    def test_get_facts_newest_first(self, store: MemoryStore) -> None:
        store.store_fact("first fact")
        store.store_fact("second fact")
        store.store_fact("third fact")
        facts = store.get_facts()
        # newest first → third inserted = first returned
        assert facts[0] == "third fact"

    def test_get_facts_respects_limit(self, store: MemoryStore) -> None:
        for i in range(20):
            store.store_fact(f"fact number {i}")
        facts = store.get_facts(limit=5)
        assert len(facts) == 5

    def test_get_facts_returns_empty_when_none(self, store: MemoryStore) -> None:
        assert store.get_facts() == []

    def test_creates_memory_db_in_agent_dir(
        self, store: MemoryStore, agent_dir: Path
    ) -> None:
        store.store_fact("any fact")
        assert (agent_dir / "memory.db").exists()


# ---------------------------------------------------------------------------
# L2 — Scenario Memory
# ---------------------------------------------------------------------------


class TestL2ScenarioMemory:
    def test_creates_scenario_file(self, store: MemoryStore, agent_dir: Path) -> None:
        store.store_scenario(
            MemoryEvent(kind="user_auth", payload={"discovery": "JWT used"})
        )
        scenario_file = agent_dir / "memory" / "scenarios" / "user_auth.jsonl"
        assert scenario_file.exists()

    def test_scenario_file_is_valid_json(
        self, store: MemoryStore, agent_dir: Path
    ) -> None:
        store.store_scenario(
            MemoryEvent(kind="user_auth", payload={"discovery": "JWT used"})
        )
        scenario_file = agent_dir / "memory" / "scenarios" / "user_auth.jsonl"
        assert scenario_file.exists()

        lines = scenario_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert isinstance(data, dict)
        assert "timestamp" in data
        assert "payload" in data

    def test_appends_to_existing_scenario(
        self, store: MemoryStore, agent_dir: Path
    ) -> None:
        store.store_scenario(
            MemoryEvent(kind="user_auth", payload={"discovery": "JWT used"})
        )
        store.store_scenario(
            MemoryEvent(kind="user_auth", payload={"blocker": "token expiry unclear"})
        )
        store.store_scenario(
            MemoryEvent(kind="user_auth", payload={"decision": "use 1h expiry"})
        )
        data = store.get_scenario("user_auth")
        assert len(data) == 3

    def test_different_kinds_are_separate_files(
        self, store: MemoryStore, agent_dir: Path
    ) -> None:
        store.store_scenario(MemoryEvent(kind="user_auth", payload={"x": 1}))
        store.store_scenario(MemoryEvent(kind="payment_flow", payload={"x": 2}))
        scenarios_dir = agent_dir / "memory" / "scenarios"
        files = list(scenarios_dir.glob("*.jsonl"))
        assert len(files) == 2

    def test_get_scenario_returns_oldest_first(self, store: MemoryStore) -> None:
        store.store_scenario(MemoryEvent(kind="feat", payload={"step": 1}))
        store.store_scenario(MemoryEvent(kind="feat", payload={"step": 2}))
        store.store_scenario(MemoryEvent(kind="feat", payload={"step": 3}))
        data = store.get_scenario("feat")
        assert data[0]["payload"]["step"] == 1
        assert data[-1]["payload"]["step"] == 3

    def test_get_scenario_returns_empty_for_unknown_kind(
        self, store: MemoryStore
    ) -> None:
        assert store.get_scenario("nonexistent_feature") == []

    def test_payload_preserved_in_scenario(self, store: MemoryStore) -> None:
        store.store_scenario(
            MemoryEvent(
                kind="checkout",
                payload={
                    "discovery": "uses Stripe",
                    "blocker": None,
                    "files": ["payment.py"],
                },
            )
        )
        data = store.get_scenario("checkout")
        assert data[0]["payload"]["discovery"] == "uses Stripe"
        assert data[0]["payload"]["files"] == ["payment.py"]

    def test_kind_with_slashes_creates_valid_filename(
        self, store: MemoryStore, agent_dir: Path
    ) -> None:
        store.store_scenario(MemoryEvent(kind="auth/login", payload={}))
        scenario_file = agent_dir / "memory" / "scenarios" / "auth_login.jsonl"
        assert scenario_file.exists()

    def test_stamps_empty_timestamp_in_scenario(self, store: MemoryStore) -> None:
        store.store_scenario(MemoryEvent(kind="feat", payload={}))
        data = store.get_scenario("feat")
        assert data[0]["timestamp"] != ""


# ---------------------------------------------------------------------------
# L3 — Engineering Profile
# ---------------------------------------------------------------------------


class TestL3EngineeringProfile:
    def test_creates_markdown_file(self, store: MemoryStore, agent_dir: Path) -> None:
        store.update_profile(
            EngineeringProfile(
                rules=("Use service layer",), confidence={"Use service layer": 0.9}
            )
        )
        assert (agent_dir / "engineering_profile.md").exists()

    def test_high_confidence_rules_included(
        self, store: MemoryStore, agent_dir: Path
    ) -> None:
        store.update_profile(
            EngineeringProfile(
                rules=("Use service layer", "DTOs are frozen"),
                confidence={"Use service layer": 0.95, "DTOs are frozen": 0.80},
            )
        )
        content = (agent_dir / "engineering_profile.md").read_text()
        assert "Use service layer" in content
        assert "DTOs are frozen" in content

    def test_low_confidence_rules_excluded(
        self, store: MemoryStore, agent_dir: Path
    ) -> None:
        store.update_profile(
            EngineeringProfile(
                rules=("Solid rule", "Uncertain rule"),
                confidence={"Solid rule": 0.9, "Uncertain rule": 0.3},
            )
        )
        content = (agent_dir / "engineering_profile.md").read_text()
        assert "Solid rule" in content
        assert "Uncertain rule" not in content

    def test_threshold_boundary_included(
        self, store: MemoryStore, agent_dir: Path
    ) -> None:
        # exactly 0.5 → included
        store.update_profile(
            EngineeringProfile(
                rules=("Boundary rule",), confidence={"Boundary rule": 0.5}
            )
        )
        content = (agent_dir / "engineering_profile.md").read_text()
        assert "Boundary rule" in content

    def test_below_threshold_excluded(
        self, store: MemoryStore, agent_dir: Path
    ) -> None:
        # 0.49 → excluded
        store.update_profile(
            EngineeringProfile(rules=("Almost rule",), confidence={"Almost rule": 0.49})
        )
        content = (agent_dir / "engineering_profile.md").read_text()
        assert "Almost rule" not in content

    def test_rules_sorted_by_confidence_descending(
        self, store: MemoryStore, agent_dir: Path
    ) -> None:
        store.update_profile(
            EngineeringProfile(
                rules=("Low rule", "High rule", "Mid rule"),
                confidence={"Low rule": 0.6, "High rule": 0.95, "Mid rule": 0.75},
            )
        )
        content = (agent_dir / "engineering_profile.md").read_text()
        high_pos = content.index("High rule")
        mid_pos = content.index("Mid rule")
        low_pos = content.index("Low rule")
        assert high_pos < mid_pos < low_pos

    def test_overwrites_not_appends(self, store: MemoryStore, agent_dir: Path) -> None:
        store.update_profile(
            EngineeringProfile(rules=("Old rule",), confidence={"Old rule": 0.9})
        )
        store.update_profile(
            EngineeringProfile(rules=("New rule",), confidence={"New rule": 0.9})
        )
        content = (agent_dir / "engineering_profile.md").read_text()
        assert "Old rule" not in content
        assert "New rule" in content

    def test_get_profile_returns_empty_when_missing(self, store: MemoryStore) -> None:
        profile = store.get_profile()
        assert profile.rules == ()


# ---------------------------------------------------------------------------
# L1 — Fact Invalidation (P4 harness enforcement)
# ---------------------------------------------------------------------------


class TestL1FactInvalidation:
    def test_invalidate_removes_matching_facts(self, store: MemoryStore) -> None:
        store.store_fact("canvas_draft.py exists and contains I love Corge")
        store.store_fact("unrelated fact about project structure")
        store.invalidate_fact_containing("canvas_draft.py")
        remaining = store.get_facts()
        assert all("canvas_draft.py" not in f for f in remaining)
        assert any("unrelated fact" in f for f in remaining)

    def test_invalidate_no_match_is_noop(self, store: MemoryStore) -> None:
        store.store_fact("some fact about the repo")
        store.invalidate_fact_containing("nonexistent_file.py")
        assert store.get_facts() == ["some fact about the repo"]

    def test_invalidate_empty_db_is_safe(self, store: MemoryStore) -> None:
        # Should not raise even if DB has never been written to
        store.invalidate_fact_containing("anything.py")

    def test_invalidate_removes_multiple_matching_facts(self, store: MemoryStore) -> None:
        store.store_fact("ghost.py exists")
        store.store_fact("ghost.py was created in step-1")
        store.store_fact("other.py is unrelated")
        store.invalidate_fact_containing("ghost.py")
        remaining = store.get_facts()
        assert len(remaining) == 1
        assert "other.py" in remaining[0]


    def test_get_profile_returns_parsed_content(self, store: MemoryStore) -> None:
        store.update_profile(
            EngineeringProfile(
                rules=("Use service layer",), confidence={"Use service layer": 0.9}
            )
        )
        profile = store.get_profile()
        assert profile.rules == ("Use service layer",)
        assert profile.confidence["Use service layer"] == 0.9

    def test_empty_rules_writes_placeholder(
        self, store: MemoryStore, agent_dir: Path
    ) -> None:
        store.update_profile(EngineeringProfile(rules=(), confidence={}))
        content = (agent_dir / "engineering_profile.md").read_text()
        assert "no rules above confidence threshold" in content

    def test_rule_without_confidence_entry_defaults_to_included(
        self, store: MemoryStore, agent_dir: Path
    ) -> None:
        # rule with no confidence entry → defaults to 1.0 → included
        store.update_profile(
            EngineeringProfile(rules=("Rule with no confidence",), confidence={})
        )
        content = (agent_dir / "engineering_profile.md").read_text()
        assert "Rule with no confidence" in content
