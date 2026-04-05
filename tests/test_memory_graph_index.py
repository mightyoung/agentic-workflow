"""
Tests for scripts/memory_graph_index.py

Covers:
- parse_reflexion_entry: field extraction from Reflexion format
- extract_entities: file/module entity detection
- build_causal_index / search_causal: causal graph round-trip
- build_entity_index / search_entity: entity graph round-trip
- rebuild_all_indexes: convenience wrapper
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Make scripts importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from memory_graph_index import (
    MEMORY_CAUSAL_FILE,
    MEMORY_ENTITY_FILE,
    MEMORY_INDEX_FILE,
    build_causal_index,
    build_entity_index,
    extract_entities,
    parse_reflexion_entry,
    rebuild_all_indexes,
    search_causal,
    search_entity,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def tmp_workdir(tmp_path, monkeypatch):
    """Run every test in a temporary directory to avoid polluting repo root."""
    monkeypatch.chdir(tmp_path)
    yield tmp_path


def _write_index(entries: list[dict], path: str = MEMORY_INDEX_FILE) -> None:
    """Write test entries to a JSONL index file."""
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


# ── parse_reflexion_entry ─────────────────────────────────────────────────────

class TestParseReflexionEntry:
    def test_full_format(self):
        text = (
            "Task:debug Trigger:Python 3.9 union syntax "
            "Mistake:used str|Path Mistake:without future "
            "Fix:add from __future__ import annotations "
            "Signal:TypeError unsupported operand type(s) for |"
        )
        fields = parse_reflexion_entry(text)
        assert fields["task"] == "debug"
        assert "Python 3.9" in fields["trigger"]
        assert "from __future__" in fields["fix"]
        assert "TypeError" in fields["signal"]

    def test_case_insensitive(self):
        text = "TASK:test TRIGGER:import error FIX:add import SIGNAL:ModuleNotFoundError"
        fields = parse_reflexion_entry(text)
        assert "test" in fields.get("task", "")
        assert "import error" in fields.get("trigger", "")

    def test_missing_fields_excluded(self):
        text = "Task:debug Signal:some error"
        fields = parse_reflexion_entry(text)
        assert "task" in fields
        assert "signal" in fields
        assert "trigger" not in fields
        assert "fix" not in fields

    def test_empty_text(self):
        assert parse_reflexion_entry("") == {}

    def test_non_reflexion_text(self):
        text = "This is just a regular note without any structured fields."
        fields = parse_reflexion_entry(text)
        assert fields == {}

    def test_multiword_values(self):
        text = "Task:type annotation Trigger:Python 3.9 does not support X|Y Fix:use typing Union Signal:unsupported |"
        fields = parse_reflexion_entry(text)
        assert "Python 3.9" in fields.get("trigger", "")
        assert "typing Union" in fields.get("fix", "")


# ── extract_entities ──────────────────────────────────────────────────────────

class TestExtractEntities:
    def test_py_file(self):
        text = "Fixed bug in src/auth.py line 42"
        ents = extract_entities(text)
        assert "src/auth.py" in ents

    def test_ts_file(self):
        text = "Updated App.tsx and components/Button.tsx"
        ents = extract_entities(text)
        assert "app.tsx" in ents or "App.tsx".lower() in ents

    def test_path_prefixed_module(self):
        text = "See scripts/memory_longterm.py for implementation"
        ents = extract_entities(text)
        assert any("memory_longterm" in e for e in ents)

    def test_multiple_entities(self):
        text = "auth.py:42 NPE — fix in scripts/workflow_engine.py"
        ents = extract_entities(text)
        assert len(ents) >= 2

    def test_no_entities(self):
        text = "Just a plain text note with no file references."
        ents = extract_entities(text)
        assert ents == []

    def test_deduplication(self):
        text = "auth.py auth.py auth.py"
        ents = extract_entities(text)
        count = sum(1 for e in ents if "auth.py" in e)
        assert count == 1


# ── Causal Index ──────────────────────────────────────────────────────────────

class TestBuildCausalIndex:
    def test_builds_from_reflexion_entries(self, tmp_path):
        entries = [
            {
                "id": "aaa1",
                "type": "experience",
                "text": "Task:debug Trigger:import error Fix:add missing import Signal:ModuleNotFoundError",
            },
            {
                "id": "bbb2",
                "type": "experience",
                "text": "Task:type Trigger:py39 Mistake:no future Fix:add future Signal:TypeError unsupported |",
            },
        ]
        _write_index(entries)
        idx = build_causal_index()

        assert idx["_total"] == 2
        assert "modulenotfounderror" in idx["signals"]
        assert "typeerror unsupported |" in idx["signals"]
        assert os.path.exists(MEMORY_CAUSAL_FILE)

    def test_skips_non_reflexion_entries(self, tmp_path):
        entries = [
            {"id": "ccc3", "type": "pattern", "text": "Always use parameterized queries."},
        ]
        _write_index(entries)
        idx = build_causal_index()
        assert idx["_total"] == 0
        assert idx["signals"] == {}

    def test_empty_index_file(self, tmp_path):
        _write_index([])
        idx = build_causal_index()
        assert idx["_total"] == 0

    def test_missing_index_file(self, tmp_path):
        idx = build_causal_index()
        assert idx["_total"] == 0

    def test_writes_causal_file(self, tmp_path):
        entries = [
            {"id": "dd4", "type": "experience",
             "text": "Task:x Trigger:foo Fix:bar Signal:SomeError"},
        ]
        _write_index(entries)
        build_causal_index()
        assert os.path.exists(MEMORY_CAUSAL_FILE)
        with open(MEMORY_CAUSAL_FILE) as f:
            data = json.load(f)
        assert data["version"] == 1


class TestSearchCausal:
    def _setup(self):
        entries = [
            {"id": "e1", "type": "experience",
             "text": "Task:debug Trigger:Python 3.9 syntax Fix:add future import Signal:TypeError unsupported |"},
            {"id": "e2", "type": "experience",
             "text": "Task:debug Trigger:missing module Fix:add to requirements Signal:ModuleNotFoundError"},
        ]
        _write_index(entries)
        build_causal_index()

    def test_signal_match(self):
        self._setup()
        hits = search_causal("TypeError unsupported")
        assert len(hits) >= 1
        assert hits[0]["_match_field"] == "signal"
        assert "future import" in hits[0]["fix"]

    def test_trigger_match(self):
        self._setup()
        hits = search_causal("missing module")
        assert len(hits) >= 1
        assert hits[0]["_match_field"] in ("signal", "trigger")

    def test_no_match_returns_empty(self):
        self._setup()
        hits = search_causal("completely unrelated xyz123")
        assert hits == []

    def test_missing_causal_file_returns_empty(self):
        hits = search_causal("any query")
        assert hits == []

    def test_limit_respected(self):
        entries = [
            {"id": f"id{i}", "type": "experience",
             "text": f"Task:x Trigger:foo{i} Fix:bar Signal:SameError"}
            for i in range(10)
        ]
        _write_index(entries)
        build_causal_index()
        hits = search_causal("SameError", limit=3)
        assert len(hits) <= 3

    def test_signal_match_before_trigger_match(self):
        """Signal matches should appear before trigger matches."""
        entries = [
            {"id": "sig", "type": "experience",
             "text": "Task:x Trigger:other Fix:f1 Signal:SpecificError target"},
            {"id": "tri", "type": "experience",
             "text": "Task:x Trigger:target Trigger:another Fix:f2 Signal:OtherError"},
        ]
        _write_index(entries)
        build_causal_index()
        hits = search_causal("target", limit=5)
        # Signal match (id=sig) should come before trigger match (id=tri)
        ids = [h["id"] for h in hits]
        if "sig" in ids and "tri" in ids:
            assert ids.index("sig") < ids.index("tri")


# ── Entity Index ──────────────────────────────────────────────────────────────

class TestBuildEntityIndex:
    def test_builds_from_file_references(self, tmp_path):
        entries = [
            {"id": "f1", "type": "experience",
             "text": "Bug in src/auth.py:42 — null check missing"},
            {"id": "f2", "type": "experience",
             "text": "Refactor scripts/memory_longterm.py to add confidence"},
        ]
        _write_index(entries)
        idx = build_entity_index()

        assert idx["_total"] == 2
        assert os.path.exists(MEMORY_ENTITY_FILE)
        entity_keys = list(idx["entities"].keys())
        assert any("auth.py" in k for k in entity_keys)
        assert any("memory_longterm" in k for k in entity_keys)

    def test_no_entities_produces_empty_index(self, tmp_path):
        entries = [
            {"id": "g1", "type": "experience", "text": "A plain note with no code refs."},
        ]
        _write_index(entries)
        idx = build_entity_index()
        assert idx["_total"] == 0
        assert idx["entities"] == {}

    def test_missing_index_returns_empty(self, tmp_path):
        idx = build_entity_index()
        assert idx["_total"] == 0

    def test_writes_entity_file(self, tmp_path):
        entries = [
            {"id": "h1", "type": "experience", "text": "See auth.py for login logic"},
        ]
        _write_index(entries)
        build_entity_index()
        assert os.path.exists(MEMORY_ENTITY_FILE)
        with open(MEMORY_ENTITY_FILE) as f:
            data = json.load(f)
        assert data["version"] == 1


class TestSearchEntity:
    def _setup(self):
        entries = [
            {"id": "p1", "type": "experience",
             "text": "NPE in src/auth.py:42 when user is None"},
            {"id": "p2", "type": "experience",
             "text": "SQL injection risk in scripts/db_utils.py — use parameterized query"},
        ]
        _write_index(entries)
        build_entity_index()

    def test_exact_filename_match(self):
        self._setup()
        hits = search_entity("auth.py")
        assert len(hits) >= 1
        assert any("auth" in h.get("snippet", "").lower() for h in hits)

    def test_partial_match(self):
        self._setup()
        hits = search_entity("auth")
        assert len(hits) >= 1

    def test_no_match_returns_empty(self):
        self._setup()
        hits = search_entity("nonexistent_file.xyz")
        assert hits == []

    def test_missing_entity_file_returns_empty(self):
        hits = search_entity("auth.py")
        assert hits == []

    def test_limit_respected(self):
        entries = [
            {"id": f"q{i}", "type": "experience", "text": f"Issue in auth.py variant {i}"}
            for i in range(10)
        ]
        _write_index(entries)
        build_entity_index()
        hits = search_entity("auth.py", limit=3)
        assert len(hits) <= 3

    def test_matched_entity_field_present(self):
        self._setup()
        hits = search_entity("auth.py")
        assert all("_matched_entity" in h for h in hits)


# ── rebuild_all_indexes ───────────────────────────────────────────────────────

class TestRebuildAllIndexes:
    def test_returns_totals(self, tmp_path):
        entries = [
            {"id": "r1", "type": "experience",
             "text": "Task:x Trigger:foo Fix:bar Signal:SomeError in auth.py"},
        ]
        _write_index(entries)
        c_total, e_total = rebuild_all_indexes()
        assert isinstance(c_total, int)
        assert isinstance(e_total, int)
        assert c_total >= 1
        assert e_total >= 1

    def test_creates_both_files(self, tmp_path):
        entries = [
            {"id": "r2", "type": "experience",
             "text": "Task:x Trigger:y Fix:z Signal:ErrX — see src/foo.py"},
        ]
        _write_index(entries)
        rebuild_all_indexes()
        assert os.path.exists(MEMORY_CAUSAL_FILE)
        assert os.path.exists(MEMORY_ENTITY_FILE)

    def test_empty_source_creates_empty_indexes(self, tmp_path):
        _write_index([])
        c, e = rebuild_all_indexes()
        assert c == 0
        assert e == 0
