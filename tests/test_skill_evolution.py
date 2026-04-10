#!/usr/bin/env python3
"""Tests for benchmark-driven skill evolution proposal generation."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from skill_evolution import build_proposal, write_proposal_artifacts  # noqa: E402


def _sample_benchmark() -> dict:
    return {
        "overall_summary": {
            "overall_improvement_pct": 62.9,
            "avg_quality_improvement_pct": 113.0,
            "avg_token_improvement_pct": -83.8,
            "completion_rate_with_skill": 100.0,
            "completion_rate_without_skill": 0.0,
            "task_count": 13,
        },
        "experiment_info": {
            "benchmark_version": "6.3",
        },
        "interpretation_notes": [
            "time deltas within +/-1% are noise",
            "50% baseline remains default",
        ],
        "module_policies": [
            {"module": "EXECUTING", "recommendation": "default_enable", "quality_gain_pct": 319.1, "token_delta_pct": -109.65, "completion_gap_pp": 100.0, "rationale": "keep"},
            {"module": "DEBUGGING", "recommendation": "conditional_enable_after_optimization", "quality_gain_pct": 127.5, "token_delta_pct": -285.1, "completion_gap_pp": 100.0, "rationale": "split"},
        ],
    }


def test_build_proposal_contains_core_actions():
    proposal = build_proposal(_sample_benchmark(), "tests/bench/sample.json", True)
    actions = {item["module"]: item for item in proposal["proposed_actions"]}
    assert "EXECUTING" in actions
    assert "DEBUGGING" in actions
    assert actions["EXECUTING"]["action"].startswith("retain_default_enable")
    assert proposal["benchmark_summary"]["task_count"] == 13
    assert proposal["benchmark_version"] == "6.3"


def test_write_proposal_artifacts(tmp_path):
    benchmark_path = tmp_path / "bench.json"
    benchmark_path.write_text(json.dumps(_sample_benchmark()), encoding="utf-8")

    artifact = write_proposal_artifacts(str(benchmark_path), output_dir=tmp_path / "proposals")
    assert artifact.markdown_path.exists()
    assert artifact.json_path.exists()

    markdown = artifact.markdown_path.read_text(encoding="utf-8")
    assert "Skill Evolution Proposal" in markdown
    assert "Benchmark Version: 6.3" in markdown
    assert "EXECUTING" in markdown
    payload = json.loads(artifact.json_path.read_text(encoding="utf-8"))
    assert payload["evidence_available"] is True
    assert payload["benchmark_summary"]["overall_improvement_pct"] == 62.9


def test_write_proposal_artifacts_reference_only(tmp_path):
    artifact = write_proposal_artifacts("missing-benchmark.json", output_dir=tmp_path / "proposals")
    payload = json.loads(artifact.json_path.read_text(encoding="utf-8"))
    assert payload["evidence_available"] is False
    assert payload["benchmark_version"] == "unknown"
