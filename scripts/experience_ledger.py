#!/usr/bin/env python3
"""
Experience Ledger - Reflexion-style Experience Aggregation

Aggregates failure patterns across sessions and provides actionable
experience recommendations before planning/review/debug actions.

Built on top of .memory_index.jsonl (MAGMA memory layer).

Usage:
    from experience_ledger import (
        check_experience_before_action,
        get_actionable_experience,
        get_failure_patterns,
        get_experience_summary,
    )

    # Before planning a complex task
    experience = check_experience_before_action("planning", task_description)

    # Get actionable patterns for debug
    patterns = get_failure_patterns(error_type="test_failure", limit=5)
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import Any

# MAGMA memory index ( Reflexion-format experiences)
MEMORY_INDEX_FILE = ".memory_index.jsonl"
EXPERIENCE_LEDGER_FILE = ".experience_ledger.json"


# ── Reflexion Field Parsing ─────────────────────────────────────────────────

_REFLEXION_KEYS = ("task", "trigger", "mistake", "fix", "signal")
_REFLEXION_BOUNDARY = "|".join(k + ":" for k in _REFLEXION_KEYS)


def _parse_reflexion_fields(text: str) -> dict[str, str]:
    """Parse Reflexion-format fields from text.

    Supports: Task:X Trigger:Y Mistake:Z Fix:W Signal:S
    Field order不限，大小写不限。
    """
    fields: dict[str, str] = {}
    for key in _REFLEXION_KEYS:
        pattern = rf"(?i){key}:(.+?)(?=\s+(?:{_REFLEXION_BOUNDARY})|$)"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            value = match.group(1).strip()
            if value:
                fields[key] = value
    return fields


# ── Experience Aggregation ──────────────────────────────────────────────────


def _load_experiences() -> list[dict[str, Any]]:
    """Load all Reflexion-format experiences from memory index."""
    if not os.path.exists(MEMORY_INDEX_FILE):
        return []
    experiences = []
    with open(MEMORY_INDEX_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("type") == "experience" and entry.get("tags") and "reflexion" in entry["tags"]:
                    experiences.append(entry)
            except json.JSONDecodeError:
                continue
    return experiences


def get_failure_patterns(
    error_type: str | None = None,
    trigger_contains: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Get aggregated failure patterns from the experience ledger.

    Args:
        error_type: Filter by error type (e.g., "test_failure", "syntax_error")
        trigger_contains: Filter by trigger keyword
        limit: Maximum number of patterns to return

    Returns:
        List of failure patterns with fix suggestions, sorted by frequency
    """
    experiences = _load_experiences()
    if not experiences:
        return []

    # Group by signal/trigger for aggregation
    pattern_buckets: dict[str, dict[str, Any]] = {}
    for exp in experiences:
        text = exp.get("text", "")
        fields = _parse_reflexion_fields(text)
        if not fields:
            continue

        signal = fields.get("signal", "unknown")[:80].lower()
        trigger = fields.get("trigger", "unknown")[:80].lower()
        fix = fields.get("fix", "")
        mistake = fields.get("mistake", "")

        # Apply filters
        if error_type and error_type.lower() not in signal.lower() and error_type.lower() not in trigger.lower():
            continue
        if trigger_contains and trigger_contains.lower() not in trigger.lower():
            continue

        bucket_key = f"{signal}::{trigger}"
        if bucket_key not in pattern_buckets:
            pattern_buckets[bucket_key] = {
                "signal": fields.get("signal", ""),
                "trigger": fields.get("trigger", ""),
                "fix": fix,
                "count": 0,
                "latest_mistake": mistake,
                "examples": [],
            }
        pattern_buckets[bucket_key]["count"] += 1
        if mistake and len(pattern_buckets[bucket_key]["latest_mistake"]) < len(mistake):
            pattern_buckets[bucket_key]["latest_mistake"] = mistake
        if len(pattern_buckets[bucket_key]["examples"]) < 3:
            pattern_buckets[bucket_key]["examples"].append(mistake[:100])

    # Sort by frequency
    sorted_patterns = sorted(
        pattern_buckets.values(),
        key=lambda p: p["count"],
        reverse=True,
    )
    return sorted_patterns[:limit]


def get_actionable_experience(
    context: str,
    intent: str = "auto",
    limit: int = 3,
) -> list[dict[str, str]]:
    """Get actionable experience for a given context and intent.

    This is the primary retrieval function for planning/review/debug phases.
    It searches the experience ledger and returns ranked, actionable suggestions.

    Args:
        context: Current task description or error message
        intent: "debug" | "plan" | "review" | "auto"
        limit: Maximum number of recommendations

    Returns:
        List of {trigger, fix, confidence} recommendations
    """
    experiences = _load_experiences()
    if not experiences:
        return []

    context_lower = context.lower()
    scored: list[tuple[float, dict[str, str]]] = []

    # Intent-based field weights
    field_weights = {
        "debug": {"signal": 2.0, "trigger": 1.5, "fix": 1.0},
        "plan": {"trigger": 2.0, "fix": 1.0, "signal": 0.5},
        "review": {"trigger": 1.0, "signal": 1.0, "fix": 0.5},
        "auto": {"signal": 1.0, "trigger": 1.0, "fix": 1.0},
    }
    weights = field_weights.get(intent, field_weights["auto"])

    for exp in experiences:
        text = exp.get("text", "")
        fields = _parse_reflexion_fields(text)
        if not fields:
            continue

        score = 0.0
        matched_fields: list[str] = []

        # Match signal
        signal = fields.get("signal", "").lower()
        if signal and signal in context_lower:
            score += weights["signal"] * 2.0
            matched_fields.append(f"signal={signal!r}")
        elif signal and any(w in context_lower for w in signal.split()):
            score += weights["signal"]
            matched_fields.append(f"signal~={signal!r}")

        # Match trigger
        trigger = fields.get("trigger", "").lower()
        if trigger and trigger in context_lower:
            score += weights["trigger"] * 1.5
            matched_fields.append(f"trigger={trigger!r}")
        elif trigger and any(w in context_lower for w in trigger.split()[:3]):
            score += weights["trigger"] * 0.5
            matched_fields.append(f"trigger~={trigger!r}")

        # Match fix (less weight - it's the solution)
        fix = fields.get("fix", "")
        if fix and any(w in context_lower for w in fix.split()[:5]):
            score += weights["fix"] * 0.3

        # Intent-specific boosts
        if intent == "debug":
            if "error" in context_lower or "fail" in context_lower:
                if fields.get("signal"):
                    score *= 1.3
        elif intent == "plan":
            if any(k in context_lower for k in ("implement", "add", "create", "build")):
                if trigger and "implement" in trigger.lower():
                    score *= 1.2

        # Apply confidence from storage
        confidence = exp.get("confidence", 0.5)
        score *= confidence

        if score > 0:
            scored.append((score, {
                "trigger": fields.get("trigger", ""),
                "fix": fields.get("fix", ""),
                "signal": fields.get("signal", ""),
                "mistake": fields.get("mistake", ""),
                "confidence": f"{confidence:.2f}",
                "matched_fields": "; ".join(matched_fields),
            }))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:limit]]


def check_experience_before_action(
    phase: str,
    context: str,
    workdir: str = ".",
) -> dict[str, Any]:
    """Pre-flight experience check before planning/review/debug actions.

    This is the primary integration point for the workflow engine.
    Call this before high-stakes actions to retrieve relevant experience.

    Args:
        phase: Current phase ("PLANNING", "REVIEWING", "DEBUGGING", etc.)
        context: Task description or error message
        workdir: Working directory

    Returns:
        Dict with:
            - has_relevant_experience: bool
            - recommendations: list of actionable fixes
            - warning: str or None (if high-risk pattern detected)
            - patterns_found: int
    """
    intent_map = {
        "PLANNING": "plan",
        "ANALYZING": "plan",
        "REVIEWING": "review",
        "DEBUGGING": "debug",
        "EXECUTING": "auto",
        "RESEARCH": "auto",
        "THINKING": "auto",
    }
    intent = intent_map.get(phase, "auto")

    recommendations = get_actionable_experience(context, intent=intent, limit=5)
    patterns = get_failure_patterns(
        trigger_contains=context.split()[0] if context else None,
        limit=3,
    )

    has_relevant = len(recommendations) > 0 or len(patterns) > 0

    # Build warning if high-risk pattern found
    warning = None
    if has_relevant:
        high_risk_signals = {"test_failure", "syntax_error", "import_error", "quality_gate_failed"}
        risky = [
            r for r in recommendations
            if any(sig in r.get("signal", "").lower() for sig in high_risk_signals)
        ]
        if risky:
            warning = (
                f"High-risk pattern detected: {len(risky)} known failure pattern(s) match this context. "
                f"Suggested fix: {risky[0].get('fix', 'consult experience ledger')[:100]}"
            )

    return {
        "has_relevant_experience": has_relevant,
        "recommendations": recommendations,
        "warning": warning,
        "patterns_found": len(recommendations),
        "intent": intent,
        "phase": phase,
    }


def build_experience_ledger() -> dict[str, Any]:
    """Rebuild the experience ledger from raw memory index.

    Returns:
        Ledger summary with pattern counts by category
    """
    patterns_by_signal: dict[str, int] = defaultdict(int)
    patterns_by_trigger: dict[str, int] = defaultdict(int)
    total = 0
    high_confidence = 0

    experiences = _load_experiences()
    for exp in experiences:
        total += 1
        if exp.get("confidence", 0) >= 0.7:
            high_confidence += 1
        text = exp.get("text", "")
        fields = _parse_reflexion_fields(text)
        if fields.get("signal"):
            patterns_by_signal[fields["signal"][:40].lower()] += 1
        if fields.get("trigger"):
            patterns_by_trigger[fields["trigger"][:40].lower()] += 1

    return {
        "total_experiences": total,
        "high_confidence_count": high_confidence,
        "top_signals": dict(sorted(patterns_by_signal.items(), key=lambda x: x[1], reverse=True)[:10]),
        "top_triggers": dict(sorted(patterns_by_trigger.items(), key=lambda x: x[1], reverse=True)[:10]),
        "built_at": datetime.now().isoformat(),
    }


def get_experience_summary(workdir: str = ".") -> str:
    """Get a human-readable experience summary for display."""
    ledger = build_experience_ledger()
    lines = [
        "# Experience Ledger Summary",
        f"Total experiences: {ledger['total_experiences']}",
        f"High confidence: {ledger['high_confidence_count']}",
        "",
        "Top failure signals:",
    ]
    for sig, count in ledger["top_signals"].items():
        lines.append(f"  - [{count}x] {sig}")
    lines.append("")
    lines.append("Top triggers:")
    for trig, count in ledger["top_triggers"].items():
        lines.append(f"  - [{count}x] {trig}")
    return "\n".join(lines)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Experience Ledger - Reflexion Experience Aggregation")
    parser.add_argument("--op", choices=[
        "check", "patterns", "actionable", "build", "summary",
    ], required=True)
    parser.add_argument("--phase", default="PLANNING", help="Phase for context")
    parser.add_argument("--context", default="", help="Task description or error context")
    parser.add_argument("--intent", default="auto", choices=["auto", "debug", "plan", "review"])
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--error-type", help="Filter by error type")
    parser.add_argument("--trigger", help="Filter by trigger keyword")
    args = parser.parse_args()

    if args.op == "check":
        result = check_experience_before_action(args.phase, args.context)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.op == "patterns":
        patterns = get_failure_patterns(
            error_type=args.error_type,
            trigger_contains=args.trigger,
            limit=args.limit,
        )
        print(json.dumps(patterns, ensure_ascii=False, indent=2))
    elif args.op == "actionable":
        recs = get_actionable_experience(args.context, intent=args.intent, limit=args.limit)
        print(json.dumps(recs, ensure_ascii=False, indent=2))
    elif args.op == "build":
        ledger = build_experience_ledger()
        print(json.dumps(ledger, ensure_ascii=False, indent=2))
    elif args.op == "summary":
        print(get_experience_summary())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
