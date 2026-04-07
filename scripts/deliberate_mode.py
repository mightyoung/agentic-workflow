#!/usr/bin/env python3
"""
Deliberate Mode - Tree of Thoughts for Complex Workflow Decisions

Implements a controlled, limited Tree of Thoughts exploration for complex
workflow decisions. Only activates in specific high-stakes scenarios.

Trigger conditions:
  - planning conflict (multiple valid plans with tradeoffs)
  - debug repeated failure (same error >2 attempts)
  - review divergence (reviewers disagree on fix direction)
  - high complexity tasks (estimated complexity >= L)

Design constraints:
  - Max 3 candidate branches per deliberation
  - Lightweight scoring (not full tree search)
  - Results are advisory (don't override human decisions)

Usage:
    from deliberate_mode import (
        should_deliberate,
        deliberate,
        Branch,
    )

    if should_deliberate(workdir, trigger="planning_conflict"):
        branches = deliberate(workdir, trigger, context)
        # Select branch or merge insights
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# AgentSys boundary: deliberation outputs go to artifacts, not to lead context
DELIBERATION_DIR = ".deliberations"
MAX_BRANCHES = 3


@dataclass
class Branch:
    """A candidate branch in the deliberation tree."""
    branch_id: str
    title: str
    description: str
    score: float
    confidence: float
    rationale: str
    risks: list[str] = field(default_factory=list)
    parent_branch_id: str | None = None  # For tree structure


@dataclass
class DeliberationResult:
    """Result of a deliberate() call."""
    trigger: str
    branches: list[Branch]
    recommended_branch_id: str | None
    timestamp: str
    context_summary: str
    deliberation_path: str | None  # Path to deliberation artifact


def should_deliberate(
    workdir: str,
    trigger: str,
    state: Any | None = None,
) -> bool:
    """Determine if deliberate mode should activate.

    Args:
        workdir: Working directory
        trigger: One of "planning_conflict", "debug_failure", "review_divergence", "high_complexity"
        state: Optional workflow state for deeper analysis

    Returns:
        True if deliberation is warranted
    """
    trigger_threshold = {
        "planning_conflict": 2,   # 2+ conflicting plans
        "debug_failure": 2,       # 2+ failed attempts
        "review_divergence": 2,   # 2+ reviewer disagreements
        "high_complexity": 1,     # Always deliberate for high complexity
    }
    threshold = trigger_threshold.get(trigger, 2)

    if trigger == "planning_conflict":
        # Check if frontier has multiple conflicting task groups
        try:
            from workflow_engine import compute_frontier
            frontier = compute_frontier(workdir)
            conflict_groups = frontier.get("conflict_groups", [])
            if len(conflict_groups) >= threshold:
                return True
            # Also check if multiple valid next tasks exist
            next_tasks = frontier.get("executable_frontier", [])
            if len(next_tasks) >= 3:
                return True
        except Exception:
            pass

    elif trigger == "debug_failure":
        # Check retry count from state
        if state and hasattr(state, "decisions"):
            retry_count = sum(1 for d in state.decisions if "retry" in str(d.decision).lower())
            if retry_count >= threshold:
                return True

    elif trigger == "review_divergence":
        # Check if review has multiple risk findings
        if state and hasattr(state, "decisions"):
            review_findings = sum(1 for d in state.decisions if "review" in str(d.decision).lower())
            if review_findings >= threshold:
                return True

    elif trigger == "high_complexity":
        if state and state.metadata:
            complexity = state.metadata.get("complexity", "")
            if complexity in ("L", "XL"):
                return True

    return False


def deliberate(
    workdir: str,
    trigger: str,
    context: dict[str, Any],
) -> DeliberationResult:
    """Run a limited ToT-style deliberation.

    Args:
        workdir: Working directory
        trigger: Deliberation trigger type
        context: Dict with:
            - task_description: str
            - candidate_options: list of option dicts (optional)
            - failure_history: list of error strings (for debug)
            - frontier: dict from compute_frontier (for planning)
            - review_findings: list of review issues (for review)

    Returns:
        DeliberationResult with scored branches
    """
    branches: list[Branch] = []
    timestamp = datetime.now().isoformat()

    if trigger == "planning_conflict":
        branches = _deliberate_planning(workdir, context)
    elif trigger == "debug_failure":
        branches = _deliberate_debug(workdir, context)
    elif trigger == "review_divergence":
        branches = _deliberate_review(workdir, context)
    elif trigger == "high_complexity":
        branches = _deliberate_high_complexity(workdir, context)
    else:
        branches = _deliberate_generic(context)

    # Sort by score descending
    branches.sort(key=lambda b: b.score, reverse=True)

    # Keep only top MAX_BRANCHES
    branches = branches[:MAX_BRANCHES]

    # Recommend the top-scored branch
    recommended = branches[0].branch_id if branches else None

    # Persist deliberation to artifact (AgentSys: only summaries cross lead boundary)
    deliberation_path = _persist_deliberation(
        workdir, trigger, branches, recommended, timestamp, context
    )

    return DeliberationResult(
        trigger=trigger,
        branches=branches,
        recommended_branch_id=recommended,
        timestamp=timestamp,
        context_summary=context.get("task_description", "")[:200],
        deliberation_path=deliberation_path,
    )


def _score_branch(
    title: str,
    description: str,
    rationale: str,
    context_keywords: list[str],
) -> tuple[float, float]:
    """Score a branch on relevance and confidence.

    Returns (score, confidence) where:
        - score: 0.0-1.0 overall quality
        - confidence: 0.0-1.0 how certain we are about the score
    """
    score = 0.5
    confidence = 0.5

    desc_lower = description.lower()
    title_lower = title.lower()
    rationale_lower = rationale.lower()

    # Boost for keyword matches with context
    matched = sum(1 for kw in context_keywords if kw.lower() in desc_lower or kw.lower() in title_lower)
    if context_keywords:
        match_ratio = matched / len(context_keywords)
        score += match_ratio * 0.3

    # Boost for concrete rationale
    if rationale_lower and len(rationale_lower) > 20:
        score += 0.1
        confidence += 0.1

    # Penalize overly long descriptions (might be hedging)
    if len(description) > 300:
        score -= 0.1

    # Clamp
    score = max(0.1, min(1.0, score))
    confidence = max(0.3, min(0.95, confidence))

    return score, confidence


def _deliberate_planning(workdir: str, context: dict[str, Any]) -> list[Branch]:
    """Deliberate on planning conflicts using frontier data."""
    branches: list[Branch] = []
    task_desc = context.get("task_description", "")
    keywords = task_desc.split()[:10]

    # Get frontier data
    frontier = context.get("frontier", {})
    if not frontier:
        try:
            from workflow_engine import compute_frontier
            frontier = compute_frontier(workdir)
        except Exception:
            frontier = {}

    executable = frontier.get("executable_frontier", [])
    conflict_groups = frontier.get("conflict_groups", [])

    # Branch 1: Execute lowest-risk tasks first
    if executable:
        safe_tasks = [t for t in executable if not any(
            k in t.get("title", "").lower()
            for k in ["risk", "refactor", "breaking"]
        )]
        if safe_tasks:
            safe_title = safe_tasks[0].get("title", "Safe task")
            branches.append(Branch(
                branch_id="plan_safe",
                title=f"Start with safe task: {safe_title}",
                description=f"Execute {len(safe_tasks)} low-risk tasks first to establish momentum.",
                score=0.6,
                confidence=0.7,
                rationale="Low-risk tasks build momentum and reduce early failure risk.",
                risks=["May delay critical high-risk tasks"],
            ))

    # Branch 2: Address conflicts first
    if conflict_groups:
        conflict_task = conflict_groups[0][0] if conflict_groups else None
        if conflict_task:
            branches.append(Branch(
                branch_id="plan_conflict_first",
                title=f"Resolve conflict: {conflict_task.get('title', 'Unknown')}",
                description=f"Tackle {len(conflict_groups)} conflicting task group(s) head-on.",
                score=0.5,
                confidence=0.6,
                rationale="Resolving conflicts early prevents deadlocks later.",
                risks=["May take longer, but prevents cascade failures"],
            ))

    # Branch 3: Parallel execution
    if len(executable) >= 2:
        branches.append(Branch(
            branch_id="plan_parallel",
            title="Parallel execution of independent tasks",
            description=f"Run {len(executable)} tasks with parallel-safe scheduling.",
            score=0.4,
            confidence=0.5,
            rationale="Parallel execution maximizes throughput when tasks are independent.",
            risks=["May create merge conflicts if tasks touch same files"],
        ))

    # Score all branches
    scored = []
    for b in branches:
        score, conf = _score_branch(b.title, b.description, b.rationale, keywords)
        b.score = (b.score + score) / 2
        b.confidence = (b.confidence + conf) / 2
        scored.append(b)

    return scored


def _deliberate_debug(workdir: str, context: dict[str, Any]) -> list[Branch]:
    """Deliberate on debug strategies after repeated failures."""
    branches: list[Branch] = []
    task_desc = context.get("task_description", "")
    keywords = task_desc.split()[:10]
    failure_history = context.get("failure_history", [])

    # Get error patterns from failures
    error_types: list[str] = []
    for failure in failure_history[-3:]:
        if isinstance(failure, str):
            if "test" in failure.lower():
                error_types.append("test_failure")
            elif "import" in failure.lower() or "module" in failure.lower():
                error_types.append("import_error")
            elif "syntax" in failure.lower():
                error_types.append("syntax_error")
            elif "type" in failure.lower():
                error_types.append("type_error")
            else:
                error_types.append("generic_error")

    # Branch 1: Narrow scope
    branches.append(Branch(
        branch_id="debug_narrow",
        title="Narrow debugging scope",
        description="Reduce task scope to minimum viable fix. Isolate the exact failure point.",
        score=0.7,
        confidence=0.8,
        rationale="Narrow scope reduces complexity and increases fix precision.",
        risks=["May not address root cause if symptom-only fix"],
    ))

    # Branch 2: Try alternative approach
    branches.append(Branch(
        branch_id="debug_alternative",
        title="Try alternative implementation path",
        description="Instead of fixing current approach, implement using a different strategy.",
        score=0.5,
        confidence=0.6,
        rationale="If current approach failed 2+ times, alternative may succeed.",
        risks=["May introduce new bugs, takes more time"],
    ))

    # Branch 3: Seek experience
    if error_types:
        branches.append(Branch(
            branch_id="debug_experience",
            title=f"Consult experience for: {error_types[0]}",
            description="Search experience ledger for known patterns related to this error type.",
            score=0.6,
            confidence=0.7,
            rationale="Similar errors likely have known fixes in experience ledger.",
            risks=["May not find exact match"],
        ))

    # Score
    for b in branches:
        score, conf = _score_branch(b.title, b.description, b.rationale, keywords)
        b.score = (b.score + score) / 2
        b.confidence = (b.confidence + conf) / 2

    return branches


def _deliberate_review(workdir: str, context: dict[str, Any]) -> list[Branch]:
    """Deliberate on review findings and fixes."""
    branches: list[Branch] = []
    task_desc = context.get("task_description", "")
    keywords = task_desc.split()[:10]
    review_findings = context.get("review_findings", [])

    # Branch 1: Fix critical issues first
    critical = [f for f in review_findings if "critical" in str(f).lower() or "high" in str(f).lower()]
    if critical:
        branches.append(Branch(
            branch_id="review_critical_first",
            title=f"Fix {len(critical)} critical/high issues",
            description="Address critical and high-risk findings before lower-priority ones.",
            score=0.8,
            confidence=0.8,
            rationale="Critical issues pose the greatest risk to production.",
            risks=["May require significant refactoring"],
        ))

    # Branch 2: Incremental fixes
    branches.append(Branch(
        branch_id="review_incremental",
        title="Fix issues incrementally in priority order",
        description="Address findings one by one in order of severity.",
        score=0.6,
        confidence=0.7,
        rationale="Incremental approach reduces risk of introducing new issues.",
        risks=["Slower overall progress"],
    ))

    # Branch 3: Request more review
    branches.append(Branch(
        branch_id="review_re_request",
        title="Request additional review before fixes",
        description="Get second opinion on findings to confirm which are real issues.",
        score=0.4,
        confidence=0.5,
        rationale="May save time if some findings are false positives.",
        risks=["Delays fixes, may not improve quality"],
    ))

    for b in branches:
        score, conf = _score_branch(b.title, b.description, b.rationale, keywords)
        b.score = (b.score + score) / 2
        b.confidence = (b.confidence + conf) / 2

    return branches


def _deliberate_high_complexity(workdir: str, context: dict[str, Any]) -> list[Branch]:
    """Deliberate on high complexity tasks."""
    branches: list[Branch] = []
    task_desc = context.get("task_description", "")
    keywords = task_desc.split()[:10]

    branches.append(Branch(
        branch_id="complex_break_down",
        title="Break down into smaller tasks",
        description="Decompose the task into P1/P2/P3 subtasks with clear dependencies.",
        score=0.7,
        confidence=0.8,
        rationale="Large tasks are harder to verify; smaller tasks enable incremental validation.",
        risks=["May delay initial progress while planning"],
    ))

    branches.append(Branch(
        branch_id="complex_increment",
        title="Implement core functionality first",
        description="Build a minimal viable implementation, then iterate.",
        score=0.6,
        confidence=0.7,
        rationale="Early working code enables faster feedback.",
        risks=["May accumulate technical debt"],
    ))

    branches.append(Branch(
        branch_id="complex_research_first",
        title="Research before implementation",
        description="Spend more time in RESEARCH/THINKING to solidify approach.",
        score=0.5,
        confidence=0.6,
        rationale="Complex tasks benefit from better upfront understanding.",
        risks=["May be seen as analysis paralysis"],
    ))

    for b in branches:
        score, conf = _score_branch(b.title, b.description, b.rationale, keywords)
        b.score = (b.score + score) / 2
        b.confidence = (b.confidence + conf) / 2

    return branches


def _deliberate_generic(context: dict[str, Any]) -> list[Branch]:
    """Generic deliberation when no specific trigger matches."""
    task_desc = context.get("task_description", "")
    keywords = task_desc.split()[:10]

    return [
        Branch(
            branch_id="generic_option_a",
            title="Option A: Conservative approach",
            description="Proceed with well-understood, lower-risk approach.",
            score=0.6,
            confidence=0.6,
            rationale="Conservative approach minimizes surprise.",
            risks=["May miss optimization opportunities"],
        ),
        Branch(
            branch_id="generic_option_b",
            title="Option B: Aggressive approach",
            description="Try the more ambitious solution that addresses root cause.",
            score=0.5,
            confidence=0.5,
            rationale="Aggressive approach may deliver better results.",
            risks=["Higher chance of failure"],
        ),
    ]


def _persist_deliberation(
    workdir: str,
    trigger: str,
    branches: list[Branch],
    recommended: str | None,
    timestamp: str,
    context: dict[str, Any],
) -> str | None:
    """Persist deliberation result to artifact (AgentSys: summary only in lead context)."""
    workdir_path = Path(workdir)
    deliberation_dir = workdir_path / DELIBERATION_DIR
    deliberation_dir.mkdir(exist_ok=True)

    deliberation_id = f"delib_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    deliberation_path = deliberation_dir / f"{deliberation_id}.json"

    data = {
        "deliberation_id": deliberation_id,
        "trigger": trigger,
        "timestamp": timestamp,
        "context_summary": context.get("task_description", "")[:200],
        "recommended_branch_id": recommended,
        "branches": [
            {
                "branch_id": b.branch_id,
                "title": b.title,
                "description": b.description[:500],  # Limit size
                "score": round(b.score, 3),
                "confidence": round(b.confidence, 3),
                "rationale": b.rationale,
                "risks": b.risks,
                "parent_branch_id": b.parent_branch_id,
            }
            for b in branches
        ],
    }

    try:
        with open(deliberation_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(deliberation_path)
    except OSError:
        return None


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Deliberate Mode - Tree of Thoughts")
    parser.add_argument("--workdir", default=".")
    parser.add_argument("--trigger", choices=[
        "planning_conflict", "debug_failure", "review_divergence", "high_complexity",
    ], required=True)
    parser.add_argument("--context", default="{}", help="JSON context dict")
    args = parser.parse_args()

    from workflow_engine import load_state
    state = load_state(args.workdir)

    if should_deliberate(args.workdir, args.trigger, state):
        context = json.loads(args.context)
        result = deliberate(args.workdir, args.trigger, context)
        print(json.dumps({
            "trigger": result.trigger,
            "recommended": result.recommended_branch_id,
            "branches": [
                {"id": b.branch_id, "title": b.title, "score": b.score, "confidence": b.confidence}
                for b in result.branches
            ],
            "path": result.deliberation_path,
        }, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"should_deliberate": False}, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
