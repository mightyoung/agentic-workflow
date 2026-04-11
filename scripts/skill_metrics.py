#!/usr/bin/env python3
"""
Skill Metrics — Outcome Recording and Quality Scoring for Skill Tier Injection.

Phase 3 of the skill improvement pipeline (Phase 4 will auto-adjust tiers):
  skill_assembler.py  → assemble tiered prompts
  skill_telemetry.py  → track usage frequency
  skill_metrics.py    → record outcomes + quality scoring  ← this file

Usage:
    from skill_metrics import (
        SkillOutcome, record_skill_outcome,
        compute_quality_score, get_tier_effectiveness,
        recommend_activation_level,
    )
    outcome = SkillOutcome(
        success=True,
        quality_score=compute_quality_score(True, 0, test_pass_rate=0.95),
        token_input=450, token_output=800, duration_ms=2100,
        failure_count=0, error_type=None,
    )
    record_skill_outcome("EXECUTING", 50, "claude-sonnet-4-6", "M", outcome)
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

SKILL_METRICS_FILE = ".skill_metrics.jsonl"

_TIER_BUCKETS = (0, 25, 50, 75, 100)
_DEFAULT_MIN_SAMPLES = 3
_QUALITY_THRESHOLD = 0.6


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SkillOutcome:
    """Immutable snapshot of a single skill-injected task outcome."""

    success: bool           # task completed without final failure?
    quality_score: float    # 0.0-1.0, pre-computed from signals
    token_input: int        # skill prompt tokens injected
    token_output: int       # LLM response tokens (0 if unavailable)
    duration_ms: int        # wall-clock execution time in milliseconds
    failure_count: int      # retries before success or give-up
    error_type: str | None  # error category if failed, else None


@dataclass(frozen=True)
class TierStats:
    """Aggregated quality statistics for one activation_level bucket."""

    activation_level: int
    sample_count: int
    avg_quality: float
    avg_tokens: int
    success_rate: float
    avg_duration_ms: int
    cost_efficiency: float  # avg_quality / avg_tokens


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _metrics_path(workdir: str) -> Path:
    return Path(workdir) / SKILL_METRICS_FILE


def _load_metrics(workdir: str = ".") -> list[dict[str, Any]]:
    path = _metrics_path(workdir)
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _snap_to_bucket(level: int) -> int:
    """Round activation_level to the nearest tier bucket (0/25/50/75/100)."""
    return min(_TIER_BUCKETS, key=lambda b: abs(max(0, min(100, level)) - b))


# ---------------------------------------------------------------------------
# 1. Outcome Recording
# ---------------------------------------------------------------------------

def record_skill_outcome(
    phase: str,
    activation_level: int,
    model_id: str | None,
    complexity: str,
    outcome: SkillOutcome,
    workdir: str = ".",
) -> bool:
    """Append one outcome record to the JSONL metrics file.

    Returns True if the entry was written successfully.
    """
    entry: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "phase": (phase or "").upper(),
        "activation_level": _snap_to_bucket(activation_level),
        "model_id": model_id or "unknown",
        "complexity": (complexity or "").upper(),
        "success": outcome.success,
        "quality_score": round(outcome.quality_score, 4),
        "token_input": outcome.token_input,
        "token_output": outcome.token_output,
        "duration_ms": outcome.duration_ms,
        "failure_count": outcome.failure_count,
        "error_type": outcome.error_type,
    }
    try:
        with open(_metrics_path(workdir), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# 2. Quality Scoring
# ---------------------------------------------------------------------------

def compute_quality_score(
    success: bool,
    failure_count: int,
    test_pass_rate: float | None = None,
    review_issues: int = 0,
    user_accepted: bool | None = None,
) -> float:
    """Compute a 0.0-1.0 quality score from task outcome signals.

    Weights (sum to 1.0):
      success          0.4  binary
      failure penalty  0.2  1.0/0.5/0.25/0.0 for 0/1/2/3+ failures
      test_pass_rate   0.2  raw value; neutral 0.5 if None
      review_issues    0.1  1.0 if 0, 0.5 if 1-2, 0.0 if 3+
      user_accepted    0.1  raw bool; neutral 0.5 if None
    """
    failure_score = {0: 1.0, 1: 0.5, 2: 0.25}.get(failure_count, 0.0)
    test_score = test_pass_rate if test_pass_rate is not None else 0.5
    review_score = 1.0 if review_issues == 0 else (0.5 if review_issues <= 2 else 0.0)
    user_score = (1.0 if user_accepted else 0.0) if user_accepted is not None else 0.5

    raw = (
        0.4 * (1.0 if success else 0.0)
        + 0.2 * failure_score
        + 0.2 * test_score
        + 0.1 * review_score
        + 0.1 * user_score
    )
    return max(0.0, min(1.0, raw))


# ---------------------------------------------------------------------------
# 3. Tier Effectiveness Analysis
# ---------------------------------------------------------------------------

def get_tier_effectiveness(
    phase: str | None = None,
    model_id: str | None = None,
    workdir: str = ".",
    min_samples: int = _DEFAULT_MIN_SAMPLES,
) -> dict[int, TierStats]:
    """Group outcome records by activation_level bucket and compute aggregates.

    Returns a dict mapping level (0/25/50/75/100) → TierStats.
    Buckets with fewer than min_samples entries are excluded.
    """
    entries = _load_metrics(workdir)
    buckets: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for entry in entries:
        if phase and entry.get("phase") != phase.upper():
            continue
        if model_id and entry.get("model_id") != model_id:
            continue
        buckets[entry.get("activation_level", 0)].append(entry)

    result: dict[int, TierStats] = {}
    for level, rows in buckets.items():
        if len(rows) < min_samples:
            continue
        n = len(rows)
        avg_quality = sum(r.get("quality_score", 0.0) for r in rows) / n
        avg_tokens = int(sum(r.get("token_input", 0) for r in rows) / n)
        success_rate = sum(1 for r in rows if r.get("success")) / n
        avg_duration_ms = int(sum(r.get("duration_ms", 0) for r in rows) / n)
        cost_efficiency = avg_quality / max(1, avg_tokens)
        result[level] = TierStats(
            activation_level=level,
            sample_count=n,
            avg_quality=round(avg_quality, 4),
            avg_tokens=avg_tokens,
            success_rate=round(success_rate, 4),
            avg_duration_ms=avg_duration_ms,
            cost_efficiency=round(cost_efficiency, 8),
        )
    return result


# ---------------------------------------------------------------------------
# 4. Adaptive Recommendation
# ---------------------------------------------------------------------------

def recommend_activation_level(
    phase: str,
    complexity: str,
    model_id: str | None = None,
    workdir: str = ".",
) -> dict[str, Any]:
    """Recommend the best activation_level based on historical outcome data.

    If insufficient data → return current_default with confidence="low".
    Otherwise pick the tier with the best cost_efficiency above quality
    threshold 0.6; if none qualify, escalate to the highest recorded tier.

    Return keys: recommended_level, current_default, confidence, reason, tier_stats
    """
    try:
        from model_profiles import get_profile, resolve_activation_level
        current_default = resolve_activation_level(phase, complexity, get_profile(model_id))
    except Exception:
        current_default = 50

    tier_stats = get_tier_effectiveness(phase=phase, model_id=model_id, workdir=workdir)
    tier_quality_map: dict[int, float] = {lvl: s.avg_quality for lvl, s in tier_stats.items()}

    if not tier_stats:
        return {
            "recommended_level": current_default,
            "current_default": current_default,
            "confidence": "low",
            "reason": "Insufficient data: no tier has enough samples yet.",
            "tier_stats": tier_quality_map,
        }

    total = sum(s.sample_count for s in tier_stats.values())
    confidence = "low" if total < 10 else ("medium" if total < 30 else "high")

    qualifying = {
        lvl: s for lvl, s in tier_stats.items() if s.avg_quality >= _QUALITY_THRESHOLD
    }

    if qualifying:
        best_level = max(qualifying, key=lambda lvl: qualifying[lvl].cost_efficiency)
        best = qualifying[best_level]
        reason = (
            f"Level {best_level} achieves quality={best.avg_quality:.2f} "
            f"at cost_efficiency={best.cost_efficiency:.6f} ({best.sample_count} samples)."
        )
    else:
        best_level = max(tier_stats.keys())
        reason = (
            f"No tier meets quality threshold {_QUALITY_THRESHOLD}. "
            f"Escalating to highest observed tier ({best_level})."
        )

    return {
        "recommended_level": best_level,
        "current_default": current_default,
        "confidence": confidence,
        "reason": reason,
        "tier_stats": tier_quality_map,
    }


# ---------------------------------------------------------------------------
# Summary helper
# ---------------------------------------------------------------------------

def get_metrics_summary(workdir: str = ".") -> dict[str, Any]:
    """Return a high-level summary of all recorded outcomes."""
    entries = _load_metrics(workdir)
    if not entries:
        return {"total_records": 0}
    n = len(entries)
    phase_counts: dict[str, int] = defaultdict(int)
    tier_counts: dict[int, int] = defaultdict(int)
    for e in entries:
        phase_counts[e.get("phase", "unknown")] += 1
        tier_counts[e.get("activation_level", 0)] += 1
    return {
        "total_records": n,
        "overall_success_rate": round(sum(1 for e in entries if e.get("success")) / n, 4),
        "overall_avg_quality": round(sum(e.get("quality_score", 0.0) for e in entries) / n, 4),
        "phase_breakdown": dict(phase_counts),
        "tier_breakdown": dict(tier_counts),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Skill Metrics — outcome recording and quality scoring")
    parser.add_argument("--workdir", default=".")
    parser.add_argument("--op", required=True,
                        choices=["record", "quality", "effectiveness", "recommend", "summary"])
    parser.add_argument("--phase", help="Phase name (e.g., EXECUTING)")
    parser.add_argument("--level", type=int, default=50, help="Activation level 0-100")
    parser.add_argument("--model", default=None, help="Model ID")
    parser.add_argument("--complexity", default="M", help="XS/S/M/L/XL")
    parser.add_argument("--success", action="store_true", default=False)
    parser.add_argument("--failures", type=int, default=0)
    parser.add_argument("--token-input", type=int, default=0)
    parser.add_argument("--token-output", type=int, default=0)
    parser.add_argument("--duration-ms", type=int, default=0)
    parser.add_argument("--error-type", default=None)
    parser.add_argument("--test-pass-rate", type=float, default=None)
    parser.add_argument("--review-issues", type=int, default=0)
    parser.add_argument("--user-accepted", action="store_true", default=None)
    parser.add_argument("--min-samples", type=int, default=_DEFAULT_MIN_SAMPLES)
    args = parser.parse_args()

    if args.op == "record":
        if not args.phase:
            print("Error: --phase required for record")
            return 1
        quality = compute_quality_score(
            success=args.success, failure_count=args.failures,
            test_pass_rate=args.test_pass_rate, review_issues=args.review_issues,
        )
        outcome = SkillOutcome(
            success=args.success, quality_score=quality,
            token_input=args.token_input, token_output=args.token_output,
            duration_ms=args.duration_ms, failure_count=args.failures,
            error_type=args.error_type,
        )
        ok = record_skill_outcome(args.phase, args.level, args.model,
                                  args.complexity, outcome, args.workdir)
        print(json.dumps({"recorded": ok, "quality_score": quality}))

    elif args.op == "quality":
        score = compute_quality_score(
            success=args.success, failure_count=args.failures,
            test_pass_rate=args.test_pass_rate, review_issues=args.review_issues,
        )
        print(json.dumps({"quality_score": score}))

    elif args.op == "effectiveness":
        stats = get_tier_effectiveness(
            phase=args.phase, model_id=args.model,
            workdir=args.workdir, min_samples=args.min_samples,
        )
        print(json.dumps({
            str(lvl): {
                "activation_level": s.activation_level, "sample_count": s.sample_count,
                "avg_quality": s.avg_quality, "avg_tokens": s.avg_tokens,
                "success_rate": s.success_rate, "avg_duration_ms": s.avg_duration_ms,
                "cost_efficiency": s.cost_efficiency,
            }
            for lvl, s in stats.items()
        }, ensure_ascii=False, indent=2))

    elif args.op == "recommend":
        if not args.phase:
            print("Error: --phase required for recommend")
            return 1
        print(json.dumps(
            recommend_activation_level(args.phase, args.complexity, args.model, args.workdir),
            ensure_ascii=False, indent=2,
        ))

    elif args.op == "summary":
        print(json.dumps(get_metrics_summary(args.workdir), ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
