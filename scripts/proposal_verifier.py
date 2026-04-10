#!/usr/bin/env python3
"""Verify skill evolution proposals before they are consumed by improvement runs."""

from __future__ import annotations

import argparse
import json
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("knowledge/skill_proposals/verifications")
DEFAULT_CONFIG_PATH = Path("configs/proposal_verifier.toml")


@dataclass(frozen=True)
class VerificationArtifact:
    decision: str
    json_path: Path
    markdown_path: Path


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load verifier threshold config, falling back to sane defaults."""
    defaults = {
        "min_task_count": 8,
        "min_completion_gap_pp": 1.0,
        "min_quality_improvement_pct": 10.0,
        "max_token_cost_increase_pct": 220.0,
    }
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        return defaults
    try:
        data = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return defaults
    policy = data.get("policy", {}) if isinstance(data, dict) else {}
    if not isinstance(policy, dict):
        return defaults
    merged = defaults.copy()
    for key in defaults:
        if key in policy:
            merged[key] = policy[key]
    return merged


def verify_proposal(
    proposal: dict[str, Any],
    *,
    proposal_path: str,
    benchmark: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    config = config or load_config()

    def add_check(name: str, status: str, detail: str) -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    required_keys = {
        "proposal_id",
        "generated_at",
        "source_reference",
        "evidence_available",
        "benchmark_version",
        "benchmark_summary",
        "proposed_actions",
        "rollback_conditions",
    }
    missing = sorted(required_keys - set(proposal.keys()))
    if missing:
        add_check("required_keys", "reject", f"missing required keys: {', '.join(missing)}")
    else:
        add_check("required_keys", "pass", "all required keys are present")

    actions = proposal.get("proposed_actions", [])
    if not isinstance(actions, list) or not actions:
        add_check("proposed_actions", "reject", "proposed_actions must be a non-empty list")
    else:
        add_check("proposed_actions", "pass", f"{len(actions)} proposed actions found")

    mutation_action = None
    for item in actions if isinstance(actions, list) else []:
        if isinstance(item, dict) and item.get("module") == "MUTATION_POLICY":
            mutation_action = item
            break

    if not mutation_action:
        add_check("mutation_policy_action", "reject", "missing MUTATION_POLICY action")
    else:
        action_name = str(mutation_action.get("action", ""))
        if action_name == "keep_skill_changes_reviewed_only":
            add_check("mutation_policy_action", "pass", "proposal keeps reviewed-only mutation policy")
        else:
            add_check(
                "mutation_policy_action",
                "revise",
                f"MUTATION_POLICY action is '{action_name}', expected reviewed-only policy",
            )

    rollback_conditions = proposal.get("rollback_conditions", [])
    if isinstance(rollback_conditions, list) and len(rollback_conditions) >= 2:
        add_check("rollback_conditions", "pass", f"{len(rollback_conditions)} rollback conditions found")
    else:
        add_check("rollback_conditions", "revise", "rollback_conditions should include at least 2 entries")

    evidence_available = bool(proposal.get("evidence_available"))
    if evidence_available:
        add_check("evidence_available", "pass", "proposal was generated from readable benchmark evidence")
    else:
        add_check("evidence_available", "revise", "proposal was generated without readable benchmark evidence")

    benchmark_version = str(proposal.get("benchmark_version", "unknown")).strip() or "unknown"
    if benchmark_version == "unknown":
        add_check("benchmark_version", "revise", "benchmark_version is unknown")
    else:
        add_check("benchmark_version", "pass", f"benchmark_version={benchmark_version}")

    summary = proposal.get("benchmark_summary", {})
    task_count = _safe_int(summary.get("task_count"))
    min_task_count = _safe_int(config.get("min_task_count"), 8)
    if task_count >= min_task_count:
        add_check("benchmark_task_count", "pass", f"task_count={task_count}")
    else:
        add_check("benchmark_task_count", "revise", f"task_count={task_count}, expected >= {min_task_count}")

    completion_with = float(summary.get("completion_rate_with_skill") or 0.0)
    completion_without = float(summary.get("completion_rate_without_skill") or 0.0)
    completion_gap = completion_with - completion_without
    min_completion_gap_pp = float(config.get("min_completion_gap_pp", 1.0))
    if completion_gap >= min_completion_gap_pp:
        add_check("completion_gap_pp", "pass", f"completion_gap_pp={completion_gap:.2f}")
    else:
        add_check(
            "completion_gap_pp",
            "revise",
            f"completion_gap_pp={completion_gap:.2f}, expected >= {min_completion_gap_pp:.2f}",
        )

    quality_imp = float(summary.get("avg_quality_improvement_pct") or 0.0)
    min_quality_imp = float(config.get("min_quality_improvement_pct", 10.0))
    if quality_imp >= min_quality_imp:
        add_check("quality_improvement_pct", "pass", f"avg_quality_improvement_pct={quality_imp:.2f}")
    else:
        add_check(
            "quality_improvement_pct",
            "revise",
            f"avg_quality_improvement_pct={quality_imp:.2f}, expected >= {min_quality_imp:.2f}",
        )

    token_imp = float(summary.get("avg_token_improvement_pct") or 0.0)
    token_cost_increase = max(0.0, -token_imp)
    max_token_cost = float(config.get("max_token_cost_increase_pct", 220.0))
    if token_cost_increase <= max_token_cost:
        add_check("token_cost_increase_pct", "pass", f"token_cost_increase_pct={token_cost_increase:.2f}")
    else:
        add_check(
            "token_cost_increase_pct",
            "revise",
            f"token_cost_increase_pct={token_cost_increase:.2f}, limit={max_token_cost:.2f}",
        )

    if benchmark is not None:
        expected_version = str(
            (benchmark.get("experiment_info", {}) if isinstance(benchmark, dict) else {}).get(
                "benchmark_version", "unknown"
            )
        ).strip() or "unknown"
        if expected_version == "unknown":
            add_check("benchmark_reference", "revise", "benchmark reference does not include benchmark_version")
        elif benchmark_version != expected_version:
            add_check(
                "benchmark_reference",
                "reject",
                f"proposal benchmark_version={benchmark_version} != benchmark reference={expected_version}",
            )
        else:
            add_check("benchmark_reference", "pass", f"matches benchmark reference ({expected_version})")

    reject_hits = [c for c in checks if c["status"] == "reject"]
    revise_hits = [c for c in checks if c["status"] == "revise"]
    if reject_hits:
        decision = "reject"
    elif revise_hits:
        decision = "revise"
    else:
        decision = "approve"

    return {
        "proposal_path": proposal_path,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "policy_config": config,
        "checks": checks,
    }


def render_markdown(verification: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Skill Proposal Verification")
    lines.append("")
    lines.append(f"- Proposal: {verification.get('proposal_path')}")
    lines.append(f"- Verified At: {verification.get('verified_at')}")
    lines.append(f"- Decision: {verification.get('decision')}")
    lines.append("")
    lines.append("## Checks")
    for check in verification.get("checks", []):
        lines.append(f"- [{check.get('status')}] {check.get('name')}: {check.get('detail')}")
    lines.append("")
    lines.append("## Policy")
    lines.append("- `approve`: safe to use as reviewed proposal input.")
    lines.append("- `revise`: proposal can be kept for reference but should be revised before apply.")
    lines.append("- `reject`: do not proceed with this proposal.")
    return "\n".join(lines).strip() + "\n"


def write_verification_artifacts(
    proposal_path: str,
    *,
    benchmark_path: str | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    config_path: str | Path | None = None,
) -> VerificationArtifact:
    proposal_file = Path(proposal_path)
    if not proposal_file.exists():
        raise FileNotFoundError(f"proposal file does not exist: {proposal_file}")

    proposal = _load_json(proposal_file)
    benchmark = _load_json(Path(benchmark_path)) if benchmark_path else None
    verification = verify_proposal(
        proposal,
        proposal_path=str(proposal_file),
        benchmark=benchmark,
        config=load_config(config_path),
    )

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    stem = proposal_file.stem
    stamp = _now_stamp()
    json_path = output_root / f"{stem}_verify_{stamp}.json"
    markdown_path = output_root / f"{stem}_verify_{stamp}.md"

    json_path.write_text(json.dumps(verification, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_markdown(verification), encoding="utf-8")

    return VerificationArtifact(
        decision=str(verification.get("decision", "reject")),
        json_path=json_path,
        markdown_path=markdown_path,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a skill evolution proposal JSON artifact.")
    parser.add_argument("--proposal", required=True, help="Path to proposal JSON")
    parser.add_argument(
        "--benchmark",
        default="",
        help="Optional benchmark JSON reference for version consistency checks",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Verifier policy config (TOML)",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for verification artifacts")
    args = parser.parse_args(argv)

    artifact = write_verification_artifacts(
        args.proposal,
        benchmark_path=args.benchmark or None,
        output_dir=args.output_dir,
        config_path=args.config,
    )
    print(json.dumps({"decision": artifact.decision, "verification_path": str(artifact.json_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
