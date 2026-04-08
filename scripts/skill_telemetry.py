#!/usr/bin/env python3
"""
Skill Telemetry - SKILL0-inspired Skill Usage Tracking

Tracks which skills are used across phases, identifies high-frequency patterns,
and recommends which skills should be "internalized" (compressed into canonical rules).

SKILL0 insight:高频 skill usage suggests the pattern should be internalized,
reducing inference-time retrieval overhead and token cost.

Usage:
    from skill_telemetry import (
        record_skill_usage,
        get_skill_frequency,
        get_internalization_recommendations,
    )

    # Record that planning phase used "planning" skill
    record_skill_usage("planning", "PLANNING")

    # Get high-frequency skills that should be internalized
    recommendations = get_internalization_recommendations(limit=5)
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Skill telemetry storage
SKILL_TELEMETRY_FILE = ".skill_telemetry.jsonl"

# Thresholds for internalization recommendation
# A skill is a candidate if:
#   - Used >= INTERNALIZATION_USAGE_THRESHOLD times
#   - AND usage span <= INTERNALIZATION_TIME_MONTHS months
INTERNALIZATION_USAGE_THRESHOLD = 5
INTERNALIZATION_TIME_MONTHS = 3


def record_skill_usage(
    skill_name: str,
    phase: str,
    workdir: str = ".",
    metadata: dict[str, Any] | None = None,
) -> bool:
    """Record that a skill was used during a phase.

    Args:
        skill_name: Name of the skill (e.g., "planning", "reviewing")
        phase: Workflow phase the skill was used in
        workdir: Working directory
        metadata: Optional metadata (session_id, outcome, etc.)

    Returns:
        True if recorded successfully
    """
    telemetry_path = Path(workdir) / SKILL_TELEMETRY_FILE
    entry = {
        "timestamp": datetime.now().isoformat(),
        "skill_name": skill_name,
        "phase": phase,
        "metadata": metadata or {},
    }

    try:
        with open(telemetry_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


def _load_telemetry(workdir: str = ".") -> list[dict[str, Any]]:
    """Load all telemetry entries."""
    telemetry_path = Path(workdir) / SKILL_TELEMETRY_FILE
    if not telemetry_path.exists():
        return []

    entries = []
    with open(telemetry_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def get_skill_frequency(
    workdir: str = ".",
    scope_months: int | None = None,
) -> dict[str, dict[str, Any]]:
    """Get skill usage frequency statistics.

    Args:
        workdir: Working directory
        scope_months: If set, only count entries from last N months

    Returns:
        Dict mapping skill_name -> {count, phases, last_used, first_used}
    """
    entries = _load_telemetry(workdir)
    if not entries:
        return {}

    now = datetime.now()
    cutoff = None
    if scope_months:
        from datetime import timedelta
        cutoff = now - timedelta(days=scope_months * 30)

    stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "phases": set(), "last_used": None, "first_used": None}
    )

    for entry in entries:
        if cutoff:
            try:
                ts = datetime.fromisoformat(entry["timestamp"])
                if ts < cutoff:
                    continue
            except (ValueError, TypeError):
                continue

        skill_name = entry.get("skill_name", "unknown")
        phase = entry.get("phase", "unknown")
        ts = entry.get("timestamp", "")

        stats[skill_name]["count"] += 1
        stats[skill_name]["phases"].add(phase)

        if ts:
            if not stats[skill_name]["last_used"] or ts > stats[skill_name]["last_used"]:
                stats[skill_name]["last_used"] = ts
            if not stats[skill_name]["first_used"] or ts < stats[skill_name]["first_used"]:
                stats[skill_name]["first_used"] = ts

    # Convert sets to lists for JSON serialization
    return {
        name: {
            "count": data["count"],
            "phases": list(data["phases"]),
            "last_used": data["last_used"],
            "first_used": data["first_used"],
        }
        for name, data in stats.items()
    }


def get_high_frequency_skills(
    workdir: str = ".",
    min_count: int = 3,
    scope_months: int = 2,
) -> list[tuple[str, dict[str, Any]]]:
    """Get skills sorted by usage frequency.

    Returns:
        List of (skill_name, stats) sorted by count descending
    """
    freq = get_skill_frequency(workdir, scope_months=scope_months)
    filtered = [(name, data) for name, data in freq.items() if data["count"] >= min_count]
    filtered.sort(key=lambda x: x[1]["count"], reverse=True)
    return filtered


def get_internalization_recommendations(
    workdir: str = ".",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Get skills that should be "internalized" (compressed into canonical rules).

    SKILL0 principle:高频 usage patterns should be internalized to reduce
    inference-time skill retrieval overhead.

    A skill is recommended for internalization if:
    1. Usage count >= INTERNALIZATION_USAGE_THRESHOLD in recent window
    2. Time span of usage <= INTERNALIZATION_TIME_MONTHS
    3. Usage is consistent (not one-off)

    Returns:
        List of {skill_name, count, time_span_days, recommendation, priority} sorted by priority
    """
    freq = get_skill_frequency(workdir, scope_months=INTERNALIZATION_TIME_MONTHS)

    recommendations = []
    for skill_name, stats in freq.items():
        count = stats["count"]
        if count < INTERNALIZATION_USAGE_THRESHOLD:
            continue

        first_used = stats.get("first_used")
        last_used = stats.get("last_used")
        if not first_used or not last_used:
            continue

        try:
            first_dt = datetime.fromisoformat(first_used)
            last_dt = datetime.fromisoformat(last_used)
            time_span_days = (last_dt - first_dt).days
        except (ValueError, TypeError):
            time_span_days = 999

        # Compute priority score
        # Higher = more urgent to internalize
        usage_rate = count / max(1, time_span_days) * 30  # Monthly usage rate
        priority = usage_rate * (count / 10)  # Weight by absolute count

        # Recommendation text
        if time_span_days <= 7:
            rec = f"High-velocity skill ({count}x in {time_span_days}d). Strong candidate for internalization."
        elif time_span_days <= INTERNALIZATION_TIME_MONTHS * 30:
            rec = f"Frequent skill ({count}x over {time_span_days}d). Consider internalizing core patterns."
        else:
            rec = f"Steady usage ({count}x). May benefit from selective internalization."

        recommendations.append({
            "skill_name": skill_name,
            "count": count,
            "time_span_days": time_span_days,
            "phases": stats["phases"],
            "monthly_usage_rate": round(usage_rate, 2),
            "recommendation": rec,
            "priority": round(priority, 3),
        })

    recommendations.sort(key=lambda x: x["priority"], reverse=True)
    return recommendations[:limit]


def extract_skill_patterns(
    skill_name: str,
    workdir: str = ".",
) -> dict[str, Any]:
    """Extract common patterns from a specific skill's usage history.

    Returns:
        Dict with phase distribution, common metadata keys, etc.
    """
    entries = _load_telemetry(workdir)
    skill_entries = [e for e in entries if e.get("skill_name") == skill_name]

    phase_dist: dict[str, int] = defaultdict(int)
    metadata_keys: set[str] = set()
    outcomes: list[str] = []

    for entry in skill_entries:
        phase_dist[entry.get("phase", "unknown")] += 1
        meta = entry.get("metadata", {})
        metadata_keys.update(meta.keys())
        if meta.get("outcome"):
            outcomes.append(meta["outcome"])

    return {
        "skill_name": skill_name,
        "total_uses": len(skill_entries),
        "phase_distribution": dict(phase_dist),
        "common_metadata_keys": list(metadata_keys),
        "outcomes": outcomes[:10],  # Last 10 outcomes
    }


def get_skill_telemetry_summary(workdir: str = ".") -> dict[str, Any]:
    """Get a comprehensive telemetry summary."""
    freq = get_skill_frequency(workdir)
    high_freq = get_high_frequency_skills(workdir, min_count=2)
    recommendations = get_internalization_recommendations(workdir, limit=5)

    return {
        "total_skills_tracked": len(freq),
        "total_usage_events": sum(d["count"] for d in freq.values()),
        "high_frequency_skills": [
            {"skill": name, "count": data["count"], "phases": data["phases"]}
            for name, data in high_freq[:5]
        ],
        "internalization_recommendations": recommendations,
        "top_phases": _get_top_phases(freq),
    }


def _get_top_phases(freq: dict[str, dict[str, Any]]) -> list[tuple[str, int]]:
    """Get phases sorted by total skill usage."""
    phase_counts: dict[str, int] = defaultdict(int)
    for data in freq.values():
        for phase in data["phases"]:
            phase_counts[phase] += data["count"]
    return sorted(phase_counts.items(), key=lambda x: x[1], reverse=True)[:5]


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Skill Telemetry - SKILL0 Usage Tracking")
    parser.add_argument("--workdir", default=".")
    parser.add_argument("--op", choices=[
        "record", "frequency", "high-frequency", "recommendations", "patterns", "summary",
    ], required=True)
    parser.add_argument("--skill", help="Skill name for pattern extraction")
    parser.add_argument("--phase", help="Phase for recording")
    parser.add_argument("--min-count", type=int, default=3)
    parser.add_argument("--scope-months", type=int, default=2)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--outcome", help="Outcome metadata for recording")
    args = parser.parse_args()

    if args.op == "record":
        if not args.skill or not args.phase:
            print("Error: --skill and --phase required for record")
            return 1
        result = record_skill_usage(
            args.skill,
            args.phase,
            workdir=args.workdir,
            metadata={"outcome": args.outcome} if args.outcome else {},
        )
        print(json.dumps({"recorded": result}))
    elif args.op == "frequency":
        freq = get_skill_frequency(args.workdir, scope_months=args.scope_months)
        print(json.dumps(freq, ensure_ascii=False, indent=2))
    elif args.op == "high-frequency":
        skills = get_high_frequency_skills(args.workdir, min_count=args.min_count, scope_months=args.scope_months)
        print(json.dumps(skills, ensure_ascii=False, indent=2))
    elif args.op == "recommendations":
        recs = get_internalization_recommendations(args.workdir, limit=args.limit)
        print(json.dumps(recs, ensure_ascii=False, indent=2))
    elif args.op == "patterns":
        if not args.skill:
            print("Error: --skill required for patterns")
            return 1
        patterns = extract_skill_patterns(args.skill, args.workdir)
        print(json.dumps(patterns, ensure_ascii=False, indent=2))
    elif args.op == "summary":
        print(json.dumps(get_skill_telemetry_summary(args.workdir), ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
