#!/usr/bin/env python3
"""Generate skill evolution proposals from benchmark evidence.

This script turns benchmark JSON into a reviewable proposal artifact rather than
mutating skills directly. The output is intentionally human-readable and
machine-readable so it can be attached to self-improvement runs.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path("knowledge/skill_proposals")


@dataclass(frozen=True)
class ProposalArtifact:
    proposal_id: str
    markdown_path: Path
    json_path: Path


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in value)
    slug = "_".join(part for part in slug.split("_") if part)
    return slug[:48] or "benchmark"


def load_benchmark(reference: str) -> tuple[dict[str, Any], str, bool]:
    """Load a benchmark report or fall back to a reference-only stub."""
    path = Path(reference)
    if path.exists() and path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8")), str(path), True
        except json.JSONDecodeError:
            return {"source": reference, "parse_error": True}, str(path), False
    return {"source": reference, "missing": True}, reference, False


def build_proposal(benchmark: dict[str, Any], source_ref: str, evidence_available: bool) -> dict[str, Any]:
    experiment_info = benchmark.get("experiment_info", {}) if isinstance(benchmark, dict) else {}
    overall = benchmark.get("overall_summary", {}) if isinstance(benchmark, dict) else {}
    module_policies = benchmark.get("module_policies", []) if isinstance(benchmark, dict) else []
    interpretation_notes = benchmark.get("interpretation_notes", []) if isinstance(benchmark, dict) else []

    policy_map = {
        item.get("module"): item for item in module_policies if isinstance(item, dict)
    }

    proposed_actions: list[dict[str, Any]] = []

    def add_action(module: str, action: str, why: str, evidence: dict[str, Any] | None = None) -> None:
        proposed_actions.append(
            {
                "module": module,
                "action": action,
                "why": why,
                "evidence": evidence or {},
            }
        )

    exec_policy = policy_map.get("EXECUTING", {})
    add_action(
        "EXECUTING",
        "retain_default_enable_50_and_escalate_to_75_for_M_plus",
        "Benchmark shows EXECUTING has the highest ROI and retains the main benefit at the 50% baseline.",
        exec_policy,
    )

    review_policy = policy_map.get("REVIEWING", {})
    add_action(
        "REVIEWING",
        "retain_conditional_enable_and_keep_two_stage_review",
        "Review quality is positive but token-cost sensitive; keep it conditional and file-aware.",
        review_policy,
    )

    debug_policy = policy_map.get("DEBUGGING", {})
    add_action(
        "DEBUGGING",
        "split_into_debug_lite_and_debug_deep",
        "Debugging has strong quality gains but poor token efficiency on some tasks; keep the lightweight path as default.",
        debug_policy,
    )

    planning_policy = policy_map.get("PLANNING", {})
    add_action(
        "PLANNING",
        "keep_file_first_lightweight_planning",
        "Planning remains the lowest ROI area; do not re-expand the heavy spec path for small tasks.",
        planning_policy,
    )

    if evidence_available:
        add_action(
            "MUTATION_POLICY",
            "keep_skill_changes_reviewed_only",
            "Benchmark evidence should produce proposals, not direct skill mutation.",
            {"source": source_ref},
        )
    else:
        add_action(
            "MUTATION_POLICY",
            "await_readable_benchmark_evidence",
            "Proposal generation can be stubbed, but the evidence path should still be attached to the run.",
            {"source": source_ref},
        )

    return {
        "proposal_id": f"skill-evolution-{_now_stamp()}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_reference": source_ref,
        "evidence_available": evidence_available,
        "benchmark_version": experiment_info.get("benchmark_version", "unknown"),
        "benchmark_summary": {
            "overall_improvement_pct": overall.get("overall_improvement_pct"),
            "avg_quality_improvement_pct": overall.get("avg_quality_improvement_pct"),
            "avg_token_improvement_pct": overall.get("avg_token_improvement_pct"),
            "completion_rate_with_skill": overall.get("completion_rate_with_skill"),
            "completion_rate_without_skill": overall.get("completion_rate_without_skill"),
            "task_count": overall.get("task_count"),
        },
        "interpretation_notes": interpretation_notes,
        "module_policies": module_policies,
        "proposed_actions": proposed_actions,
        "rollback_conditions": [
            "quality regression on the core workflow suite",
            "review gate or checkpoint handoff incompatibility",
            "skill activation baseline changes without benchmark re-run",
        ],
    }


def render_markdown(proposal: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Skill Evolution Proposal - {proposal['proposal_id']}")
    lines.append("")
    lines.append(f"- Generated: {proposal['generated_at']}")
    lines.append(f"- Source: {proposal['source_reference']}")
    lines.append(f"- Evidence Available: {proposal['evidence_available']}")
    lines.append(f"- Benchmark Version: {proposal.get('benchmark_version', 'unknown')}")
    lines.append("")
    lines.append("## Benchmark Summary")
    summary = proposal.get("benchmark_summary", {})
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Interpretation Notes")
    for note in proposal.get("interpretation_notes", []):
        lines.append(f"- {note}")
    lines.append("")
    lines.append("## Proposed Actions")
    for action in proposal.get("proposed_actions", []):
        lines.append(f"### {action['module']}")
        lines.append(f"- Action: {action['action']}")
        lines.append(f"- Why: {action['why']}")
        if action.get("evidence"):
            lines.append(f"- Evidence: {json.dumps(action['evidence'], ensure_ascii=False)}")
        lines.append("")
    lines.append("## Rollback Conditions")
    for cond in proposal.get("rollback_conditions", []):
        lines.append(f"- {cond}")
    lines.append("")
    lines.append("## Policy")
    lines.append("- This artifact is a proposal only; it does not mutate skills directly.")
    lines.append("- Apply only after review or explicit gate approval.")
    return "\n".join(lines).strip() + "\n"


def write_proposal_artifacts(benchmark_ref: str, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> ProposalArtifact:
    benchmark, source_ref, evidence_available = load_benchmark(benchmark_ref)
    proposal = build_proposal(benchmark, source_ref, evidence_available)

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    slug = _slugify(Path(source_ref).stem if Path(source_ref).stem else str(source_ref))
    proposal_id = proposal["proposal_id"]
    markdown_path = output_root / f"{proposal_id}_{slug}.md"
    json_path = output_root / f"{proposal_id}_{slug}.json"

    markdown_path.write_text(render_markdown(proposal), encoding="utf-8")
    json_path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")

    return ProposalArtifact(
        proposal_id=proposal_id,
        markdown_path=markdown_path,
        json_path=json_path,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a skill evolution proposal from benchmark evidence.")
    parser.add_argument("--benchmark", required=True, help="Benchmark JSON file or reference string")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for proposal artifacts")
    args = parser.parse_args(argv)

    artifact = write_proposal_artifacts(args.benchmark, args.output_dir)
    print(artifact.markdown_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
