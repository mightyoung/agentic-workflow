"""
Snapshot builder: phase context and workflow snapshot assembly.

Provides:
- _build_phase_context: build context dict for the next phase
- get_workflow_snapshot: assemble a full workflow snapshot dict
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import router
import task_tracker
from contract_manager import parse_phase_contract
from findings_paths import (
    ensure_findings_dir,
    findings_latest_path,
    findings_session_path,
    legacy_findings_paths,
)
from frontier_scheduler import (
    _find_canonical_tasks_path,
    load_planning_tasks,
    next_plan_tasks,
)
from phase_transitions import recommend_next_phases
from runtime_profile import build_thinking_summary
from unified_state import (
    get_debug_summary,
    get_failure_event_summary,
    get_planning_summary,
    get_research_summary,
    get_review_summary,
    get_runtime_profile_summary,
    get_thinking_summary,
    load_state,
    workflow_state_path,
)


def _build_phase_context(current_phase: str, workdir: str, session_id: str) -> dict[str, Any]:
    """
    Build context for the next phase based on artifacts from the current phase.

    Returns dict with:
        files_to_read: list of file paths the AI should read
        summary: brief description of what was produced
    """
    workdir_path = Path(workdir)
    files_to_read: list[str] = []
    summary = ""
    memory_hints: list[str] = []
    memory_query = ""
    memory_intent = "auto"
    research_summary: dict[str, Any] = {}

    try:
        state = load_state(workdir)
    except Exception:
        state = None

    task_text = ""
    if state and state.task:
        task_text = state.task.description or state.task.title or ""
    if not task_text:
        task_text = session_id

    complexity = ""
    if state and state.metadata:
        complexity = str(state.metadata.get("complexity") or "")
    if not complexity and task_text:
        complexity, _ = router.estimate_complexity(task_text)

    research_summary = get_research_summary(workdir, state)
    try:
        contract_summary = parse_phase_contract(workdir)
    except Exception:
        contract_summary = {}

    if current_phase in ("PLANNING", "THINKING"):
        memory_intent = "plan"
    elif current_phase == "REVIEWING":
        memory_intent = "review"
    elif current_phase in ("DEBUGGING", "REFINING"):
        memory_intent = "debug"

    thinking_summary: dict[str, Any] = {}

    try:
        from memory_longterm import search_memory

        memory_query = task_text or current_phase
        memory_hints = search_memory(
            memory_query,
            filepath=str(workdir_path / "MEMORY.md"),
            scope="project",
            limit=3,
            intent=memory_intent,
        )
    except Exception:
        memory_hints = []
        memory_query = ""

    # MAGMA P2: Also search semantic and temporal views for richer context
    try:
        from memory_views import search_views
        view_results = search_views(
            task_text or current_phase,
            intent=memory_intent,
            limit=3,
        )
        # Add semantic hits as memory hints if not already covered
        semantic_hints = view_results.get("semantic", [])
        for hit in semantic_hints[:2]:
            snippet = hit.get("snippet", "")
            if snippet and snippet not in memory_hints:
                memory_hints.append(f"[semantic] {snippet}")
        # Add temporal context if recent and relevant
        temporal_hints = view_results.get("temporal", [])
        for hit in temporal_hints[:1]:
            month = hit.get("_month", "")
            snippet = hit.get("text", "")
            if snippet and month:
                hint = f"[temporal:{month}] {snippet[:80]}"
                if hint not in memory_hints:
                    memory_hints.append(hint)
    except Exception:
        pass  # MAGMA views are best-effort

    # Reflexion P1: Pre-flight experience check before high-stakes phases
    # This retrieves actionable experience from the ledger before planning/review/debug
    experience_check: dict[str, Any] = {
        "has_relevant_experience": False,
        "recommendations": [],
        "warning": None,
        "patterns_found": 0,
    }
    if current_phase in ("PLANNING", "REVIEWING", "DEBUGGING", "EXECUTING", "ANALYZING", "THINKING"):
        try:
            from experience_ledger import check_experience_before_action
            experience_check = check_experience_before_action(
                phase=current_phase,
                context=task_text,
                workdir=workdir,
            )
        except Exception:
            # Experience ledger is best-effort - don't fail the workflow
            pass

    if current_phase == "RESEARCH":
        # RESEARCH produces findings — THINKING should read them
        findings = findings_session_path(workdir_path, session_id)
        findings_latest = findings_latest_path(workdir_path)
        if findings.exists():
            files_to_read.append(str(findings))
            summary = "Research findings available. Read findings before analysis."
        elif findings_latest.exists():
            files_to_read.append(str(findings_latest))
            summary = "Research findings available. Read findings before analysis."
        else:
            findings_glob = legacy_findings_paths(workdir_path)
            if findings_glob:
                files_to_read.append(str(findings_glob[0]))
                summary = "Research findings available."

    elif current_phase == "PLANNING":
        # PLANNING produces the canonical spec/task chain — EXECUTING should follow it
        canonical_tasks = _find_canonical_tasks_path(workdir)
        contract_json = workdir_path / ".contract.json"
        legacy_plan = workdir_path / "task_plan.md"
        if canonical_tasks and canonical_tasks.exists():
            files_to_read.append(str(canonical_tasks))
            if contract_json.exists():
                files_to_read.append(str(contract_json))
            summary = "Canonical task chain available. Execute tasks in priority order and follow the contract."
        elif legacy_plan.exists():
            files_to_read.append(str(legacy_plan))
            if contract_json.exists():
                files_to_read.append(str(contract_json))
            summary = "Legacy task plan available. Execute tasks in priority order and follow the contract."

    elif current_phase == "EXECUTING":
        # EXECUTING produces code changes — REVIEWING should diff them
        contract_parts: list[str] = []
        if contract_summary.get("goals"):
            contract_parts.append(
                "Contract goals: "
                + " | ".join(str(goal) for goal in contract_summary.get("goals", [])[:3])
            )
        if contract_summary.get("acceptance_criteria"):
            contract_parts.append(
                "Acceptance: "
                + " | ".join(str(item) for item in contract_summary.get("acceptance_criteria", [])[:2])
            )
        if contract_summary.get("impact_files"):
            contract_parts.append(
                "Impact files: "
                + ", ".join(str(item) for item in contract_summary.get("impact_files", [])[:3])
            )
        if contract_parts:
            summary = "Code changes made. Run `git diff` to review actual changes. " + " ".join(contract_parts)
        else:
            summary = "Code changes made. Run `git diff` to review actual changes."

    elif current_phase == "REVIEWING":
        # REVIEWING produces review feedback — REFINING should fix issues
        summary = "Review complete. Fix any issues identified in review."

    elif current_phase == "THINKING":
        # THINKING produces analysis — PLANNING should use conclusions
        thinking_summary = build_thinking_summary(
            task_text,
            complexity or "M",
            memory_hints,
            experience_check,
            research_summary=research_summary,
            contract_summary=contract_summary,
        )
        thinking_methods = thinking_summary.get("thinking_methods", [])
        methods_text = " → ".join(thinking_methods) if thinking_methods else "调查研究 → 矛盾分析 → 群众路线 → 持久战略"
        summary = (
            f"{thinking_summary.get('workflow_label', 'THINKING')}："
            f"{methods_text}。"
            f"当前阶段: {thinking_summary.get('stage_judgment', '战术速决')}。"
            f"主要矛盾: {thinking_summary.get('major_contradiction', '事实 vs 假设')}。"
            f"局部攻坚点: {thinking_summary.get('local_attack_point', '先找最小可验证切口')}。"
        )

    if research_summary:
        research_note = (
            f"Research evidence status: {research_summary.get('evidence_status', 'unset')}; "
            f"sources={research_summary.get('sources_count', 0)}; "
            f"engine={research_summary.get('search_engine') or 'unset'}."
        )
        if current_phase == "RESEARCH":
            summary = f"{summary} {research_note}".strip() if summary else research_note
        elif current_phase in {"PLANNING", "THINKING", "REVIEWING", "EXECUTING"}:
            summary = f"{summary} {research_note}".strip() if summary else research_note

    if memory_hints and summary:
        summary += " Relevant long-term memory is available."
    elif memory_hints:
        summary = "Relevant long-term memory is available."

    return {
        "files_to_read": files_to_read,
        "summary": summary,
        "research_summary": research_summary,
        "thinking_summary": thinking_summary if current_phase == "THINKING" else {},
        "memory_query": memory_query,
        "memory_intent": memory_intent,
        "memory_hints": memory_hints,
        # Reflexion P1: Include experience recommendations in phase context
        "experience_check": experience_check,
    }


def get_workflow_snapshot(workdir: str = ".") -> dict[str, Any]:
    state = load_state(workdir)
    tracker_path = Path(workdir) / task_tracker.DEFAULT_TRACKER_FILE
    task = None
    plan_tasks, plan_source = load_planning_tasks(workdir)
    next_tasks = next_plan_tasks(workdir)

    if state is None:
        return {
            "exists": False,
            "valid": False,
            "errors": ["state file does not exist"],
            "recommended_next_phases": [],
            "plan_tasks": plan_tasks,
            "plan_source": plan_source,
            "next_plan_tasks": next_tasks,
            "planning_summary": get_planning_summary(workdir, None),
            "research_summary": get_research_summary(workdir, None),
            "thinking_summary": get_thinking_summary(workdir, None),
            "review_summary": get_review_summary(workdir, None),
            "debug_summary": get_debug_summary(workdir, None),
            "runtime_profile_summary": get_runtime_profile_summary(None),
            "failure_event_summary": get_failure_event_summary(None),
            "context_for_next_phase": {
                "files_to_read": [],
                "summary": "",
                "thinking_summary": {},
                "memory_query": "",
                "memory_intent": "auto",
                "memory_hints": [],
                "experience_check": {
                    "has_relevant_experience": False,
                    "recommendations": [],
                    "warning": None,
                    "patterns_found": 0,
                },
            },
        }

    if state.task and state.task.task_id:
        task = task_tracker.get_task(state.task.task_id, str(tracker_path))

    current_phase = state.phase.get("current", "IDLE") if state.phase else "IDLE"
    context_for_next_phase = _build_phase_context(current_phase, workdir, state.session_id or "unknown")

    # Load artifact registry for full audit trail
    from unified_state import _load_artifact_registry
    artifact_registry = _load_artifact_registry(workdir)

    # Validate state
    from unified_state import validate_workflow_state
    is_valid, errors = validate_workflow_state(workdir)
    runtime_profile_summary = get_runtime_profile_summary(state)
    planning_summary = get_planning_summary(workdir, state)

    return {
        "exists": True,
        "valid": is_valid,
        "errors": errors,
        "session_id": state.session_id,
        "task_id": state.task.task_id if state.task else None,
        "current_phase": current_phase,
        "trigger_type": state.trigger_type,
        "task": task,
        "runtime_profile_summary": runtime_profile_summary,
        "planning_summary": planning_summary,
        "research_summary": get_research_summary(workdir, state),
        "thinking_summary": get_thinking_summary(workdir, state),
        "review_summary": get_review_summary(workdir, state),
        "debug_summary": get_debug_summary(workdir, state),
        "failure_event_summary": get_failure_event_summary(state),
        "recommended_next_phases": recommend_next_phases(current_phase, None),
        "plan_tasks": plan_tasks,
        "plan_source": plan_source,
        "next_plan_tasks": next_tasks,
        "context_for_next_phase": context_for_next_phase,
        "state_file": str(workflow_state_path(workdir)),
        # artifact_registry is the authoritative source - state.artifacts removed from interface
        "artifact_registry": artifact_registry.get("artifacts", []),
    }
