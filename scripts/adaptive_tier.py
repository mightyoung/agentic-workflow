#!/usr/bin/env python3
"""
Adaptive Tier Resolver — combines model_profiles static defaults with
skill_metrics historical data to produce data-driven activation level decisions.

Usage:
    from adaptive_tier import AdaptiveResolver, adaptive_activation_level

    level = adaptive_activation_level("EXECUTING", "M", model_id="claude-sonnet-4-6")

    resolver = AdaptiveResolver(workdir=".", min_samples=5)
    decision = resolver.resolve("EXECUTING", "M", model_id="claude-sonnet-4-6")
    print(decision.activation_level, decision.source, decision.confidence)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

_TIER_BUCKETS = (0, 25, 50, 75, 100)
_ESCALATION_FILE = ".tier_escalations.jsonl"

try:
    from model_profiles import get_profile, resolve_activation_level as _mp_resolve
    _HAS_MODEL_PROFILES = True
except Exception:  # pragma: no cover
    _HAS_MODEL_PROFILES = False

try:
    from skill_metrics import recommend_activation_level as _sm_recommend
    from skill_metrics import get_tier_effectiveness as _sm_effectiveness
    _HAS_SKILL_METRICS = True
except Exception:  # pragma: no cover
    _HAS_SKILL_METRICS = False


@dataclass(frozen=True)
class TierDecision:
    """Immutable result of an adaptive tier resolution."""

    activation_level: int
    source: str     # "default" | "adaptive" | "escalated" | "de-escalated"
    confidence: str  # "high" | "medium" | "low"
    reason: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _snap_to_bucket(level: float) -> int:
    """Round a float level to the nearest valid tier bucket (0/25/50/75/100)."""
    clamped = max(0, min(100, int(round(level))))
    return min(_TIER_BUCKETS, key=lambda b: abs(clamped - b))


def _default_level(phase: str, complexity: str, model_id: str | None) -> int:
    if not _HAS_MODEL_PROFILES:
        return 50
    try:
        return _mp_resolve(phase, complexity, get_profile(model_id), failure_count=0)
    except Exception:
        return 50


def _escalation_path(workdir: str) -> Path:
    return Path(workdir) / _ESCALATION_FILE


# ---------------------------------------------------------------------------
# AdaptiveResolver
# ---------------------------------------------------------------------------

class AdaptiveResolver:
    """Combine static model defaults with historical skill_metrics data."""

    def __init__(self, workdir: str = ".", min_samples: int = 5) -> None:
        self._workdir = workdir
        self._min_samples = min_samples

    def resolve(
        self,
        phase: str,
        complexity: str,
        model_id: str | None = None,
        failure_count: int = 0,
    ) -> TierDecision:
        """Resolve activation_level using historical data when available, default otherwise.

        Steps:
        1. Static default from model_profiles.
        2. Data-driven recommendation from skill_metrics.
        3. high confidence + differs → use recommended ("adaptive").
           medium confidence → weighted blend 0.6*rec + 0.4*default, snap to bucket.
           low / no data → keep default.
        4. failure_count >= 2 → escalate one tier up ("escalated").
        """
        phase = (phase or "").upper()
        complexity = (complexity or "").upper()

        default = _default_level(phase, complexity, model_id)
        chosen, source, confidence = default, "default", "low"
        reason = "Using static model-profile default (no historical data)."

        if _HAS_SKILL_METRICS:
            try:
                rec = _sm_recommend(phase, complexity, model_id=model_id, workdir=self._workdir)
                rec_level: int = rec.get("recommended_level", default)
                rec_conf: str = rec.get("confidence", "low")
                rec_reason: str = rec.get("reason", "")

                if rec_conf == "high" and rec_level != default:
                    chosen, source, confidence = rec_level, "adaptive", "high"
                    reason = f"High-confidence data: {rec_reason}"
                elif rec_conf == "medium":
                    blended = _snap_to_bucket(0.6 * rec_level + 0.4 * default)
                    chosen, source, confidence = blended, "adaptive", "medium"
                    reason = (
                        f"Medium-confidence blend "
                        f"(0.6×{rec_level} + 0.4×{default} → {blended}). {rec_reason}"
                    )
                else:
                    confidence = "low"
                    reason = f"Low data confidence, using default. {rec_reason}".strip()
            except Exception as exc:
                reason = f"skill_metrics unavailable ({exc}); using default."

        if failure_count >= 2:
            pre = chosen
            chosen = _snap_to_bucket(chosen + 25)
            source = "escalated"
            reason = (
                f"Failure escalation (failure_count={failure_count}): "
                f"{pre} → {chosen}. {reason}"
            )

        return TierDecision(activation_level=chosen, source=source,
                            confidence=confidence, reason=reason)

    def should_de_escalate(
        self,
        phase: str,
        current_level: int,
        model_id: str | None = None,
    ) -> TierDecision | None:
        """Return a de-escalation recommendation if the tier below meets quality bar, else None.

        Conditions: current_level > 25, lower tier avg_quality >= 0.7,
        and lower tier sample_count >= min_samples.
        """
        if current_level <= 25 or not _HAS_SKILL_METRICS:
            return None
        try:
            tier_stats = _sm_effectiveness(
                phase=phase, model_id=model_id,
                workdir=self._workdir, min_samples=self._min_samples,
            )
        except Exception:
            return None

        lower = _snap_to_bucket(current_level - 25)
        stats = tier_stats.get(lower) if tier_stats else None
        if stats and stats.avg_quality >= 0.7 and stats.sample_count >= self._min_samples:
            return TierDecision(
                activation_level=lower,
                source="de-escalated",
                confidence="medium",
                reason=(
                    f"Lower tier {lower} achieves avg_quality={stats.avg_quality:.2f} "
                    f"over {stats.sample_count} samples "
                    f"(threshold=0.7, min_samples={self._min_samples}). "
                    f"Recommend reducing from {current_level}."
                ),
            )
        return None

    def record_escalation(
        self,
        phase: str,
        from_level: int,
        to_level: int,
        reason: str,
    ) -> None:
        """Append a tier escalation/de-escalation event to .tier_escalations.jsonl."""
        entry: dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "phase": (phase or "").upper(),
            "from_level": from_level,
            "to_level": to_level,
            "reason": reason,
        }
        try:
            with open(_escalation_path(self._workdir), "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass  # best-effort


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def get_adaptation_summary(workdir: str = ".") -> dict[str, Any]:
    """Return counts and recent events from .tier_escalations.jsonl."""
    path = _escalation_path(workdir)
    if not path.exists():
        return {"total_events": 0, "escalation_count": 0, "de_escalation_count": 0,
                "phase_breakdown": {}, "recent_events": []}

    events: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    phase_breakdown: dict[str, int] = {}
    for e in events:
        ph = str(e.get("phase", "UNKNOWN"))
        phase_breakdown[ph] = phase_breakdown.get(ph, 0) + 1

    return {
        "total_events": len(events),
        "escalation_count": sum(1 for e in events if e.get("to_level", 0) > e.get("from_level", 0)),
        "de_escalation_count": sum(1 for e in events if e.get("to_level", 0) < e.get("from_level", 0)),
        "phase_breakdown": phase_breakdown,
        "recent_events": events[-5:],
    }


def adaptive_activation_level(
    phase: str,
    complexity: str,
    model_id: str | None = None,
    failure_count: int = 0,
    workdir: str = ".",
) -> int:
    """One-liner for callers that just want the resolved activation level."""
    return AdaptiveResolver(workdir).resolve(phase, complexity, model_id, failure_count).activation_level


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Adaptive Tier Resolver — combines model defaults with historical skill data")
    parser.add_argument("--workdir", default=".")
    parser.add_argument("--op", required=True,
                        choices=["resolve", "de-escalate", "record", "summary"])
    parser.add_argument("--phase", default="EXECUTING")
    parser.add_argument("--complexity", default="M")
    parser.add_argument("--model", default=None)
    parser.add_argument("--failures", type=int, default=0)
    parser.add_argument("--current-level", type=int, default=50)
    parser.add_argument("--to-level", type=int, default=None)
    parser.add_argument("--reason", default="")
    parser.add_argument("--min-samples", type=int, default=5)
    args = parser.parse_args()

    resolver = AdaptiveResolver(workdir=args.workdir, min_samples=args.min_samples)

    if args.op == "resolve":
        d = resolver.resolve(args.phase, args.complexity, args.model, args.failures)
        print(json.dumps({"activation_level": d.activation_level, "source": d.source,
                          "confidence": d.confidence, "reason": d.reason},
                         ensure_ascii=False, indent=2))

    elif args.op == "de-escalate":
        d = resolver.should_de_escalate(args.phase, args.current_level, args.model)
        if d is None:
            print(json.dumps({"de_escalate": False, "reason": "No de-escalation warranted."},
                             ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"de_escalate": True, "recommended_level": d.activation_level,
                              "confidence": d.confidence, "reason": d.reason},
                             ensure_ascii=False, indent=2))

    elif args.op == "record":
        to_level = args.to_level if args.to_level is not None else args.current_level
        resolver.record_escalation(args.phase, args.current_level, to_level, args.reason)
        print(json.dumps({"recorded": True, "phase": args.phase.upper(),
                          "from_level": args.current_level, "to_level": to_level},
                         ensure_ascii=False))

    elif args.op == "summary":
        print(json.dumps(get_adaptation_summary(args.workdir), ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
