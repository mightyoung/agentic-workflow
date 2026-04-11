#!/usr/bin/env python3
"""Tests for skill proposal verifier."""

from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from proposal_registry import get_latest_proposal_state  # noqa: E402
from skill_evolution import write_proposal_artifacts  # noqa: E402
from proposal_verifier import verify_proposal, write_verification_artifacts  # noqa: E402


def _proposal(
    *,
    evidence_available: bool = True,
    benchmark_version: str = "6.3",
    include_ci: bool = True,
) -> dict:
    confidence_intervals = {}
    if include_ci:
        confidence_intervals = {
            "overall": {
                "time_improvement_pct": {
                    "mean": 66.0,
                    "lower": 22.0,
                    "upper": 94.0,
                    "sample_size": 13,
                    "confidence_level": 0.95,
                },
                "token_improvement_pct": {
                    "mean": -83.8,
                    "lower": -90.0,
                    "upper": -70.0,
                    "sample_size": 13,
                    "confidence_level": 0.95,
                },
                "quality_improvement_pct": {
                    "mean": 113.0,
                    "lower": 42.0,
                    "upper": 167.0,
                    "sample_size": 13,
                    "confidence_level": 0.95,
                },
                "overall_improvement_pct": {
                    "mean": 62.9,
                    "lower": 12.0,
                    "upper": 88.0,
                    "sample_size": 13,
                    "confidence_level": 0.95,
                },
                "completion_gap_pp": {
                    "mean": 80.0,
                    "lower": 64.0,
                    "upper": 100.0,
                    "sample_size": 13,
                    "confidence_level": 0.95,
                },
            }
        }
    return {
        "proposal_id": "skill-evolution-20260411T000000Z",
        "generated_at": "2026-04-11T00:00:00+00:00",
        "source_reference": "tests/bench/sample.json",
        "evidence_available": evidence_available,
        "benchmark_version": benchmark_version,
        "benchmark_summary": {
            "task_count": 13,
            "completion_rate_with_skill": 100.0,
            "completion_rate_without_skill": 20.0,
            "avg_quality_improvement_pct": 55.0,
            "avg_token_improvement_pct": -80.0,
        },
        "interpretation_notes": [],
        "module_policies": [],
        "confidence_intervals": confidence_intervals,
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
    return {
        "experiment_info": {"benchmark_version": version},
        "overall_summary": {
            "overall_improvement_pct": 62.9,
            "avg_quality_improvement_pct": 113.0,
            "avg_token_improvement_pct": -83.8,
            "completion_rate_with_skill": 100.0,
            "completion_rate_without_skill": 0.0,
            "task_count": 13,
        },
        "confidence_intervals": _proposal()["confidence_intervals"],
        "interpretation_notes": [
            "time deltas within +/-1% are noise",
            "50% baseline remains default",
        ],
        "module_policies": [
            {
                "module": "EXECUTING",
                "recommendation": "default_enable",
                "quality_gain_pct": 319.1,
                "token_delta_pct": -109.65,
                "completion_gap_pp": 100.0,
                "rationale": "keep",
            },
            {
                "module": "DEBUGGING",
                "recommendation": "conditional_enable_after_optimization",
                "quality_gain_pct": 127.5,
                "token_delta_pct": -285.1,
                "completion_gap_pp": 100.0,
                "rationale": "split",
            },
        ],
    }


def test_verify_proposal_approve():
    result = verify_proposal(_proposal(), proposal_path="proposal.json", benchmark=_benchmark("6.3"))
    assert result["decision"] == "approve"


def test_verify_proposal_revise_when_no_evidence():
    result = verify_proposal(_proposal(evidence_available=False), proposal_path="proposal.json")
    assert result["decision"] == "revise"
    assert any(check["name"] == "evidence_available" and check["status"] == "revise" for check in result["checks"])


def test_verify_proposal_revise_when_confidence_intervals_missing():
    result = verify_proposal(_proposal(include_ci=False), proposal_path="proposal.json")
    assert result["decision"] == "revise"
    assert any(check["name"] == "confidence_intervals" and check["status"] == "revise" for check in result["checks"])


def test_verify_proposal_reject_on_version_mismatch():
    result = verify_proposal(_proposal(benchmark_version="6.2"), proposal_path="proposal.json", benchmark=_benchmark("6.3"))
    assert result["decision"] == "reject"
    assert any(check["name"] == "benchmark_reference" and check["status"] == "reject" for check in result["checks"])


def test_verify_proposal_revise_on_threshold_violation():
    proposal = _proposal()
    proposal["benchmark_summary"]["task_count"] = 3
    proposal["benchmark_summary"]["avg_quality_improvement_pct"] = 2.0
    result = verify_proposal(proposal, proposal_path="proposal.json", benchmark=_benchmark("6.3"))
    assert result["decision"] == "revise"
    assert any(check["name"] == "benchmark_task_count" and check["status"] == "revise" for check in result["checks"])


def test_write_verification_artifacts(tmp_path):
    proposal_path = tmp_path / "proposal.json"
    benchmark_path = tmp_path / "bench.json"
    proposal_path.write_text(json.dumps(_proposal(), ensure_ascii=False), encoding="utf-8")
    benchmark_path.write_text(json.dumps(_benchmark(), ensure_ascii=False), encoding="utf-8")

    artifact = write_verification_artifacts(str(proposal_path), benchmark_path=str(benchmark_path), output_dir=tmp_path / "out")
    assert artifact.decision == "approve"
    payload = json.loads(artifact.json_path.read_text(encoding="utf-8"))
    assert payload["decision"] == "approve"


def test_write_verification_artifacts_updates_registry(tmp_path):
    benchmark_path = tmp_path / "bench.json"
    registry_path = tmp_path / "index.jsonl"
    benchmark_path.write_text(json.dumps(_benchmark(), ensure_ascii=False), encoding="utf-8")

    generated = write_proposal_artifacts(str(benchmark_path), output_dir=tmp_path / "proposals", registry_path=registry_path)

    artifact = write_verification_artifacts(
        str(generated.json_path),
        benchmark_path=str(benchmark_path),
        output_dir=tmp_path / "out",
        registry_path=registry_path,
    )
    assert artifact.decision == "approve"
    latest = get_latest_proposal_state(generated.proposal_id, index_path=registry_path)
    assert latest is not None
    assert latest["status"] == "verified"
    assert latest["decision"] == "approve"
