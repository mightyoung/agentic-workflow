#!/usr/bin/env python3
"""Tests for skill proposal verifier."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from proposal_verifier import verify_proposal, write_verification_artifacts  # noqa: E402


def _proposal(*, evidence_available: bool = True, benchmark_version: str = "6.3") -> dict:
    return {
        "proposal_id": "skill-evolution-20260411T000000Z",
        "generated_at": "2026-04-11T00:00:00+00:00",
        "source_reference": "tests/bench/sample.json",
        "evidence_available": evidence_available,
        "benchmark_version": benchmark_version,
        "benchmark_summary": {
            "task_count": 13,
        },
        "interpretation_notes": [],
        "module_policies": [],
        "proposed_actions": [
            {"module": "EXECUTING", "action": "retain_default_enable_50", "why": "roi"},
            {
                "module": "MUTATION_POLICY",
                "action": "keep_skill_changes_reviewed_only",
                "why": "proposal only",
            },
        ],
        "rollback_conditions": ["r1", "r2"],
    }


def _benchmark(version: str = "6.3") -> dict:
    return {"experiment_info": {"benchmark_version": version}}


def test_verify_proposal_approve():
    result = verify_proposal(_proposal(), proposal_path="proposal.json", benchmark=_benchmark("6.3"))
    assert result["decision"] == "approve"


def test_verify_proposal_revise_when_no_evidence():
    result = verify_proposal(_proposal(evidence_available=False), proposal_path="proposal.json")
    assert result["decision"] == "revise"
    assert any(check["name"] == "evidence_available" and check["status"] == "revise" for check in result["checks"])


def test_verify_proposal_reject_on_version_mismatch():
    result = verify_proposal(_proposal(benchmark_version="6.2"), proposal_path="proposal.json", benchmark=_benchmark("6.3"))
    assert result["decision"] == "reject"
    assert any(check["name"] == "benchmark_reference" and check["status"] == "reject" for check in result["checks"])


def test_write_verification_artifacts(tmp_path):
    proposal_path = tmp_path / "proposal.json"
    benchmark_path = tmp_path / "bench.json"
    proposal_path.write_text(json.dumps(_proposal(), ensure_ascii=False), encoding="utf-8")
    benchmark_path.write_text(json.dumps(_benchmark(), ensure_ascii=False), encoding="utf-8")

    artifact = write_verification_artifacts(str(proposal_path), benchmark_path=str(benchmark_path), output_dir=tmp_path / "out")
    assert artifact.decision == "approve"
    payload = json.loads(artifact.json_path.read_text(encoding="utf-8"))
    assert payload["decision"] == "approve"
