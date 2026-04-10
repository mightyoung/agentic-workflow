#!/usr/bin/env python3
"""Verify skill evolution proposals before they are consumed by improvement runs."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("knowledge/skill_proposals/verifications")


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


def verify_proposal(
    proposal: dict[str, Any],
    *,
    proposal_path: str,
    benchmark: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

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
    if task_count > 0:
        add_check("benchmark_task_count", "pass", f"task_count={task_count}")
    else:
        add_check("benchmark_task_count", "revise", "task_count is missing or zero")

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
) -> VerificationArtifact:
    proposal_file = Path(proposal_path)
    if not proposal_file.exists():
        raise FileNotFoundError(f"proposal file does not exist: {proposal_file}")

    proposal = _load_json(proposal_file)
    benchmark = _load_json(Path(benchmark_path)) if benchmark_path else None
    verification = verify_proposal(proposal, proposal_path=str(proposal_file), benchmark=benchmark)

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
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for verification artifacts")
    args = parser.parse_args(argv)

    artifact = write_verification_artifacts(
        args.proposal,
        benchmark_path=args.benchmark or None,
        output_dir=args.output_dir,
    )
    print(json.dumps({"decision": artifact.decision, "verification_path": str(artifact.json_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
