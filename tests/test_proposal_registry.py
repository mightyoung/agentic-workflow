#!/usr/bin/env python3
"""Tests for the proposal lifecycle registry."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from proposal_registry import get_latest_proposal_state, record_proposal_event, render_summary  # noqa: E402


def test_registry_records_lifecycle_events(tmp_path):
    index_path = tmp_path / "index.jsonl"
    proposal_id = "skill-evolution-20260411T010101Z"

    generated = record_proposal_event(
        proposal_id=proposal_id,
        status="generated",
        event_type="generated",
        index_path=index_path,
        source_reference="bench.json",
        benchmark_version="6.3",
        proposal_path="proposal.json",
    )
    verified = record_proposal_event(
        proposal_id=proposal_id,
        status="verified",
        event_type="verification",
        index_path=index_path,
        source_reference="proposal.json",
        benchmark_version="6.3",
        proposal_path="proposal.json",
        verification_path="verify.json",
        decision="approve",
    )
    approved = record_proposal_event(
        proposal_id=proposal_id,
        status="approved",
        event_type="run_approved",
        index_path=index_path,
        source_reference="proposal.json",
        benchmark_version="6.3",
        proposal_path="proposal.json",
        verification_path="verify.json",
        decision="approve",
    )

    assert generated["status"] == "generated"
    assert verified["status"] == "verified"
    assert approved["status"] == "approved"

    latest = get_latest_proposal_state(proposal_id, index_path=index_path)
    assert latest is not None
    assert latest["status"] == "approved"
    assert "decision=approve" in render_summary(latest)

    records = [json.loads(line) for line in index_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(records) == 3
    assert records[-1]["status"] == "approved"


def test_registry_allows_blocked_to_discarded(tmp_path):
    index_path = tmp_path / "index.jsonl"
    proposal_id = "skill-evolution-20260411T020202Z"

    record_proposal_event(
        proposal_id=proposal_id,
        status="generated",
        event_type="generated",
        index_path=index_path,
        source_reference="bench.json",
        benchmark_version="6.3",
        proposal_path="proposal.json",
    )
    record_proposal_event(
        proposal_id=proposal_id,
        status="blocked",
        event_type="verification",
        index_path=index_path,
        source_reference="proposal.json",
        benchmark_version="6.3",
        proposal_path="proposal.json",
        verification_path="verify.json",
        decision="reject",
    )
    final = record_proposal_event(
        proposal_id=proposal_id,
        status="discarded",
        event_type="run_aborted",
        index_path=index_path,
        source_reference="proposal.json",
        benchmark_version="6.3",
        proposal_path="proposal.json",
        verification_path="verify.json",
        decision="reject",
    )

    assert final["status"] == "discarded"
    assert get_latest_proposal_state(proposal_id, index_path=index_path)["status"] == "discarded"
