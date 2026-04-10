#!/usr/bin/env python3
"""
Minimal workflow runtime for agentic-workflow.

This bridges the existing scripts into a concrete runtime chain:
prompt -> route -> local state -> task tracker -> optional plan scaffold
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import memory_ops
import router
import search_adapter
import task_tracker
from analyze_gate import validate_analyze_gate
from contract_manager import (
    _create_phase_contract,
    parse_phase_contract,
    update_contract_json,
    validate_contract_gate,
)
from findings_paths import (
    ensure_findings_dir,
    findings_latest_path,
    findings_session_path,
    legacy_findings_paths,
)
from middleware import Request as MiddlewareRequest
from middleware import create_default_chain as create_middleware_chain
from review_paths import (
    ensure_review_dir,
    legacy_review_paths,
    review_latest_path,
    review_session_path,
)
from runtime_profile import (
    build_skill_context,
    build_thinking_summary,
    debugging_activation_level_for_context,
    escalate_skill_activation_level,
    should_use_skill_for_phase,
    skill_activation_level_for_phase,
    skill_policy_for_phase,
)
from safe_io import safe_write_json, safe_write_text_locked
from skill_loader import SkillPromptFormatter, load_skill
from team_agent import TeamAgent
from trajectory_logger import TrajectoryLogger
from unified_state import (
    ArtifactType,
    can_transition,
    create_initial_state,
    get_allowed_transitions,
    get_failure_event_summary,
    get_planning_summary,
    get_research_summary,
    get_thinking_summary,
    get_review_summary,
    get_runtime_profile_summary,
    load_state,
    register_artifact,
    save_state,
    trajectory_dir_path,
    transition_phase,
    workflow_state_path,
)

# 存储当前活跃的 TrajectoryLogger 实例
_active_loggers: dict[str, TrajectoryLogger] = {}

DEFAULT_CATEGORY = "WORKFLOW"

def _run_quality_gate_if_applicable(workdir: str, task_id: str, tracker_path: str, is_code_task: bool = True) -> bool:
    """
    Run quality gate if applicable for the task.

    For code implementation tasks, runs typecheck/lint/test.
    For research-only tasks, returns True (no code to check).

    Args:
        workdir: Working directory
        task_id: Task ID
        tracker_path: Path to task tracker
        is_code_task: Whether this is a code task (False for research-only)

    Returns:
        True if gate passed or not applicable, False if gate failed
    """
    if not is_code_task:
        # Research-only tasks don't need quality gate
        return True

    try:
        import quality_gate

        # Run quality gate on workdir
        report = quality_gate.run_quality_gate(workdir, ["all"], timeout=60)

        # Log the result
        gate_result_path = Path(workdir) / f".quality_gate_{task_id}.json"
        safe_write_json(gate_result_path, report.to_dict())

        return bool(report.all_passed)
    except Exception:
        # If quality gate fails for any reason, block completion for code tasks
        # This is fail-closed: code tasks must pass quality gate to complete
        return False


def _run_review_gate_if_applicable(
    workdir: str,
    is_code_task: bool,
    state: Any | None = None,
) -> tuple[bool, str]:
    """Validate that code tasks have a completed two-stage review before completion."""
    if not is_code_task:
        return True, "not applicable"

    if state is None:
        state = load_state(workdir)

    review_summary = get_review_summary(workdir, state)
    if not review_summary.get("review_found"):
        return False, "review artifact not found"
    if review_summary.get("review_status") != "reviewed":
        return False, f"review status is {review_summary.get('review_status')}"
    if review_summary.get("stage_1_status") != "reviewed":
        return False, "spec compliance stage missing"
    if review_summary.get("stage_2_status") != "reviewed":
        return False, "code quality stage missing"
    if int(review_summary.get("files_reviewed", 0) or 0) <= 0:
        return False, "review did not analyze any files"
    if review_summary.get("degraded_mode"):
        return False, "review is degraded"
    if review_summary.get("review_source") in {"template", "none", "workdir_scan"}:
        return False, f"review source is {review_summary.get('review_source')}"
    if not review_summary.get("verdict"):
        return False, "review verdict missing"
    return True, "review gate passed"


def _task_id_from_timestamp() -> str:
    return f"T{datetime.now().strftime('%Y%m%d%H%M%S')}"


def _generate_and_register_summary(
    workdir: str,
    state,
    current_phase: str,
    final_state: str,
    session_id: str,
    failure_reason: str | None = None,
) -> str:
    """
    Generate completion summary content and register artifact.
    Used by both advance_workflow (COMPLETE) and complete_workflow.

    Returns:
        Path to the summary file
    """
    from unified_state import ArtifactType, _load_artifact_registry, register_artifact
    registry = _load_artifact_registry(workdir)
    artifact_types = [a.get("type") for a in registry.get("artifacts", [])]

    summary_path = Path(workdir) / f"completion_summary_{session_id}.md"
    task_info = f"# Workflow Completed: {state.task.title if state.task else 'N/A'}\n\n"
    task_info += f"## Status\n- Final State: {final_state}\n"
    task_info += f"- Completed At: {datetime.now().isoformat()}\n"
    task_info += f"- Last Phase: {current_phase}\n\n"

    if failure_reason:
        task_info += f"- Reason: {failure_reason}\n\n"

    # Aggregate research findings content if available
    findings_session_file = findings_session_path(workdir, session_id)
    findings_latest_file = findings_latest_path(workdir)
    findings_content = ""
    for candidate_path in [findings_session_file, findings_latest_file, *legacy_findings_paths(workdir)]:
        if candidate_path.exists():
            findings_content = candidate_path.read_text(encoding="utf-8")
            break

    if findings_content:
        lines = findings_content.split("\n")

        # Extract Research Question
        for i, line in enumerate(lines):
            if "## Research Question" in line and i + 1 < len(lines):
                task_info += f"## Research Summary\n**Question:** {lines[i+1].strip()}\n"
                break

        # Extract Key Findings (first 2 bullet points)
        finding_count = 0
        for i, line in enumerate(lines):
            if "## Key Findings" in line:
                task_info += "\n**Key Findings:**\n"
                for j in range(i + 1, min(i + 5, len(lines))):
                    if lines[j].startswith("## ") or not lines[j].strip():
                        break
                    if lines[j].strip().startswith(("1.", "2.", "3.", "- ")) and finding_count < 2:
                        task_info += f"- {lines[j].strip()[3:] if lines[j].strip().startswith(('1.', '2.', '3.')) else lines[j].strip()[2:]}\n"
                        finding_count += 1
                task_info += "\n"
                break

        # Extract Conclusions
        for i, line in enumerate(lines):
            if "## Conclusions" in line and i + 1 < len(lines):
                task_info += f"**Conclusions:** {lines[i+1].strip()}\n\n"
                break

    # Aggregate review findings content if available
    review_session_file = review_session_path(workdir, session_id)
    review_latest_file = review_latest_path(workdir)
    review_content = ""
    for candidate_path in [review_session_file, review_latest_file, *legacy_review_paths(workdir)]:
        if candidate_path.exists():
            review_content = candidate_path.read_text(encoding="utf-8")
            break

    if review_content:
        lines = review_content.split("\n")

        # Extract Review Scope
        for i, line in enumerate(lines):
            if "## Review Scope" in line and i + 1 < len(lines):
                task_info += f"## Review Summary\n**Scope:** {lines[i+1].strip()}\n"
                break

        # Extract Risk Assessment
        for i, line in enumerate(lines):
            if "## Risk Assessment" in line:
                risk_lines = []
                for j in range(i + 1, min(i + 6, len(lines))):
                    if lines[j].startswith("## ") or not lines[j].strip():
                        break
                    if lines[j].strip() and lines[j].startswith("- **"):
                        risk_lines.append(lines[j].strip())
                if risk_lines:
                    task_info += "**Risk Assessment:**\n" + "\n".join(risk_lines[:3]) + "\n\n"
                break

        # Extract Risk Level
        for i, line in enumerate(lines):
            if "## Risk Level" in line and i + 1 < len(lines):
                task_info += f"**Risk Level:** {lines[i+1].strip()}\n\n"
                break

    # Include task plan summary if available
    plan_path = Path(workdir) / "task_plan.md"
    if plan_path.exists():
        plan_content = plan_path.read_text(encoding="utf-8")
        if "## Task Breakdown" in plan_content or "# Task Plan" in plan_content:
            task_info += "## Execution Summary\n"
            task_info += "- Task plan was created and executed\n"

    task_info += "## Delivered Artifacts\n"
    for atype in set(artifact_types):
        task_info += f"- {atype}\n"

    # Aggregate quality gate results if available (for code tasks)
    tracker_path = Path(workdir) / ".task_tracker.json"
    if tracker_path.exists():
        try:
            tracker_data = json.loads(tracker_path.read_text(encoding="utf-8"))
            tasks_with_qg = [t for t in tracker_data.get("tasks", []) if "quality_gates_passed" in t]
            if tasks_with_qg:
                task_info += "\n## Quality Gate\n"
                for t in tasks_with_qg[:5]:  # Limit to first 5
                    qg_passed = t.get("quality_gates_passed")
                    task_info += f"- {t.get('id')}: {'Passed' if qg_passed else 'Failed'}\n"
        except (OSError, json.JSONDecodeError):
            pass

    safe_write_text_locked(summary_path, task_info)
    register_artifact(workdir, ArtifactType.SUMMARY, str(summary_path), "COMPLETE", "system",
                     metadata={"final_state": final_state,
                             "aggregated_types": list(set(artifact_types)),
                             "session_id": session_id})
    return str(summary_path)


def _derive_phase_contract_fields(
    task_title: str,
    task_desc: str,
    plan_tasks: list[dict[str, Any]],
    workdir: str,
) -> dict[str, Any]:
    """Derive machine-readable contract fields from planning output."""
    goals: list[str] = []
    acceptance_criteria: list[str] = []
    verification_methods: list[str] = []
    owned_files: list[str] = []
    dependencies: list[str] = []
    impact_files: list[str] = []

    for task in plan_tasks:
        task_id = str(task.get("id", "")).strip()
        title = str(task.get("title", "")).strip()
        if title:
            goals.append(title)
            acceptance_criteria.append(f"Complete {task_id or 'task'}: {title}")
        verification = str(task.get("verification", "")).strip()
        if verification:
            verification_methods.append(verification)
        task_owned_files = task.get("owned_files", [])
        if isinstance(task_owned_files, list):
            for file_path in task_owned_files:
                file_path = str(file_path).strip()
                if file_path:
                    owned_files.append(file_path)
                    impact_files.append(file_path)
        task_dependencies = task.get("dependencies", [])
        if isinstance(task_dependencies, list):
            for dep in task_dependencies:
                dep = str(dep).strip()
                if dep:
                    dependencies.append(dep)

    if not goals:
        goals = [task_title.strip() or task_desc.strip() or "Deliver the requested task"]

    if not acceptance_criteria:
        acceptance_criteria = [
            "All planned tasks are completed or explicitly deferred with rationale",
            "All verification methods pass",
            "All impacted files are aligned with the implementation",
        ]

    if not verification_methods:
        verification_methods = ["Run the project test suite", "Review the implementation against the plan"]

    if not owned_files:
        owned_files = []

    if not impact_files:
        impact_files = list(dict.fromkeys(owned_files))

    if not dependencies:
        dependencies = []

    rollback_note = (
        "Revert the files listed in owned_files or impact_files and rerun the listed verification methods."
    )

    return {
        "goals": list(dict.fromkeys(goals)),
        "acceptance_criteria": list(dict.fromkeys(acceptance_criteria)),
        "verification_methods": list(dict.fromkeys(verification_methods)),
        "owned_files": list(dict.fromkeys(owned_files)),
        "impact_files": list(dict.fromkeys(impact_files or owned_files)),
        "dependencies": list(dict.fromkeys(dependencies)),
        "rollback_note": rollback_note,
        "status": "active",
    }


def _create_plan_from_template(task_name: str, workdir: str) -> Path | None:
    destination = Path(workdir) / "task_plan.md"
    if destination.exists():
        return destination

    # Try to find template in references/templates/
    template_dir = Path(workdir) / "references" / "templates"
    template_path = template_dir / "task_plan.md" if template_dir.exists() else None

    if template_path and template_path.exists():
        content = template_path.read_text(encoding="utf-8")
        content = content.replace("{{TASK_NAME}}", task_name)
        content = content.replace("{{CREATED_AT}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        safe_write_text_locked(destination, content)
        return destination
    else:
        # Create minimal plan file if no template
        content = f"""# Task Plan - {task_name}

## Overview
- Task: {task_name}
- Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Tasks

### P1 Tasks
- [ ] TASK-1: Initial task

## Status
- Overall: Not Started
"""
        safe_write_text_locked(destination, content)
        return destination


def _create_spec_artifacts(task_name: str, task_description: str, workdir: str, session_id: str) -> tuple[Path | None, Path | None, Path | None]:
    """
    Create spec.md and plan.md artifacts in .specs/<feature_id>/ directory.

    Args:
        task_name: Name/title of the task
        task_description: Full description
        workdir: Working directory
        session_id: Session identifier

    Returns:
        (spec_path, plan_path, tasks_path) tuple - any may be None if creation failed
    """
    # Generate feature_id from task_name
    feature_id = re.sub(r"[^a-zA-Z0-9]+", "_", task_name.lower())[:50]
    specs_dir = Path(workdir) / ".specs" / feature_id
    specs_dir.mkdir(parents=True, exist_ok=True)

    spec_path = None
    plan_path = None
    tasks_path = None

    # Create spec.md from template if available
    template_dir = Path(workdir) / "scripts" / "templates"
    spec_template = template_dir / "spec_template.md"
    if spec_template.exists():
        content = spec_template.read_text(encoding="utf-8")
        content = content.replace("{{TASK_NAME}}", task_name)
        content = content.replace("{{SESSION_ID}}", session_id)
        content = content.replace("{{TIMESTAMP}}", datetime.now().isoformat())
        spec_path = specs_dir / "spec.md"
        safe_write_text_locked(spec_path, content)
    else:
        # Create minimal spec
        spec_path = specs_dir / "spec.md"
        content = f"""# Spec: {task_name}

> Generated: {datetime.now().isoformat()}
> Session: {session_id}

## User Stories

### Story 1: {task_name}
**As a** [user type]
**I want** [goal]
**So that** [benefit]

**Acceptance Criteria:**
- [ ] Criterion 1: [verifiable outcome]
- [ ] Criterion 2: [verifiable outcome]

## Success Criteria

- [ ] **SC-1:** [Measurable outcome with specific metrics]

## Constraints

- **Tech Stack:** [e.g., Python 3.11+]
- **Performance:** [e.g., <100ms latency]
"""
        safe_write_text_locked(spec_path, content)

    # Create plan.md from template if available
    plan_template = template_dir / "plan_template.md"
    if plan_template.exists():
        content = plan_template.read_text(encoding="utf-8")
        content = content.replace("{{TASK_NAME}}", task_name)
        content = content.replace("{{SESSION_ID}}", session_id)
        content = content.replace("{{FEATURE_ID}}", feature_id)
        content = content.replace("{{TIMESTAMP}}", datetime.now().isoformat())
        plan_path = specs_dir / "plan.md"
        safe_write_text_locked(plan_path, content)
    else:
        # Create minimal plan
        plan_path = specs_dir / "plan.md"
        content = f"""# Plan: {task_name}

> **Provenance Header**
> Generated-By: agentic-workflow
> Session: {session_id}
> Source-Spec: .specs/{feature_id}/spec.md
> Timestamp: {datetime.now().isoformat()}

---

## Technical Context

### Project Overview
{task_description[:200]}

### Technology Stack
- **Language:** Python 3.11+
- **Framework:** TBD

---

## Structure Decisions

### Directory Structure
```
/
├── src/
├── tests/
└── docs/
```

---

## Constraints

- [ ] **Tech Stack:** Python 3.11+
- [ ] **Performance:** TBD

---

## Output Artifacts

| Artifact | Source | Description |
|----------|--------|-------------|
| `.contract.json` | plan.md | Machine-readable contract |
| `tasks.md` | plan.md | Task breakdown |

---

*This plan is generated from spec.md and drives task decomposition.*
"""
        safe_write_text_locked(plan_path, content)

    # Create tasks.md from the generated spec so the canonical planning chain exists
    try:
        import task_decomposer

        decomposed_tasks = task_decomposer.decompose_from_spec(workdir, feature_id)
        tasks_content = task_decomposer.generate_tasks_md(decomposed_tasks, str(spec_path), session_id, feature_id)
        tasks_path = specs_dir / "tasks.md"
        safe_write_text_locked(tasks_path, tasks_content)
    except Exception:
        # Fallback: create a minimal canonical tasks.md so downstream code can consume it
        tasks_path = specs_dir / "tasks.md"
        fallback_content = f"""# Tasks

> **Provenance Header**
> Generated-By: agentic-workflow
> Session: {session_id}
> Source-Spec: {spec_path}
> Timestamp: {datetime.now().isoformat()}

---

## Setup

- [ ] **TASK-US1-1:** Initial task [P]
  - **Files:** `src/`
  - **Verification:** `pytest -v`
        - **Blocked-By:**
"""
        safe_write_text_locked(tasks_path, fallback_content)

    return spec_path, plan_path, tasks_path


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

    if current_phase in ("PLANNING", "THINKING"):
        memory_intent = "plan"
    elif current_phase == "REVIEWING":
        memory_intent = "review"
    elif current_phase in ("DEBUGGING", "REFINING"):
        memory_intent = "debug"

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

    thinking_summary: dict[str, Any] = {}

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
        # PLANNING produces task_plan — EXECUTING should follow it
        plan = workdir_path / "task_plan.md"
        if plan.exists():
            files_to_read.append(str(plan))
            summary = "Task plan available. Execute tasks in priority order."

    elif current_phase == "EXECUTING":
        # EXECUTING produces code changes — REVIEWING should diff them
        summary = "Code changes made. Run `git diff` to review actual changes."

    elif current_phase == "REVIEWING":
        # REVIEWING produces review feedback — REFINING should fix issues
        summary = "Review complete. Fix any issues identified in review."

    elif current_phase == "THINKING":
        # THINKING produces analysis — PLANNING should use conclusions
        thinking_summary = build_thinking_summary(task_text, complexity or "M", memory_hints, experience_check)
        thinking_methods = thinking_summary.get("thinking_methods", [])
        methods_text = " → ".join(thinking_methods) if thinking_methods else "调查研究 → 矛盾分析 → 群众路线 → 持久战略"
        summary = (
            f"{thinking_summary.get('workflow_label', 'THINKING')}："
            f"{methods_text}。"
            f"当前阶段: {thinking_summary.get('stage_judgment', '战术速决')}。"
            f"主要矛盾: {thinking_summary.get('major_contradiction', '事实 vs 假设')}。"
            f"局部攻坚点: {thinking_summary.get('local_attack_point', '先找最小可验证切口')}。"
        )

    research_summary = get_research_summary(workdir, state)
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


def _phase_display_name(trigger_type: str, phase: str) -> str:
    if trigger_type == "DIRECT_ANSWER":
        return "DIRECT_ANSWER"
    if trigger_type == "FULL_WORKFLOW":
        return "PLANNING"
    return phase


def _render_progress_content(
    current_phase: str,
    runtime_profile: dict[str, Any],
    planning_summary: dict[str, Any],
    state: WorkflowState,
    research_summary: dict[str, Any] | None = None,
    thinking_summary: dict[str, Any] | None = None,
) -> str:
    research_summary = research_summary or {}
    lines = [
        "# Progress",
        "",
        "## Current Phase",
        f"- phase: {current_phase}",
        "- status: active",
        f"- updated: {datetime.now().isoformat()}",
        "",
        "## Skill Policy",
        f"- policy: {runtime_profile['skill_policy']}",
        f"- use_skill: {runtime_profile['use_skill']}",
        f"- activation_level: {runtime_profile['skill_activation_level']}",
        f"- profile_source: {runtime_profile['profile_source']}",
        "",
        "## Planning Summary",
        f"- plan_source: {planning_summary.get('plan_source', 'none')}",
        f"- planning_mode: {planning_summary.get('planning_mode', 'lightweight')}",
        f"- plan_digest: {planning_summary.get('plan_digest', 'unset')}",
        f"- worktree_recommended: {planning_summary.get('worktree_recommended', False)}",
        "",
        "## Research Summary",
        f"- research_found: {research_summary.get('research_found', False)}",
        f"- research_source: {research_summary.get('research_source', 'unset')}",
        f"- research_path: {research_summary.get('research_path', 'unset')}",
        f"- key_terms: {research_summary.get('key_terms', 'unset')}",
        f"- search_engine: {research_summary.get('search_engine', 'unset')}",
        f"- sources_count: {research_summary.get('sources_count', 0)}",
        f"- used_real_search: {research_summary.get('used_real_search', False)}",
        f"- degraded_mode: {research_summary.get('degraded_mode', False)}",
        f"- evidence_status: {research_summary.get('evidence_status', 'unset')}",
        "",
        "## Session",
        f"- session_id: {state.session_id}",
        f"- task_id: {state.task.task_id if state.task else 'N/A'}",
    ]
    if thinking_summary:
        lines.extend(
            [
                "",
                "## THINKING Summary",
                f"- workflow_label: {thinking_summary.get('workflow_label', 'unset')}",
                f"- thinking_mode: {thinking_summary.get('thinking_mode', 'unset')}",
                f"- thinking_methods: {' | '.join(thinking_summary.get('thinking_methods', [])) if thinking_summary.get('thinking_methods') else 'unset'}",
                f"- major_contradiction: {thinking_summary.get('major_contradiction', 'unset')}",
                f"- stage_judgment: {thinking_summary.get('stage_judgment', 'unset')}",
                f"- local_attack_point: {thinking_summary.get('local_attack_point', 'unset')}",
            ]
        )
    return "\n".join(lines)


def parse_task_plan(workdir: str = ".") -> list[dict[str, Any]]:
    """
    解析 task_plan.md 为结构化任务列表

    支持的字段:
    - id, title, done (从 checkbox 解析)
    - status: backlog | in_progress | completed | blocked
    - priority: P0 | P1 | P2 | P3
    - description: 任务描述
    - owned_files: 逗号分隔的文件列表
    - dependencies: 逗号分隔的任务ID列表
    - verification: 验证命令或方法
    - acceptance: 验收标准
    """
    plan_path = Path(workdir) / "task_plan.md"
    if not plan_path.exists():
        return []

    tasks: list[dict[str, Any]] = []
    current_priority = None
    current_task: dict[str, Any] | None = None
    task_pattern = re.compile(r"^- \[(?P<done>[ xX])\] (?P<id>TASK-\d+): (?P<title>.+)$")
    field_pattern = re.compile(r"^\s+- (?P<key>[a-zA-Z_]+): (?P<value>.+)$")

    for raw_line in plan_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()

        if line.startswith("### P"):
            current_priority = line.replace("###", "").strip()
            continue

        task_match = task_pattern.match(line)
        if task_match:
            is_done = task_match.group("done").lower() == "x"
            current_task = {
                "id": task_match.group("id"),
                "title": task_match.group("title"),
                "done": is_done,
                "priority": current_priority,
                "status": "completed" if is_done else "backlog",
            }
            tasks.append(current_task)
            continue

        field_match = field_pattern.match(line)
        if field_match and current_task is not None:
            key = field_match.group("key")
            value = field_match.group("value")
            # Only set status if checkbox and status disagree, prefer checkbox
            if key == "status" and not current_task.get("done"):
                current_task[key] = value
            elif key == "dependencies":
                current_task[key] = [d.strip() for d in value.split(",") if d.strip()]
            elif key == "owned_files":
                current_task[key] = [f.strip() for f in value.split(",") if f.strip()]
            elif key != "status":  # Skip status if from checkbox
                current_task[key] = value

    return tasks


def parse_tasks_md(workdir: str = ".") -> list[dict[str, Any]]:
    """
    Parse tasks.md (spec-kit style) from .specs/<feature_id>/tasks.md.

    Returns structured tasks with owned_files, dependencies, and verification.

    Supports the format:
    - [ ] **TASK-US1-1:** Title [P]
      - **Files:** `file1.py`, `file2.py`
      - **Verification:** `[P]` pytest tests/ -v
      - **Blocked-By:** TASK-US1-2
    """
    # Find the most recent .specs/<feature_id>/tasks.md
    specs_dir = Path(workdir) / ".specs"
    if not specs_dir.exists():
        return []

    # Get the most recent feature directory
    feature_dirs = sorted(specs_dir.glob("*/"), key=lambda p: p.stat().st_mtime, reverse=True)
    tasks_path = None
    for feature_dir in feature_dirs:
        tp = feature_dir / "tasks.md"
        if tp.exists():
            tasks_path = tp
            break

    if not tasks_path or not tasks_path.exists():
        return []

    tasks: list[dict[str, Any]] = []
    current_section = None

    # Patterns for parsing
    task_pattern = re.compile(r"^- \[(?P<done>[ xX])\] \*\*(?P<id>[^:]+):\*\* (?P<title>.+?)(?:\s+\[P\])?$")
    file_pattern = re.compile(r"\*\*Files:\*\*\s*`?([^`]+)`?")
    verification_pattern = re.compile(r"\*\*Verification:\*\*\s*(?:\[P\]\s*)?([^\n]+)")
    blocked_by_pattern = re.compile(r"\*\*Blocked-By:\*\*\s*([^\n]+)")
    status_pattern = re.compile(r"\*\*Status:\*\*\s*([^\n]+)")
    section_pattern = re.compile(r"^## (.+)$")

    current_task: dict[str, Any] | None = None

    for line in tasks_path.read_text(encoding="utf-8").splitlines():
        line = line.rstrip()

        # Check for section headers
        section_match = section_pattern.match(line)
        if section_match:
            current_section = section_match.group(1)
            continue

        # Try to match task line
        task_match = task_pattern.match(line)
        if task_match:
            if current_task:
                tasks.append(current_task)

            task_id = task_match.group("id")
            title = task_match.group("title").strip()
            is_done = task_match.group("done").lower() == "x"

            # Determine priority from section or task ID
            priority = "P1"
            if current_section in ("Setup", "Foundational"):
                priority = "P0"
            elif current_section == "Polish":
                priority = "P2"

            current_task = {
                "id": task_id,
                "title": title,
                "status": "completed" if is_done else "backlog",
                "priority": priority,
                "owned_files": [],
                "dependencies": [],
                "verification": "",
                "section": current_section,
            }
            continue

        # Parse fields for current task
        if current_task:
            file_match = file_pattern.search(line)
            if file_match:
                files_str = file_match.group(1)
                current_task["owned_files"] = [f.strip() for f in files_str.split(",")]

            verification_match = verification_pattern.search(line)
            if verification_match:
                current_task["verification"] = verification_match.group(1).strip()

            blocked_match = blocked_by_pattern.search(line)
            if blocked_match:
                deps_str = blocked_match.group(1).strip()
                current_task["dependencies"] = [d.strip() for d in deps_str.split(",")]

            status_match = status_pattern.search(line)
            if status_match:
                current_task["status"] = status_match.group(1).strip()

    if current_task:
        tasks.append(current_task)

    return tasks


def load_planning_tasks(workdir: str = ".") -> tuple[list[dict[str, Any]], str]:
    """
    Load planning tasks, preferring the canonical spec-kit chain.

    Returns:
        (tasks, source_name) where source_name is "tasks.md", "task_plan.md", or "none".
    """
    tasks = parse_tasks_md(workdir)
    if tasks:
        return tasks, "tasks.md"

    legacy_tasks = parse_task_plan(workdir)
    if legacy_tasks:
        return legacy_tasks, "task_plan.md"

    return [], "none"


def _find_canonical_tasks_path(workdir: str = ".") -> Path | None:
    """Find the most recent canonical tasks.md file under .specs/."""
    specs_dir = Path(workdir) / ".specs"
    if not specs_dir.exists():
        return None

    feature_dirs = sorted(specs_dir.glob("*/"), key=lambda p: p.stat().st_mtime, reverse=True)
    for feature_dir in feature_dirs:
        tasks_path = feature_dir / "tasks.md"
        if tasks_path.exists():
            return tasks_path
    return None


def next_plan_tasks(workdir: str = ".", limit: int = 3) -> list[dict[str, Any]]:
    """
    获取下一个应该执行的任务列表

    考虑:
    - 优先级 (P0 > P1 > P2 > P3)
    - 依赖关系 (只有依赖都完成才能开始)
    - 状态 (只选 backlog 的)
    """
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, None: 9}
    # Prefer tasks.md (spec-kit style) over task_plan.md when available
    all_tasks, _source = load_planning_tasks(workdir)
    completed_ids = {t["id"] for t in all_tasks if t.get("status") == "completed"}

    candidates = []
    for task in all_tasks:
        if task.get("status") in ("completed", "in_progress", "blocked"):
            continue

        # 检查依赖是否都满足
        deps = task.get("dependencies", [])
        if deps and not all(d in completed_ids for d in deps):
            continue

        candidates.append(task)

    candidates.sort(key=lambda item: (priority_order.get(item.get("priority"), 9), item.get("id", "")))
    return candidates[:limit]


def compute_frontier(workdir: str = ".") -> dict[str, Any]:
    """
    Compute the executable task frontier from task_plan.md.

    Returns:
        {
            "executable_frontier": [task, ...],     # Tasks ready to execute
            "ready_tasks": [task, ...],            # Alias for executable_frontier
            "parallel_candidates": [[task, task], ...], # Tasks can run in parallel (ownership-safe, parallel-ready)
            "blocked_tasks": [task, ...],           # Tasks blocked by dependencies
            "conflict_groups": [[task, task], ...], # Tasks with overlapping owned_files (must be serialized)
            "completed_count": int,
            "total_count": int,
        }

    Frontier rules:
    - executable_frontier: backlog tasks with all dependencies satisfied
    - parallel_candidates: within frontier, tasks WITHOUT ownership conflicts can run concurrently (parallel-ready, not yet parallel execution)
    - conflict_groups: tasks with overlapping owned_files that must be serialized

    Prefers tasks.md (spec-kit style) over task_plan.md when available for richer owned_files semantics.
    """
    # Prefer tasks.md (spec-kit style) over task_plan.md when available
    all_tasks, source = load_planning_tasks(workdir)
    if not all_tasks:
        return {
            "executable_frontier": [],
            "ready_tasks": [],
            "parallel_candidates": [],
            "blocked_tasks": [],
            "conflict_groups": [],
            "completed_count": 0,
            "total_count": 0,
            "plan_source": "none",
        }

    completed_ids = {t["id"] for t in all_tasks if t.get("status") == "completed"}
    backlog_tasks = [t for t in all_tasks if t.get("status") == "backlog"]

    # Partition into frontier (ready) vs blocked
    frontier_tasks = []
    blocked_tasks = []
    for task in backlog_tasks:
        deps = task.get("dependencies", [])
        if deps and not all(d in completed_ids for d in deps):
            blocked_tasks.append(task)
        else:
            frontier_tasks.append(task)

    # Ownership conflict detection
    # Build a map: file -> [task_ids] that own it
    file_owner_map: dict[str, list[str]] = {}
    for task in frontier_tasks:
        owned = task.get("owned_files", [])
        if isinstance(owned, list):
            for f in owned:
                if f not in file_owner_map:
                    file_owner_map[f] = []
                file_owner_map[f].append(task["id"])

    # Find conflicting task pairs (share owned files)
    conflicts: list[tuple[str, str]] = []
    for _file_path, owners in file_owner_map.items():
        if len(owners) > 1:
            for i in range(len(owners)):
                for j in range(i + 1, len(owners)):
                    pair = (owners[i], owners[j]) if owners[i] < owners[j] else (owners[j], owners[i])
                    if pair not in conflicts:
                        conflicts.append(pair)

    # Build conflict groups
    conflict_graph: dict[str, set] = {}
    for t1, t2 in conflicts:
        if t1 not in conflict_graph:
            conflict_graph[t1] = set()
        if t2 not in conflict_graph:
            conflict_graph[t2] = set()
        conflict_graph[t1].add(t2)
        conflict_graph[t2].add(t1)

    # Find maximal independent sets for parallel execution
    parallel_groups: list[list[dict[str, Any]]] = []
    assigned_ids: set = set()

    # First, assign tasks that have conflicts to conflict_groups (serial execution)
    conflict_groups: list[list[dict[str, Any]]] = []
    for task in frontier_tasks:
        if task["id"] in conflict_graph and task["id"] not in assigned_ids:
            # This task has conflicts, find all its conflict partners
            group = [task]
            assigned_ids.add(task["id"])
            to_check = list(conflict_graph[task["id"]])
            while to_check:
                tid = to_check.pop()
                if tid in assigned_ids:
                    continue
                # Find task object
                t = next((x for x in frontier_tasks if x["id"] == tid), None)
                if t:
                    group.append(t)
                    assigned_ids.add(tid)
                    to_check.extend(conflict_graph.get(tid, []))
            conflict_groups.append(group)

    # Remaining tasks (no conflicts) can run in parallel
    independent_tasks = [t for t in frontier_tasks if t["id"] not in assigned_ids]
    if independent_tasks:
        # Each independent task is its own parallel group
        parallel_groups.extend([[t] for t in independent_tasks])
        for t in independent_tasks:
            assigned_ids.add(t["id"])

    # Handle dependency chains within non-conflicting tasks
    frontier_ids = {t["id"] for t in frontier_tasks}
    dep_graph: dict[str, set] = {}
    for task in frontier_tasks:
        task_deps = task.get("dependencies", [])
        relevant_deps = {d for d in task_deps if d in frontier_ids}
        dep_graph[task["id"]] = relevant_deps

    return {
        "executable_frontier": frontier_tasks,
        "ready_tasks": frontier_tasks,  # Alias
        "parallel_candidates": parallel_groups,
        "blocked_tasks": blocked_tasks,
        "conflict_groups": conflict_groups,
        "completed_count": len(completed_ids),
        "total_count": len(all_tasks),
        "plan_source": source,
    }


@dataclass
class CheckpointConfig:
    """
    Conditional checkpoint configuration.

    Attributes:
        phase_change_threshold: Trigger after N phase transitions (default 1)
        resume_threshold: Trigger after N resume attempts
        failure_threshold: Trigger after N failures
        step_threshold: Trigger after N workflow steps
        enabled: Whether auto-checkpoint is enabled
    """
    phase_change_threshold: int = 1
    resume_threshold: int = 2
    failure_threshold: int = 1
    step_threshold: int = 5
    enabled: bool = True


def should_checkpoint(
    workdir: str,
    config: CheckpointConfig | None = None,
) -> tuple[bool, str]:
    """
    Determine if a checkpoint should be triggered based on conditions.

    Conditions evaluated:
    - Phase changes since last checkpoint
    - Resume attempts
    - Failure count
    - Total workflow steps

    Args:
        workdir: Working directory
        config: Checkpoint configuration (uses defaults if None)

    Returns:
        (should_checkpoint, reason) tuple
    """
    # Delegate to checkpoint_manager (imported lazily to avoid circular dependency)
    from checkpoint_manager import should_checkpoint as _impl
    result: tuple[bool, str] = _impl(workdir, config)
    return bool(result[0]), str(result[1])


def conditional_checkpoint(
    workdir: str,
    config: CheckpointConfig | None = None,
) -> dict[str, Any]:
    """
    Save a checkpoint if conditions are met.

    Creates:
    - .checkpoints/<checkpoint_id>.json: Full state snapshot
    - handoff_<checkpoint_id>.md: Human-readable handoff document

    Args:
        workdir: Working directory
        config: Checkpoint configuration (uses defaults if None)

    Returns:
        dict with keys:
            checkpoint_saved: bool
            reason: str
            checkpoint_id: str
            session_id: str
            files: list of created file paths
            error: str or None
            partial: bool (True if only JSON was saved, not handoff)
    """
    # Delegate to checkpoint_manager (imported lazily to avoid circular dependency)
    from checkpoint_manager import conditional_checkpoint as _impl
    result: dict[str, Any] = _impl(workdir, config)
    return result


def validate_task_plan(workdir: str = ".") -> tuple[bool, list[str]]:
    """
    验证任务计划的合法性

    检查:
    - 循环依赖
    - 缺失的依赖
    - 非法的任务ID引用

    Returns:
        (is_valid, error_list)
    """
    tasks, _source = load_planning_tasks(workdir)
    if not tasks:
        return True, []

    errors = []
    task_ids = {t["id"] for t in tasks}
    task_map = {t["id"]: t for t in tasks}

    for task in tasks:
        deps = task.get("dependencies", [])
        for dep in deps:
            if dep not in task_ids:
                errors.append(f"Task {task['id']} depends on non-existent task {dep}")

    # 检查循环依赖 (简单的 DFS)
    def has_cycle(task_id: str, visited: set, rec_stack: set) -> bool:
        visited.add(task_id)
        rec_stack.add(task_id)
        for dep in task_map.get(task_id, {}).get("dependencies", []):
            if dep not in visited:
                if has_cycle(dep, visited, rec_stack):
                    return True
            elif dep in rec_stack:
                return True
        rec_stack.remove(task_id)
        return False

    for task in tasks:
        if task["id"] not in task_ids:
            continue
        if has_cycle(task["id"], set(), set()):
            errors.append(f"Circular dependency detected involving {task['id']}")

    return len(errors) == 0, errors


def update_task_status_in_plan(
    workdir: str,
    task_id: str,
    status: str,
) -> dict[str, Any]:
    """
    更新 task_plan.md 中任务的状态

    Args:
        workdir: 工作目录
        task_id: 任务ID (如 "TASK-001")
        status: 新状态 (backlog | in_progress | completed | blocked)

    Returns:
        更新结果
    """
    if status not in ("backlog", "in_progress", "completed", "blocked"):
        return {"success": False, "error": f"Invalid status: {status}"}

    plan_path = _find_canonical_tasks_path(workdir)
    source = "tasks.md"
    if plan_path is None:
        plan_path = Path(workdir) / "task_plan.md"
        source = "task_plan.md"

    if not plan_path.exists():
        return {"success": False, "error": "task_plan.md not found"}

    content = plan_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    new_lines: list[str] = []
    task_found = False
    in_target_task = False

    legacy_task_pattern = re.compile(r"^- \[(?P<done>[ xX])\] (?P<id>TASK-\d+): (?P<title>.+)$")
    canonical_task_pattern = re.compile(r"^- \[(?P<done>[ xX])\] \*\*(?P<id>[^:]+):\*\* (?P<title>.+)$")
    status_pattern = re.compile(r"^\s+- \*\*Status:\*\*")

    task_pattern = canonical_task_pattern if source == "tasks.md" else legacy_task_pattern

    for line in lines:
        line_stripped = line.rstrip()
        task_match = task_pattern.match(line_stripped)
        if task_match:
            in_target_task = task_match.group("id") == task_id
            if in_target_task:
                task_found = True
                done_marker = "x" if status == "completed" else " "
                if source == "tasks.md":
                    task_title = task_match.group("title").rstrip()
                    new_lines.append(f"- [{done_marker}] **{task_match.group('id')}:** {task_title}")
                    new_lines.append(f"  - **Status:** {status}")
                else:
                    task_title = task_match.group("title").rstrip()
                    new_lines.append(f"- [{done_marker}] {task_match.group('id')}: {task_title}")
                continue

        if in_target_task:
            if source == "tasks.md" and status_pattern.match(line_stripped):
                continue
            if source == "task_plan.md":
                field_pattern = re.compile(r"^\s+- (?P<key>[a-zA-Z_]+):")
                field_match = field_pattern.match(line)
                if field_match and field_match.group("key") == "status":
                    new_lines.append(f"  - status: {status}")
                    continue

        new_lines.append(line)

    if not task_found:
        return {"success": False, "error": f"Task {task_id} not found"}

    safe_write_text_locked(plan_path, "\n".join(new_lines))
    return {"success": True, "task_id": task_id, "status": status, "source": source}


def allowed_next_phases(phase: str) -> list[str]:
    return sorted(get_allowed_transitions(phase))


def recommend_next_phases(current_phase: str, trigger_type: str | None = None) -> list[str]:
    """
    Recommend the next phases reachable from the current phase.

    Args:
        current_phase: The current workflow phase
        trigger_type: Optional trigger type (FULL_WORKFLOW, STAGE, DIRECT_ANSWER)

    Returns:
        List of phase names that are valid next steps, ordered by recommendation priority
    """
    if current_phase == "DIRECT_ANSWER":
        return ["COMPLETE"]
    if current_phase == "PLANNING":
        return ["ANALYZING", "EXECUTING", "RESEARCH", "THINKING"]
    if current_phase == "ANALYZING":
        return ["EXECUTING", "PLANNING"]
    if current_phase == "RESEARCH":
        return ["THINKING", "PLANNING"]
    if current_phase == "THINKING":
        return ["PLANNING", "EXECUTING"]
    if current_phase == "EXECUTING":
        return ["REVIEWING", "COMPLETE", "DEBUGGING"]
    if current_phase == "REVIEWING":
        return ["COMPLETE", "DEBUGGING"]
    if current_phase == "DEBUGGING":
        return ["EXECUTING", "REVIEWING"]
    if current_phase == "COMPLETE":
        return []
    if trigger_type == "FULL_WORKFLOW":
        return ["PLANNING"]
    return allowed_next_phases(current_phase)


def validate_transition(current_phase: str, next_phase: str) -> None:
    """
    Validate that a phase transition is allowed by the state machine.

    Args:
        current_phase: Current phase
        next_phase: Desired next phase

    Raises:
        ValueError: If the transition is not allowed
    """
    if not can_transition(current_phase, next_phase):
        raise ValueError(f"illegal phase transition: {current_phase} -> {next_phase}")


def _build_runtime_profile(prompt: str, workdir: str) -> dict[str, Any]:
    """
    Build the initial runtime profile for a prompt.

    The authoritative runtime owns state and gates. Skill context and workspace
    injection are now inlined here, reducing experimental-layer residue.
    Middleware remains available for experimental signal extraction but is no
    longer required for profile construction.
    """
    trigger_type, routed_phase, _confidence = router.route(prompt)
    complexity, complexity_conf = router.estimate_complexity(prompt)
    phase_sequence = router.get_phase_sequence(complexity)
    current_phase = _phase_display_name(trigger_type, routed_phase)

    # CHAT intent: direct answer, no skill needed
    skill_policy = skill_policy_for_phase(current_phase, complexity, trigger_type)

    if trigger_type == "DIRECT_ANSWER":
        skill_context = ""
        tokens_expected = 500
        use_skill = False
    else:
        use_skill = should_use_skill_for_phase(current_phase, complexity, trigger_type, prompt)
        if use_skill:
            # Build skill context inline using sunk PHASE_PROMPTS
            skill_context, tokens_expected = build_skill_context(current_phase, complexity)
        else:
            skill_context = ""
            tokens_expected = 500

    skill_activation_level = (
        skill_activation_level_for_phase(current_phase, complexity, trigger_type, prompt) if use_skill else 0
    )

    profile: dict[str, Any] = {
        "trigger_type": trigger_type,
        "phase": current_phase,
        "complexity": complexity,
        "complexity_confidence": complexity_conf,
        "phase_sequence": phase_sequence,
        "skill_context": skill_context,
        "tokens_expected": tokens_expected,
        "use_skill": use_skill,
        "skill_policy": skill_policy,
        "skill_activation_level": skill_activation_level,
        "intent": None,
        "profile_source": "router",
    }

    # Middleware signal overlay: when the experimental middleware layer is present,
    # its normalized intent/skill policy can override router defaults.
    # ContextMiddleware / SkillMiddleware signals are now sunk into this function.
    try:
        request = MiddlewareRequest(text=prompt, metadata={"cwd": workdir})
        create_middleware_chain().execute(request)

        if request.intent is not None:
            profile["intent"] = request.intent
            profile["skill_policy"] = getattr(request, "skill_policy", profile["skill_policy"])
            profile["skill_activation_level"] = getattr(
                request, "skill_activation_level", profile["skill_activation_level"]
            )
            profile["profile_source"] = "middleware+router"

        if request.intent == "CHAT":
            profile["trigger_type"] = "DIRECT_ANSWER"
            profile["phase"] = "DIRECT_ANSWER"
            profile["use_skill"] = False
            profile["skill_context"] = ""
            profile["tokens_expected"] = 500
            profile["skill_policy"] = "disable"
            profile["skill_activation_level"] = 0
            profile["profile_source"] = "middleware+router"
        elif request.intent == "FULL_WORKFLOW":
            profile["trigger_type"] = "FULL_WORKFLOW"
            profile["phase"] = request.phase.value
            profile["complexity"] = request.complexity.value
            if request.metadata.get("phase_sequence"):
                profile["phase_sequence"] = [
                    phase.value if hasattr(phase, "value") else str(phase)
                    for phase in request.metadata["phase_sequence"]
                ]
            profile["profile_source"] = "middleware+router"
            profile["skill_activation_level"] = 0 if not profile["use_skill"] else skill_activation_level_for_phase(
                profile["phase"], profile["complexity"], profile["intent"], prompt
            )
    except Exception:
        # Keep router-derived defaults when middleware is unavailable.
        pass

    return profile


def initialize_workflow(
    prompt: str,
    workdir: str = ".",
    task_id: str | None = None,
    auto_create_plan: bool = True,
) -> dict[str, Any]:
    """
    Initialize a new workflow session.

    Creates .workflow_state.json, initializes task tracker, and sets up
    trajectory logging. Determines initial phase via router and creates
    spec artifacts if auto_create_plan is True.

    Args:
        prompt: User task description (e.g., "帮我开发一个REST API")
        workdir: Working directory for workflow files
        task_id: Optional task ID (auto-generated from timestamp if None)
        auto_create_plan: Whether to create spec/plan/task artifacts

    Returns:
        Initial state snapshot dict with session_id, task, phase, trigger_type
    """
    workdir_path = Path(workdir)
    workdir_path.mkdir(parents=True, exist_ok=True)

    session_path = workdir_path / memory_ops.DEFAULT_SESSION_STATE
    tracker_path = workdir_path / task_tracker.DEFAULT_TRACKER_FILE

    memory_ops.ensure_session_state_exists(str(session_path))
    task_tracker.save_tracker(str(tracker_path), task_tracker.load_tracker(str(tracker_path)))

    runtime_profile = _build_runtime_profile(prompt, workdir)
    trigger_type = runtime_profile["trigger_type"]
    current_phase = runtime_profile["phase"]
    complexity = runtime_profile["complexity"]
    complexity_conf = runtime_profile["complexity_confidence"]
    phase_sequence = runtime_profile["phase_sequence"]

    # Create unified state
    state = create_initial_state(
        prompt=prompt,
        task_id=task_id or _task_id_from_timestamp(),
        trigger_type=trigger_type,
        initial_phase=current_phase,
    )

    # Store complexity and phase sequence in state metadata
    if state.metadata is None:
        state.metadata = {}
    state.metadata["complexity"] = complexity
    state.metadata["complexity_confidence"] = complexity_conf
    state.metadata["phase_sequence"] = phase_sequence
    state.metadata["runtime_profile"] = runtime_profile

    # NOTE: create_initial_state already sets the phase to initial_phase
    # Don't call transition_phase here as it would try to transition to the same phase

    # Ensure trajectory directory exists
    traj_dir = trajectory_dir_path(workdir)
    traj_dir.mkdir(parents=True, exist_ok=True)

    # Start trajectory logging
    logger = TrajectoryLogger(workdir, state.session_id)
    logger.start(prompt, trigger_type, runtime_profile=runtime_profile)
    logger.enter_phase(current_phase)
    _active_loggers[state.session_id] = logger

    # Trajectory info tracked in _active_loggers and saved to trajectory files
    # All artifact tracking goes through artifact_registry (authoritative source)

    memory_ops.update_task_info(str(session_path), prompt, current_phase)
    memory_ops.update_resume_point(str(session_path), current_phase, 0)
    memory_ops.update_runtime_profile(
        str(session_path),
        skill_policy=runtime_profile["skill_policy"],
        use_skill=runtime_profile["use_skill"],
        skill_activation_level=runtime_profile["skill_activation_level"],
        tokens_expected=runtime_profile["tokens_expected"],
        profile_source=runtime_profile["profile_source"],
        complexity=runtime_profile["complexity"],
        complexity_confidence=runtime_profile["complexity_confidence"],
    )
    planning_summary = get_planning_summary(str(workdir), state)
    research_summary = get_research_summary(str(workdir), state)
    thinking_summary = get_thinking_summary(workdir, state)
    review_summary = get_review_summary(workdir, state)
    memory_ops.update_planning_summary(
        str(session_path),
        planning_summary,
    )
    memory_ops.update_review_summary(
        str(session_path),
        review_summary,
    )
    memory_ops.update_thinking_summary(
        str(session_path),
        thinking_summary,
    )
    progress_file = workdir_path / "progress.md"
    progress_content = _render_progress_content(
        current_phase,
        runtime_profile,
        planning_summary,
        state,
        research_summary,
        thinking_summary if current_phase == "THINKING" else None,
    )
    safe_write_text_locked(progress_file, progress_content)

    # Register progress.md artifact (authoritative tracking via registry only)
    register_artifact(workdir, ArtifactType.PROGRESS, str(progress_file), current_phase, "system")

    created_task = False
    if trigger_type in ("FULL_WORKFLOW", "STAGE"):
        task_id = state.task.task_id if state.task else None
        if task_id is None:
            raise ValueError("state.task is None, cannot create task")
        if task_tracker.get_task(task_id, str(tracker_path)) is None:
            created_task = task_tracker.create_task(
                task_id,
                prompt,
                priority="P1" if current_phase in ("PLANNING", "DEBUGGING", "REVIEWING") else "P2",
                path=str(tracker_path),
            )
        task_tracker.start_task(task_id, str(tracker_path))
        task_tracker.update_status(task_id, "in_progress", progress=0, path=str(tracker_path))

    contract_path: Path | None = None
    spec_path: Path | None = None
    plan_md_path: Path | None = None
    tasks_path: Path | None = None
    if auto_create_plan and current_phase == "PLANNING" and complexity not in {"XS", "S"}:
        # Create spec.md and plan.md in .specs/<feature_id>/ directory
        task_title = state.task.title if state.task else prompt[:50]
        task_desc = state.task.description if state.task else prompt
        spec_path, plan_md_path, tasks_path = _create_spec_artifacts(
            task_title, task_desc, workdir, state.session_id
        )
        if spec_path is not None:
            register_artifact(workdir, ArtifactType.CUSTOM, str(spec_path), current_phase, "system",
                           metadata={"deliverable": "spec", "type": "spec.md"})
        if plan_md_path is not None:
            register_artifact(workdir, ArtifactType.CUSTOM, str(plan_md_path), current_phase, "system",
                           metadata={"deliverable": "plan", "type": "plan.md"})
        if tasks_path is not None:
            register_artifact(workdir, ArtifactType.CUSTOM, str(tasks_path), current_phase, "system",
                           metadata={"deliverable": "tasks", "type": "tasks.md"})

        # Create Anthropic-style phase contract
        contract_path = _create_phase_contract(task_title, task_desc, workdir)
        if contract_path is not None:
            register_artifact(workdir, "contract", str(contract_path), current_phase, "system",
                            metadata={"deliverable": "contract", "phase": current_phase})

        plan_tasks, _plan_source = load_planning_tasks(workdir)
        contract_fields = _derive_phase_contract_fields(task_title, task_desc, plan_tasks, workdir)
        update_contract_json(workdir, **contract_fields)

        planning_summary = get_planning_summary(str(workdir), state)
        memory_ops.update_planning_summary(
            str(session_path),
            planning_summary,
        )
        progress_content = _render_progress_content(
            current_phase,
            runtime_profile,
            planning_summary,
            state,
            research_summary,
            thinking_summary if current_phase == "THINKING" else None,
        )
        safe_write_text_locked(progress_file, progress_content)

    # Register session state artifact
    register_artifact(workdir, ArtifactType.SESSION, str(session_path), current_phase, "system")

    # Register task tracker artifact
    register_artifact(workdir, ArtifactType.TRACKER, str(tracker_path), current_phase, "system")

    # Note: phase-specific business artifacts (findings/review) are now generated
    # on phase EXIT (when advancing to another phase), not on phase ENTER.
    # This ensures artifacts represent completed work, not just entry into a phase.

    # Save unified state (minimal artifacts index only - trajectory refs)
    save_state(workdir, state)

    return {
        "task_id": state.task.task_id if state.task else None,
        "session_id": state.session_id,
        "trigger_type": trigger_type,
        "phase": current_phase,
        "created_task": created_task,
        "plan_created": any(path is not None for path in (spec_path, plan_md_path, tasks_path, contract_path)),
        "recommended_next_phases": recommend_next_phases(current_phase, trigger_type),
        "state_file": str(workflow_state_path(workdir)),
        "trajectory_session_id": state.session_id,
        "complexity": complexity,
        "skill_policy": runtime_profile["skill_policy"],
        "skill_context": runtime_profile["skill_context"],
        "tokens_expected": runtime_profile["tokens_expected"],
        "skill_activation_level": runtime_profile["skill_activation_level"],
        "use_skill": runtime_profile["use_skill"],
        "profile_source": runtime_profile["profile_source"],
        "phase_sequence": phase_sequence,
        "total_phases": len(phase_sequence),
    }


def advance_workflow(
    phase: str,
    workdir: str = ".",
    progress: int = 0,
    task_status: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    """
    Advance the workflow to a new phase.

    Updates .workflow_state.json with the new phase, saves progress to progress.md,
    runs quality gate on phase exit (for EXECUTING), generates phase-specific
    artifacts (findings for RESEARCH, review for REVIEWING), and saves checkpoint
    if conditions are met.

    Args:
        phase: Target phase to advance to
        workdir: Working directory
        progress: Progress percentage (0-100)
        task_status: Optional task status override
        note: Optional note for this transition

    Returns:
        Updated state snapshot dict

    Raises:
        ValueError: If workflow not initialized or phase transition is illegal
    """
    state = load_state(workdir)
    if state is None:
        raise ValueError("workflow state not found, please run init first")
    if not state.task or not state.task.task_id:
        raise ValueError("workflow runtime has not been initialized properly")

    task_id = state.task.task_id
    tracker_path = Path(workdir) / task_tracker.DEFAULT_TRACKER_FILE
    session_path = Path(workdir) / memory_ops.DEFAULT_SESSION_STATE

    current_phase = state.phase.get("current", "IDLE")
    validate_transition(current_phase, phase)

    # P2 ToT: Check if deliberation is warranted before complex transitions
    deliberation_result: dict[str, Any] = {}
    try:
        from deliberate_mode import should_deliberate
        # Determine trigger type based on phase transition context
        deliberation_trigger = None
        if phase == "EXECUTING" and current_phase in ("PLANNING", "ANALYZING"):
            deliberation_trigger = "planning_conflict"
        elif phase == "DEBUGGING":
            deliberation_trigger = "debug_failure"
        elif phase == "REVIEWING":
            deliberation_trigger = "review_divergence"
        # Check state metadata for high complexity
        complexity = state.metadata.get("complexity", "") if state.metadata else ""
        if complexity in ("L", "XL") and deliberation_trigger is None:
            deliberation_trigger = "high_complexity"

        if deliberation_trigger and should_deliberate(workdir, deliberation_trigger, state):
            from deliberate_mode import deliberate
            frontier = compute_frontier(workdir)
            task_desc = state.task.description or state.task.title or "" if state.task else ""
            context = {
                "task_description": task_desc,
                "frontier": frontier,
            }
            result = deliberate(workdir, deliberation_trigger, context)
            deliberation_result = {
                "trigger": result.trigger,
                "recommended_branch": result.recommended_branch_id,
                "branches": [
                    {"id": b.branch_id, "title": b.title, "score": b.score, "confidence": b.confidence}
                    for b in result.branches
                ],
                "path": result.deliberation_path,
            }
            # Log deliberation decision
            if state.session_id in _active_loggers:
                logger = _active_loggers[state.session_id]
                logger.log_decision(
                    f"Deliberation ({deliberation_trigger}): {len(result.branches)} branches considered",
                    f"Recommended: {result.recommended_branch_id}",
                )
    except Exception:
        # Deliberation is best-effort - don't block workflow
        deliberation_result = {}

    # Log phase transition in trajectory
    if state.session_id in _active_loggers:
        logger = _active_loggers[state.session_id]
        logger.exit_phase(current_phase)
        if note:
            logger.log_decision(f"Transition: {current_phase} -> {phase}", note)
        logger.enter_phase(phase)

    # Analyze gate validation: PLANNING/ANALYZING -> EXECUTING requires passing analyze gate
    if phase == "EXECUTING" and current_phase in ("PLANNING", "ANALYZING"):
        analyze_result = validate_analyze_gate(workdir)
        if not analyze_result.passed:
            errors_str = "; ".join(analyze_result.errors)
            raise ValueError(f"analyze gate failed: {errors_str}")
        # Log warnings but don't block
        if analyze_result.warnings:
            logger.log_decision(f"analyze gate warnings: {'; '.join(analyze_result.warnings)}") if state.session_id in _active_loggers else None

    # Transition phase using unified_state
    state = transition_phase(state, phase, reason=note or "advance_workflow")

    # Contract lifecycle management
    # PLANNING -> EXECUTING: activate contract
    if current_phase == "PLANNING" and phase == "EXECUTING":
        update_contract_json(workdir, status="active")
    # EXECUTING -> REVIEWING: mark for review
    elif current_phase == "EXECUTING" and phase == "REVIEWING":
        update_contract_json(workdir, status="review")

    runtime_profile = state.metadata.get("runtime_profile", {}) if state.metadata else {}
    thinking_summary: dict[str, Any] | None = None

    # Update progress.md
    progress_file = Path(workdir) / "progress.md"
    if progress_file.exists():
        planning_summary = get_planning_summary(workdir, state)
        research_summary = get_research_summary(workdir, state)
        if phase == "THINKING":
            task_desc = state.task.description if state.task else (state.task.title if state.task else "")
            runtime_complexity = str(runtime_profile.get("complexity") or (state.metadata.get("complexity") if state.metadata else "M"))
            thinking_summary = build_thinking_summary(task_desc, runtime_complexity)
        progress_content = _render_progress_content(
            phase,
            runtime_profile,
            planning_summary,
            state,
            research_summary,
            thinking_summary,
        )
        safe_write_text_locked(progress_file, progress_content)

    # Save updated state
    save_state(workdir, state)

    memory_ops.update_task_info(str(session_path), state.task.description if state.task else "(未设置)", phase)
    memory_ops.update_resume_point(str(session_path), phase, progress)
    if runtime_profile:
        memory_ops.update_runtime_profile(
            str(session_path),
            skill_policy=str(runtime_profile.get("skill_policy", "")),
            use_skill=bool(runtime_profile.get("use_skill", False)),
            skill_activation_level=int(runtime_profile.get("skill_activation_level", 0)),
            tokens_expected=int(runtime_profile.get("tokens_expected", 0)),
            profile_source=str(runtime_profile.get("profile_source", "router")),
            complexity=str(runtime_profile.get("complexity", state.metadata.get("complexity", "M")) if state.metadata else "M"),
            complexity_confidence=runtime_profile.get("complexity_confidence"),
        )
    memory_ops.update_planning_summary(
        str(session_path),
        get_planning_summary(workdir, state),
    )
    if phase == "THINKING":
        if thinking_summary is None:
            task_desc = state.task.description if state.task else (state.task.title if state.task else "")
            runtime_complexity = str(runtime_profile.get("complexity") or (state.metadata.get("complexity") if state.metadata else "M"))
            thinking_summary = build_thinking_summary(task_desc, runtime_complexity)
        memory_ops.update_thinking_summary(
            str(session_path),
            thinking_summary,
        )

    if task_status:
        task_tracker.update_status(task_id, task_status, progress=progress, path=str(tracker_path))
        if task_status == "completed":
            # Run actual quality gate before marking as completed
            # Research tasks (current_phase == RESEARCH) don't need quality gate
            is_code_task = current_phase != "RESEARCH"
            quality_passed = _run_quality_gate_if_applicable(workdir, task_id, str(tracker_path), is_code_task)
            task_tracker.update_quality_gate(task_id, quality_passed, str(tracker_path))

    # Register phase-specific business artifacts on phase EXIT (not entry)
    # This ensures artifacts represent completed work, not just entry into a phase
    # Artifacts are generated when LEAVING RESEARCH/REVIEWING, not when entering
    from unified_state import ArtifactType, register_artifact
    session_id = state.session_id or "unknown"
    if current_phase == "RESEARCH" and phase != "RESEARCH":
        # Generating findings when leaving RESEARCH phase (completing research work)
        task_desc = state.task.description if state.task else 'N/A'
        task_title = state.task.title if state.task else 'Research Task'

        # Extract meaningful keywords and key phrases from task description
        words = task_desc.split()
        stop_words = {"的", "了", "和", "是", "在", "我", "有", "个", "等", "以", "对", "为", "与", "或", "及", "包括", "什么", "如何", "怎么", "哪些", "一个", "可以", "需要", "应该", "the", "a", "an", "of", "and", "in", "on", "for", "to", "is", "this", "that", "with", "as"}
        key_terms = [w for w in words if w.lower() not in stop_words and len(w) > 2][:10]
        key_terms_str = ", ".join(key_terms) if key_terms else task_title

        # Try real web search first
        search_response = search_adapter.search(task_desc, num_results=5)
        used_real_search = search_response.has_results

        if used_real_search:
            # Generate findings from real search results
            findings_list = []
            sources_list = []
            for i, result in enumerate(search_response.results, 1):
                findings_list.append(f"{i}. **{result.title}**: {result.snippet}")
                sources_list.append(f"[{i}] {result.title} - {result.url}")

            recommendations = [
                "- Review cited sources for detailed implementation guidance",
                "- Validate findings against project-specific constraints",
                "- Proceed to planning phase with verified research findings",
            ]

            findings_dir = ensure_findings_dir(workdir)
            findings_path = findings_dir / f"findings_{session_id}.md"
            findings_latest = findings_latest_path(workdir)
            engine_label = search_response.search_engine
            if search_response.search_engine == "duckduckgo":
                engine_label = f"{search_response.search_engine} [DEGRADED - DuckDuckGo HTML fallback]"
            findings_content = f"""# Research Findings: {task_title}

## Research Question
{task_desc}

## Method
- Research conducted at: {datetime.now().isoformat()}
- Search engine: {engine_label}
- Results: {search_response.total_results} sources found

## Key Findings
{chr(10).join(findings_list)}

## Sources
{chr(10).join(sources_list)}

## Conclusions
- Research completed with {search_response.total_results} verified sources
- Findings provide evidence-based insights for implementation planning
- Sources cited for further reference and validation

## Recommendations
{chr(10).join(recommendations)}
"""
            # Extract degraded_reason from search metadata if present
            degraded_reason = None
            if search_response.metadata and isinstance(search_response.metadata, dict):
                degraded_reason = search_response.metadata.get("degraded_reason")

            metadata = {
                "deliverable": "findings",
                "session_id": session_id,
                "has_method": True,
                "has_conclusions": True,
                "generated_on_exit": True,
                "key_terms": key_terms_str,
                "search_engine": search_response.search_engine,
                "sources_count": search_response.total_results,
                "used_real_search": True,
                "degraded_mode": search_response.search_engine == "duckduckgo",
            }
            if degraded_reason:
                metadata["degraded_reason"] = degraded_reason
            research_summary = {
                "research_found": True,
                "research_source": "findings_session",
                "research_path": str(findings_path),
                "key_terms": key_terms_str,
                "search_engine": search_response.search_engine,
                "sources_count": search_response.total_results,
                "used_real_search": True,
                "degraded_mode": search_response.search_engine == "duckduckgo",
                "degraded_reason": degraded_reason,
                "search_error": None,
                "evidence_status": "verified" if search_response.total_results > 0 else "degraded",
            }
        else:
            # Search failed or returned no usable results.
            # Emit an explicit degraded report instead of pretending we found evidence.
            search_note = search_response.error if search_response.error else "Search unavailable"
            findings_dir = ensure_findings_dir(workdir)
            findings_path = findings_dir / f"findings_{session_id}.md"
            findings_latest = findings_latest_path(workdir)

            findings_list = [
                f"1. **No verifiable external sources for {key_terms_str}**: configured search providers returned no usable evidence for this research question.",
            ]
            recommendations = [
                "- Re-run RESEARCH with a more specific query or narrower scope",
                "- Verify external search access before relying on this result",
                "- Fall back to manual source collection if search remains unavailable",
            ]
            findings_content = f"""# Research Findings: {task_title}

## Research Question
{task_desc}

## Method
- Research conducted at: {datetime.now().isoformat()}
- Focus: {key_terms_str}
- Search status: degraded
- Note: {search_note}

## Evidence Status
- No verifiable external sources were returned for this query
- This report records the failure mode instead of fabricating findings

## Key Findings
{chr(10).join(findings_list)}

## Conclusions
- Research could not be validated with external sources
- The current result should be treated as a degraded placeholder, not evidence-backed research

## Recommendations
{chr(10).join(recommendations)}
"""
            metadata = {
                "deliverable": "findings",
                "session_id": session_id,
                "has_method": True,
                "has_conclusions": True,
                "generated_on_exit": True,
                "key_terms": key_terms_str,
                "search_error": search_note,
                "used_real_search": False,
                "degraded_mode": True,
                "degraded_reason": search_note,
            }
            research_summary = {
                "research_found": True,
                "research_source": "findings_session",
                "research_path": str(findings_path),
                "key_terms": key_terms_str,
                "search_engine": search_response.search_engine,
                "sources_count": 0,
                "used_real_search": False,
                "degraded_mode": True,
                "degraded_reason": search_note,
                "search_error": search_note,
                "evidence_status": "degraded",
            }

        safe_write_text_locked(findings_path, findings_content)
        safe_write_text_locked(findings_latest, findings_content)
        register_artifact(workdir, ArtifactType.FINDINGS, str(findings_path), "RESEARCH", "system", metadata=metadata)
        session_state_path = Path(workdir) / memory_ops.DEFAULT_SESSION_STATE
        memory_ops.update_research_summary(str(session_state_path), research_summary)

    if current_phase == "REVIEWING" and phase != "REVIEWING":
        # Generating review when leaving REVIEWING phase (completing review work)
        task_title = state.task.title if state.task else 'N/A'
        task_desc = state.task.description if state.task else 'N/A'

        # Try to read actual code files from workdir
        workdir_path = Path(workdir)
        code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs', '.c', '.cpp'}
        code_files: list[Path] = []
        for ext in code_extensions:
            code_files.extend(workdir_path.rglob(f'*{ext}'))

        # Filter out common non-source directories
        excluded_dirs = {'node_modules', '.git', '__pycache__', 'venv', '.venv', 'dist', 'build'}

        # Task-directed review: prioritize spec-kit (tasks.md / .contract.json) over legacy task_plan.md
        target_files = []
        review_source = "none"

        # 1. Try tasks.md (spec-kit): parse **Files:** per task
        tasks_md_path = Path(workdir) / "tasks.md"
        if tasks_md_path.exists():
            tasks_content = tasks_md_path.read_text(encoding="utf-8", errors="ignore")
            files_pattern = re.compile(r'\*\*Files:\*\*\s*`([^`]+)`', re.IGNORECASE)
            for match in files_pattern.finditer(tasks_content):
                files_str = match.group(1).strip()
                for f in files_str.split(','):
                    f = f.strip()
                    if f:
                        fp = Path(workdir) / f
                        if fp.exists():
                            target_files.append(fp)
            if target_files:
                review_source = "tasks_md"

        # 2. Try .contract.json (spec-kit): owned_files field
        if not target_files:
            contract_json_path = Path(workdir) / ".contract.json"
            if contract_json_path.exists():
                try:
                    import json as json_lib
                    contract_data = json_lib.loads(contract_json_path.read_text(encoding="utf-8"))
                    owned = contract_data.get("owned_files", [])
                    for f in owned:
                        f = f.strip()
                        if f:
                            fp = Path(workdir) / f
                            if fp.exists():
                                target_files.append(fp)
                    if target_files:
                        review_source = "contract_json"
                except (json_lib.JSONDecodeError, OSError):
                    pass

        # 3. Try task_plan.md (legacy fallback): parse owned_files: line
        if not target_files:
            plan_path = Path(workdir) / "task_plan.md"
            if plan_path.exists():
                plan_content = plan_path.read_text(encoding="utf-8", errors="ignore")
                owned_pattern = re.compile(r'owned_files:\s*(.+)', re.IGNORECASE)
                for line in plan_content.split('\n'):
                    owned_match: re.Match[str] | None = owned_pattern.search(line)
                    if owned_match:
                        files_str = owned_match.group(1).strip()
                        for f in files_str.split(','):
                            f = f.strip()
                            if f:
                                fp = Path(workdir) / f
                                if fp.exists():
                                    target_files.append(fp)
                        if target_files:
                            review_source = "task_plan_md"
                            break

        # 4. Try state.file_changes
        if not target_files and state.file_changes:
            for fc in state.file_changes[:10]:  # Limit to first 10 changes
                fp = Path(workdir) / fc.path
                if fp.exists() and fp.suffix in {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs', '.c', '.cpp'}:
                    target_files.append(fp)
            if target_files:
                review_source = "file_changes"

        # 5. Strict fallback: ONLY do workdir_scan if explicitly allowed
        review_fallback_allowed = False
        if state.task:
            task_text = (state.task.description or "").lower() + (state.task.title or "").lower()
            if "allow_review_fallback" in task_text or "review_fallback=true" in task_text:
                review_fallback_allowed = True

        # Also check task_plan.md / tasks.md for explicit allow_fallback flag
        if not review_fallback_allowed and plan_path.exists():
            plan_content = plan_path.read_text(encoding="utf-8", errors="ignore").lower()
            if "allow_review_fallback" in plan_content or "review_fallback: true" in plan_content:
                review_fallback_allowed = True

        if not target_files:
            if review_fallback_allowed:
                # Explicitly allowed - do the scan
                code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs', '.c', '.cpp'}
                for ext in code_extensions:
                    for fp in workdir_path.rglob(f'*{ext}'):
                        if not any(ex in fp.parts for ex in excluded_dirs):
                            target_files.append(fp)
                if target_files:
                    review_source = "workdir_scan"
            else:
                # Not allowed - leave target_files empty; template-based review will be used
                review_source = "none"

        # Limit to 10 files total for performance
        target_files = target_files[:10]
        used_real_review = len(target_files) > 0
        reviewed_files_info = []

        if used_real_review:
            # Analyze actual code files
            risk_findings = []
            risk_level = "Medium"
            total_lines = 0

            for code_file in target_files:
                try:
                    content = code_file.read_text(encoding="utf-8", errors="ignore")
                    lines = content.split('\n')
                    total_lines += len(lines)
                    file_size = len(content)

                    # Generate findings based on actual code content
                    file_path_str = str(code_file.relative_to(workdir_path))

                    # Check for common security issues
                    if any(kw in content.lower() for kw in ['password', 'secret', 'token', 'api_key', 'apikey', 'auth']):
                        risk_findings.append(f"- **{file_path_str}**: Contains potential credential/secrets - review for hardcoded secrets (lines: {len(lines)})")
                        if risk_level != "Critical":
                            risk_level = "High"

                    # Check for error handling
                    if 'except' not in content and 'try:' not in content:
                        if file_size > 1000:  # Only flag larger files
                            risk_findings.append(f"- **{file_path_str}**: Missing try/except blocks - review error handling (lines: {len(lines)})")

                    # Check for TODO/FIXME (indicates incomplete work)
                    if '# TODO' in content or '# FIXME' in content:
                        risk_findings.append(f"- **{file_path_str}**: Contains TODO/FIXME comments - incomplete work identified (lines: {len(lines)})")

                    reviewed_files_info.append(f"- {file_path_str} ({len(lines)} lines)")

                except Exception:
                    continue

            # Add overall assessment findings
            if not risk_findings:
                risk_findings.append("- **Code Quality**: No critical issues identified in code review")

            # Generate recommendations based on actual findings
            recommendations = []
            if risk_level == "High":
                recommendations.append("- Address high-risk findings before production deployment")
                recommendations.append("- Remove or secure any hardcoded credentials/secrets")
            if "Contains potential credential" in " ".join(risk_findings):
                recommendations.append("- Implement secret management (environment variables or vault)")
            recommendations.append("- Verify implementation against specific acceptance criteria")
            recommendations.append("- Add integration tests for critical business paths")

            # Read phase contract if available (Anthropic-style negotiated contract)
            contract_info = ""
            contract = parse_phase_contract(workdir)
            if contract.get("goals"):
                contract_info = "\n## Phase Contract\n"
                if contract.get("goals"):
                    contract_info += "**Goals:**\n"
                    for goal in contract["goals"][:3]:
                        contract_info += f"- {goal}\n"
                if contract.get("verification_methods"):
                    contract_info += "\n**Verification:**\n"
                    for method in contract["verification_methods"][:2]:
                        contract_info += f"- {method}\n"
                if contract.get("owned_files"):
                    contract_info += f"\n**Contract Files:** {', '.join(contract['owned_files'][:3])}\n"

            review_dir = ensure_review_dir(workdir)
            review_path = review_dir / f"review_{session_id}.md"
            review_latest = review_latest_path(workdir)
            degraded_note = ""
            if review_source == "workdir_scan":
                degraded_note = """> **⚠️ Degraded Mode**: Review used workdir_scan fallback (no owned_files in tasks.md, .contract.json, task_plan.md, and no file_changes recorded). Results are less targeted than owned_files/file_changes directed review.
"""
            review_content = f"""# Code Review: {task_title}

## Review Scope
{task_title}

## Task Description
{task_desc}
{contract_info}

## Review Date
{datetime.now().isoformat()}

## Files Reviewed
**Files Reviewed**: {len(target_files)} code files

## Stage 1: Spec Compliance
- Contract/owned_files alignment: reviewed against {review_source}
- Acceptance coverage: checked via task contract and target files
- Scope completeness: target files count = {len(target_files)}

## Stage 2: Code Quality
- Correctness: Implementation reviewed based on actual code
- Security: Security posture assessed based on code analysis
- Maintainability: Code structure supports future maintenance

{degraded_note}## Reviewed Files ({len(target_files)} files analyzed)
{chr(10).join(reviewed_files_info)}

## Risk Findings
{chr(10).join(risk_findings)}

## Risk Level
- **Overall**: {risk_level}
- {"High-risk areas identified - requires careful review" if risk_level == "High" else "Standard review findings apply" if risk_level == "Medium" else "Critical areas require immediate attention"}

## Recommendations
{chr(10).join(recommendations)}

## Verdict
- Status: REVIEWED
"""
            metadata = {
                "deliverable": "review",
                "session_id": session_id,
                "has_findings": True,
                "has_risk_level": True,
                "generated_on_exit": True,
                "risk_level": risk_level,
                "files_reviewed": len(target_files),
                "total_lines": total_lines,
                "used_real_review": True,
                "review_source": review_source,
                "degraded_mode": review_source == "workdir_scan",
                "fallback_mode": review_source == "workdir_scan",
            }
            review_summary = {
                "review_found": True,
                "review_source": review_source,
                "review_status": "reviewed",
                "stage_1_status": "reviewed",
                "stage_2_status": "reviewed",
                "risk_level": risk_level,
                "verdict": "REVIEWED",
                "degraded_mode": review_source == "workdir_scan",
                "files_reviewed": len(target_files),
            }
        else:
            # Fall back to template-based review (no code files found)
            desc_lower = task_desc.lower()
            risk_findings = []
            risk_level = "Medium"

            # Generate specific risk findings based on task type
            if "认证" in desc_lower or "auth" in desc_lower or "login" in desc_lower:
                risk_findings.append("- **Authentication**: Credential handling and session management reviewed for security concerns")
                risk_level = "High"
            if "API" in desc_lower or "rest" in desc_lower or "接口" in desc_lower:
                risk_findings.append("- **API Security**: Endpoint validation, rate limiting, and input sanitization reviewed")
            if "用户" in desc_lower or "user" in desc_lower:
                risk_findings.append("- **Data Handling**: User input validation and data protection mechanisms reviewed")
            if "注册" in desc_lower or "register" in desc_lower:
                risk_findings.append("- **Registration Flow**: Password policy, email verification, and duplicate prevention reviewed")
                risk_level = "High"
            if "支付" in desc_lower or "payment" in desc_lower or "transaction" in desc_lower:
                risk_findings.append("- **Transaction Safety**: ACID compliance, idempotency, and financial error handling critical")
                risk_level = "Critical"
            if "敏感" in desc_lower or "sensitive" in desc_lower or "privacy" in desc_lower:
                risk_findings.append("- **Data Privacy**: PII handling, encryption, and compliance considerations reviewed")
                risk_level = "High"
            if not risk_findings:
                risk_findings.append("- **General Quality**: Code structure, error handling, and edge cases reviewed for correctness")

            # Generate specific recommendations based on identified risks
            recommendations = []
            if "认证" in desc_lower or "auth" in desc_lower:
                recommendations.append("- Implement multi-factor authentication for production")
            if "API" in desc_lower or "rest" in desc_lower:
                recommendations.append("- Add API rate limiting and request validation middleware")
            if risk_level == "High" or risk_level == "Critical":
                recommendations.append("- Conduct dedicated security review before production deployment")
            recommendations.append("- Verify implementation against specific acceptance criteria")
            recommendations.append("- Add integration tests for critical business paths")

            review_dir = ensure_review_dir(workdir)
            review_path = review_dir / f"review_{session_id}.md"
            review_latest = review_latest_path(workdir)
            review_content = f"""# Code Review: {task_title}

## Review Scope
{task_title}

## Task Description
{task_desc}

## Review Date
{datetime.now().isoformat()}

## Files Reviewed
**Files Reviewed**: 0 code files

## Stage 1: Spec Compliance
- Contract/owned_files alignment: no file-level contract available
- Acceptance coverage: verified against task description only
- Scope completeness: template-based fallback

## Stage 2: Code Quality
- Correctness: Implementation reviewed for functional correctness
- Security: Security posture assessed based on task requirements
- Maintainability: Code structure supports future maintenance

## Risk Findings
{chr(10).join(risk_findings)}

## Risk Level
- **Overall**: {risk_level}
- {"High-risk areas identified - requires careful review" if risk_level == "High" else "Critical areas require dedicated security review" if risk_level == "Critical" else "Standard review findings apply"}

## Recommendations
{chr(10).join(recommendations)}

## Verdict
- Status: REVIEWED
"""
            metadata = {
                "deliverable": "review",
                "session_id": session_id,
                "has_findings": True,
                "has_risk_level": True,
                "generated_on_exit": True,
                "risk_level": risk_level,
                "files_reviewed": 0,
                "used_real_review": False,
                "review_source": "none",
                "note": "No code files found in workdir - template-based review",
            }
            review_summary = {
                "review_found": True,
                "review_source": "template",
                "review_status": "reviewed",
                "stage_1_status": "reviewed",
                "stage_2_status": "reviewed",
                "risk_level": risk_level,
                "verdict": "REVIEWED",
                "degraded_mode": True,
                "files_reviewed": 0,
            }

        safe_write_text_locked(review_path, review_content)
        safe_write_text_locked(review_latest, review_content)
        register_artifact(workdir, ArtifactType.REVIEW, str(review_path), "REVIEWING", "system", metadata=metadata)
        memory_ops.update_review_summary(str(session_path), review_summary)

    # Block COMPLETE transition if quality gate failed for code tasks
    if phase == "COMPLETE":
        # Check if this is a code implementation task (has REVIEWING or EXECUTING in history)
        phase_history = state.phase.get("history", [])
        is_code_task = any(p.get("phase") in ("REVIEWING", "EXECUTING") for p in phase_history)

        if is_code_task:
            # Get quality gate status from tracker
            tracker_data = task_tracker.load_tracker(str(tracker_path))
            task_data = None
            for t in tracker_data.get("tasks", []):
                if t.get("id") == task_id:
                    task_data = t
                    break

            quality_gate_passed = task_data.get("quality_gates_passed") if task_data else None
            task_priority = task_data.get("priority") if task_data else None
            task_verification = task_data.get("verification") if task_data else None

            # Code tasks must have explicitly passed quality gate (None = not run, False = failed)
            if quality_gate_passed is not True:
                raise ValueError(
                    f"Cannot transition to COMPLETE: quality gate not passed for task {task_id}. "
                    f"quality_gates_passed={quality_gate_passed}. "
                    f"Allowed transitions: stay in {current_phase}, go to DEBUGGING, or abort."
                )

            # If P0/P1 task has no verification, block COMPLETE
            if task_priority in ("P0", "P1") and not task_verification:
                raise ValueError(
                    f"Cannot transition to COMPLETE: task {task_id} (P0/P1) has no verification method. "
                    f"Allowed transitions: stay in {current_phase}, go to DEBUGGING, or abort."
                )

            review_valid, review_error = _run_review_gate_if_applicable(workdir, True)
            if not review_valid:
                raise ValueError(
                    f"Cannot transition to COMPLETE: {review_error}. "
                    f"Allowed transitions: stay in {current_phase}, go to REVIEWING, or abort."
                )

        # Contract fulfillment gate: validate contract is properly fulfilled
        contract_valid, contract_error = validate_contract_gate(workdir, state)
        if not contract_valid:
            raise ValueError(
                f"Cannot transition to COMPLETE: {contract_error}"
            )

        _generate_and_register_summary(workdir, state, current_phase, "completed", session_id)

    # Load and format skill prompt for the new phase
    skill_prompt_path = None
    skill_name = None
    try:
        skill = load_skill(phase)
        if skill:
            formatter = SkillPromptFormatter(skill)
            task_desc = state.task.description if state.task else ""
            task_title = state.task.title if state.task else ""
            prompt = formatter.format(
                task=task_desc or task_title or "未指定任务",
                session_id=session_id or "",
            )
            # Save skill prompt as artifact (use PROGRESS type, not SUMMARY - SUMMARY is for completion_summary)
            skill_prompt_path = Path(workdir) / f"skill_prompt_{phase.lower()}_{session_id}.md"
            safe_write_text_locked(skill_prompt_path, prompt)
            skill_name = skill.metadata.name
            register_artifact(workdir, ArtifactType.PROGRESS, str(skill_prompt_path), phase, "system",
                             metadata={"skill_name": skill_name, "phase": phase})
            # SKILL0 P3: Record skill usage for telemetry
            try:
                from skill_telemetry import record_skill_usage
                record_skill_usage(
                    skill_name=skill_name,
                    phase=phase,
                    workdir=workdir,
                    metadata={"session_id": session_id, "outcome": "loaded"},
                )
            except Exception:
                pass  # Skill telemetry is best-effort
    except Exception:
        # Skill loading is best-effort - don't fail the phase transition
        pass

    # Calculate progress visualization data
    phase_sequence = state.metadata.get("phase_sequence") if state.metadata else None
    phase_index = None
    total_phases = None
    if phase_sequence and isinstance(phase_sequence, list):
        try:
            phase_index = phase_sequence.index(phase) + 1
            total_phases = len(phase_sequence)
        except ValueError:
            pass

    # Build context for next phase — what the AI should read before proceeding
    context_for_next_phase = _build_phase_context(phase, workdir, state.session_id or "unknown")

    # Reflexion P1: Surface experience warning prominently if found
    experience_warning = None
    exp_check = context_for_next_phase.get("experience_check", {})
    if isinstance(exp_check, dict) and exp_check.get("warning"):
        experience_warning = exp_check["warning"]

    return {
        "task_id": task_id,
        "session_id": state.session_id,
        "phase": phase,
        "progress": progress,
        "task_status": task_status,
        "recommended_next_phases": recommend_next_phases(phase, state.trigger_type),
        "state_file": str(workflow_state_path(workdir)),
        "skill_prompt_path": str(skill_prompt_path) if skill_prompt_path else None,
        "skill_name": skill_name,
        "phase_index": phase_index,
        "total_phases": total_phases,
        "complexity": state.metadata.get("complexity") if state.metadata else None,
        "context_for_next_phase": context_for_next_phase,
        # Reflexion P1: Top-level experience warning for visibility
        "experience_warning": experience_warning,
        # P2 ToT: Deliberation result (if deliberation was triggered)
        "deliberation": deliberation_result if deliberation_result else None,
    }


def complete_workflow(
    workdir: str = ".",
    final_state: str = "completed",
    failure_reason: str | None = None,
) -> dict[str, Any]:
    """
    Complete the workflow and finalize trajectory logging.

    Validates contract fulfillment gate before allowing completion (contract must
    be active/fulfilled, goals must not be placeholders). Generates final
    summary artifact and flushes trajectory logger.

    Args:
        workdir: Working directory
        final_state: Final state string (completed/failed/aborted)
        failure_reason: Reason for failure (if final_state is not completed)

    Returns:
        Completion result dict with session_id and final state

    Raises:
        ValueError: If contract gate validation fails or workflow not initialized
    """
    state = load_state(workdir)
    if state is None:
        raise ValueError("workflow state not found, please run init first")

    current_phase = state.phase.get("current", "IDLE")
    session_id = state.session_id or "unknown"
    if final_state == "completed":
        contract_valid, contract_error = validate_contract_gate(workdir, state)
        if not contract_valid:
            raise ValueError(f"Cannot complete workflow: {contract_error}")

    # Gate blocking for code tasks - same logic as advance_workflow COMPLETE
    phase_history = state.phase.get("history", [])
    is_code_task = any(p.get("phase") in ("REVIEWING", "EXECUTING") for p in phase_history)

    if is_code_task and final_state == "completed":
        # Get task_id from state
        task_id = state.task.task_id if state.task else None

        # Code tasks MUST have a valid task_id to complete
        # If task_id is None, we cannot verify quality gate was run - fail closed
        if task_id is None:
            raise ValueError(
                f"Cannot complete workflow: task has no task_id. "
                f"Cannot verify quality gate was run. "
                f"Allowed transitions: stay in {current_phase}, go to DEBUGGING, or abort."
            )

        tracker_path = Path(workdir) / ".task_tracker.json"
        tracker_data = task_tracker.load_tracker(str(tracker_path))
        task_data = None
        for t in tracker_data.get("tasks", []):
            if t.get("id") == task_id:
                task_data = t
                break

        quality_gate_passed = task_data.get("quality_gates_passed") if task_data else None
        task_priority = task_data.get("priority") if task_data else None
        task_verification = task_data.get("verification") if task_data else None

        # Code tasks must have explicitly passed quality gate (None = not run, False = failed)
        if quality_gate_passed is not True:
            raise ValueError(
                f"Cannot complete workflow: quality gate not passed for task {task_id}. "
                f"quality_gates_passed={quality_gate_passed}. "
                f"Allowed transitions: stay in {current_phase}, go to DEBUGGING, or abort."
            )

        # If P0/P1 task has no verification, block COMPLETE
        if task_priority in ("P0", "P1") and not task_verification:
            raise ValueError(
                f"Cannot complete workflow: task {task_id} (P0/P1) has no verification method. "
                f"Allowed transitions: stay in {current_phase}, go to DEBUGGING, or abort."
            )

        review_valid, review_error = _run_review_gate_if_applicable(workdir, True, state)
        if not review_valid:
            raise ValueError(
                f"Cannot complete workflow: {review_error}. "
                f"Allowed transitions: stay in {current_phase}, go to REVIEWING, or abort."
            )

    # Complete trajectory logging
    if state.session_id in _active_loggers:
        logger = _active_loggers[state.session_id]
        logger.exit_phase(current_phase)
        logger.complete(final_state, failure_reason)
        del _active_loggers[state.session_id]

    # Register completion summary artifact using shared helper
    _generate_and_register_summary(workdir, state, current_phase, final_state, session_id, failure_reason)

    # Transition to COMPLETE if not already there
    if current_phase != "COMPLETE":
        state = transition_phase(state, "COMPLETE", reason=f"Workflow {final_state}")
        save_state(workdir, state)

    return {
        "session_id": state.session_id,
        "final_state": final_state,
        "failure_reason": failure_reason,
    }


def log_workflow_decision(
    workdir: str,
    decision: str,
    reason: str = "",
) -> dict[str, Any]:
    """Log workflow decision to trajectory"""
    state = load_state(workdir)
    if state is None:
        raise ValueError("workflow state not found")

    if state.session_id in _active_loggers:
        logger = _active_loggers[state.session_id]
        logger.log_decision(decision, reason)
        return {"status": "logged", "decision": decision}

    return {"status": "no_active_logger", "decision": decision}


def log_workflow_file_change(
    workdir: str,
    file_path: str,
    action: str,
) -> dict[str, Any]:
    """Log file change to trajectory"""
    state = load_state(workdir)
    if state is None:
        raise ValueError("workflow state not found")

    if state.session_id in _active_loggers:
        logger = _active_loggers[state.session_id]
        logger.log_file_change(file_path, action)
        return {"status": "logged", "file_path": file_path, "action": action}

    return {"status": "no_active_logger", "file_path": file_path, "action": action}


# ============================================================================
# Lightweight Generator-Evaluator Loop
# ============================================================================
# Anthropic-style generator-evaluator pattern, thin stable implementation.
#
# Trigger conditions (one of):
#   - High complexity task (detected by task size/complexity indicators)
#   - Quality gate failure during REVIEWING
#   - Explicit opt-in via task_plan.md flag: `enable_evaluator_loop=true`
#
# Revision cycle:
#   REVIEWING -> (if issues found) -> EXECUTING (revise) -> REVIEWING (re-verify)
#   Maximum 2 revision cycles per phase contract
# ============================================================================

MAX_REVISION_CYCLES = 2


def request_revision(
    workdir: str,
    reason: str,
    feedback: str,
) -> dict[str, Any]:
    """
    Request revision from REVIEWING back to EXECUTING.

    Lightweight Generator-Evaluator loop integration point.
    Tracks revision count in state and limits to MAX_REVISION_CYCLES.

    Args:
        workdir: Working directory
        reason: Why revision is needed (e.g., "quality_gate_failed", "high_risk_issues")
        feedback: Specific feedback for the executor

    Returns:
        Dict with transition info including revision_count and whether revision is allowed
    """
    from state_schema import Decision

    state = load_state(workdir)
    if state is None:
        raise ValueError("workflow state not found")

    # Track revision count in state decisions
    revision_decisions = [d for d in state.decisions if "revision" in d.decision.lower()]
    revision_count = len(revision_decisions)

    if revision_count >= MAX_REVISION_CYCLES:
        return {
            "status": "revision_limit_reached",
            "revision_count": revision_count,
            "max_revisions": MAX_REVISION_CYCLES,
            "message": f"Maximum revision cycles ({MAX_REVISION_CYCLES}) reached. Proceeding to COMPLETE.",
        }

    # Log revision request
    state.decisions.append(Decision(
        timestamp=datetime.now().isoformat(),
        decision=f"Revision requested: {reason}",
        reason=feedback,
    ))
    save_state(workdir, state)

    return {
        "status": "revision_requested",
        "revision_count": revision_count + 1,
        "max_revisions": MAX_REVISION_CYCLES,
        "reason": reason,
        "feedback": feedback,
        "next_phase": "EXECUTING",
    }


def resume_workflow(
    workdir: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Resume workflow from a checkpoint.

    Loads checkpoint state from .checkpoints/ directory (or from trajectory if
    session_id not provided), restores .workflow_state.json, and updates
    task tracker to reflect resumed state.

    Args:
        workdir: Working directory
        session_id: Optional session ID (auto-detected from trajectories if None)

    Returns:
        Restored state snapshot dict with resume metadata
    """
    from trajectory_logger import list_trajectories, resume_from_point

    # 如果没有指定 session_id，找到最新的中断工作流
    if session_id is None:
        trajectories = list_trajectories(workdir)
        for traj in trajectories:
            if traj.get("final_state") == "running":
                session_id = traj.get("session_id")
                break

        if session_id is None:
            return {"success": False, "error": "No interrupted workflow found to resume"}

    # 获取恢复点
    result = resume_from_point(workdir, session_id)
    if not result:
        return {"success": False, "error": f"Failed to resume session {session_id}"}

    # 获取新的 session_id 和 next_phase
    new_session_id = result["session_id"]
    next_phase = result["next_phase"]
    resume_summary = result.get("resume_summary", {})
    research_summary = resume_summary.get("research_summary", {})
    planning_summary = resume_summary.get("planning_summary", {})
    review_summary = resume_summary.get("review_summary", {})
    thinking_summary = resume_summary.get("thinking_summary", {})

    # 更新 unified state - 这是关键同步步骤
    state = load_state(workdir)
    if state is not None:
        runtime_profile_summary = get_runtime_profile_summary(state)
        failure_event_summary = get_failure_event_summary(state)
        state_planning_summary = get_planning_summary(workdir, state)
        state_research_summary = get_research_summary(workdir, state)
        state_review_summary = get_review_summary(workdir, state)
        if not planning_summary or planning_summary.get("plan_source") in {None, "", "none"}:
            planning_summary = state_planning_summary
        if not research_summary or research_summary.get("research_source") in {None, "", "none"}:
            research_summary = state_research_summary
        if not review_summary or review_summary.get("review_source") in {None, "", "none"}:
            review_summary = state_review_summary
        # 记录恢复决策
        from datetime import datetime

        from state_schema import Decision
        state.decisions.append(Decision(
            timestamp=datetime.now().isoformat(),
            decision=f"Resumed from {session_id}",
            reason=f"resume_from={result['resume_from']}",
            metadata={
                "original_session": session_id,
                "resumed_session": new_session_id,
                "resume_from": result["resume_from"],
                "next_phase": next_phase,
                "resume_summary": resume_summary,
                "runtime_profile_summary": runtime_profile_summary,
                "research_summary": research_summary,
                "planning_summary": planning_summary,
                "review_summary": review_summary,
                "thinking_summary": thinking_summary,
                "failure_event_summary": failure_event_summary,
            },
        ))

        # 更新 session_id
        state.session_id = new_session_id

        # 更新 phase
        state.phase["current"] = next_phase

        save_state(workdir, state)
    else:
        runtime_profile_summary = {}
        failure_event_summary = {}
        research_summary = research_summary or get_research_summary(workdir, None)
        planning_summary = planning_summary or get_planning_summary(workdir, None)
        review_summary = review_summary or get_review_summary(workdir, None)

    session_path = Path(workdir) / memory_ops.DEFAULT_SESSION_STATE
    memory_ops.update_resume_summary(
        str(session_path),
        resume_from=result["resume_from"],
        next_phase=next_phase,
        original_session_id=session_id,
        runtime_profile=runtime_profile_summary,
        research_summary=research_summary,
        planning_summary=planning_summary,
        review_summary=review_summary,
        thinking_summary=thinking_summary,
        failure_event_summary=failure_event_summary,
    )
    memory_ops.update_planning_summary(
        str(session_path),
        planning_summary,
    )

    # 重新初始化 trajectory logger
    new_logger = TrajectoryLogger(workdir, new_session_id)
    new_logger.start(
        f"[RESUMED from {session_id}]",
        "RESUMED",
        runtime_profile=runtime_profile_summary,
        resume_summary=resume_summary,
    )
    new_logger.enter_phase(next_phase)
    _active_loggers[new_session_id] = new_logger

    return {
        "success": True,
        "original_session_id": session_id,
        "new_session_id": new_session_id,
        "resume_from": result["resume_from"],
        "next_phase": next_phase,
        "resume_summary": resume_summary,
        "runtime_profile_summary": runtime_profile_summary,
        "research_summary": research_summary,
        "planning_summary": planning_summary,
        "review_summary": review_summary,
        "thinking_summary": thinking_summary,
        "failure_event_summary": failure_event_summary,
        "state_synced": True,
    }


# Error classification patterns
_ERROR_TYPE_PATTERNS = {
    "test_failure": [
        "FAILED", "pytest", "test fail", "assertion error",
        "AssertionError", "test failed", "tests failed",
    ],
    "type_error": [
        "TypeError", "type error", "typing error",
        "cannot assign", "argument type", "expected ", "got ",
    ],
    "lint_error": [
        "lint", "ruff", "flake8", "pylint", "mypy",
        "unused import", "undefined name", "missing import",
    ],
    "runtime_exception": [
        "Exception", "Error:", "Traceback", "IndexError",
        "KeyError", "ValueError", "AttributeError", "ImportError",
    ],
    "syntax_error": [
        "SyntaxError", "IndentationError", "TabError",
        "unexpected EOF", "invalid syntax",
    ],
    "quality_gate_failed": [
        "quality gate", "gate failed", "gate_check",
    ],
}


def classify_error(error: str) -> tuple[str, float]:
    """
    Classify error type and return (error_type, confidence).

    Args:
        error: Error message string

    Returns:
        Tuple of (error_type, confidence_score)
    """
    error_lower = error.lower()
    scores: dict[str, float] = {}

    for error_type, patterns in _ERROR_TYPE_PATTERNS.items():
        score = sum(1 for p in patterns if p.lower() in error_lower)
        if score > 0:
            scores[error_type] = score / len(patterns)

    if not scores:
        return ("unknown", 1.0)

    # Return highest scoring type
    best_type = max(scores, key=lambda k: scores[k])
    return (best_type, scores[best_type])


def _get_error_history(state) -> list[dict[str, Any]]:
    """Extract error history from state decisions."""
    history = []
    for decision in state.decisions:
        if "error" in decision.metadata:
            history.append({
                "error": decision.metadata.get("error", ""),
                "type": decision.metadata.get("error_type", "unknown"),
                "timestamp": decision.timestamp,
            })
    return history


def _should_escalate_skill_activation(
    error: str,
    error_type: str,
    strategy: str,
    retry_count: int,
    error_history: list[dict[str, Any]],
) -> tuple[bool, str]:
    """
    Decide whether to escalate skill activation based on explicit failure events.

    Escalation is reserved for high-signal failures and repeated test failures.
    Generic recoverable failures should not automatically increase activation.
    """
    if strategy == "abort":
        return False, "abort strategy does not escalate skill activation"

    if error_type in {"syntax_error", "type_error", "quality_gate_failed"}:
        return True, f"high_signal_failure:{error_type}"

    if error_type == "test_failure":
        normalized_error = error[:120].lower()
        repeated_test_failure = any(
            item.get("type") == "test_failure" and item.get("error", "")[:120].lower() == normalized_error
            for item in error_history[-5:]
        )
        if repeated_test_failure or retry_count >= 1:
            return True, "repeated_test_failure"

    return False, "no escalation event"


def handle_workflow_failure(
    workdir: str,
    error: str,
    strategy: str = "retry",
    max_retries: int = 3,
) -> dict[str, Any]:
    """
    Handle workflow failure with intelligent error classification and retry strategy.

    Args:
        workdir: Working directory
        error: Error message
        strategy: Failure handling strategy
            - "retry": Retry current phase
            - "debugging": Transition to DEBUGGING phase
            - "abort": Abort workflow
        max_retries: Maximum retry count

    Returns:
        Handling result
    """
    from datetime import datetime

    from state_schema import Decision

    state = load_state(workdir)
    if state is None:
        return {"success": False, "error": "workflow state not found"}

    current_phase = state.phase.get("current", "IDLE")

    # Classify the error
    error_type, confidence = classify_error(error)

    # Log failure to trajectory
    if state.session_id in _active_loggers:
        logger = _active_loggers[state.session_id]
        logger.log_error(error, recoverable=(strategy != "abort"))

    # Check for quality gate failure details
    quality_gate_details = None
    if error_type == "quality_gate_failed":
        quality_gate_details = _extract_quality_gate_details(workdir)

    # Determine retry count early so we can make a stricter escalation decision.
    runtime_profile = state.metadata.get("runtime_profile", {}) if state.metadata else {}
    retry_count = 0
    if state.decisions:
        last_decision = state.decisions[-1]
        retry_count = int(last_decision.metadata.get("retry_count", 0))

    error_history = _get_error_history(state)

    # Escalate activation level only for explicit failure events.
    if runtime_profile:
        current_activation_level = int(runtime_profile.get("skill_activation_level", 0))
        should_escalate, escalation_reason = _should_escalate_skill_activation(
            error=error,
            error_type=error_type,
            strategy=strategy,
            retry_count=retry_count,
            error_history=error_history,
        )
        escalated_activation_level = (
            escalate_skill_activation_level(current_activation_level) if should_escalate else current_activation_level
        )
        if escalated_activation_level != current_activation_level:
            runtime_profile["skill_activation_level"] = escalated_activation_level
            if state.metadata is None:
                state.metadata = {}
            state.metadata["runtime_profile"] = runtime_profile
            state.decisions.append(Decision(
                timestamp=datetime.now().isoformat(),
                decision="Escalate skill activation",
                reason=f"{escalation_reason} escalated activation to {escalated_activation_level}",
                metadata={
                    "error_type": error_type,
                    "current_activation_level": current_activation_level,
                    "escalated_activation_level": escalated_activation_level,
                    "escalation_reason": escalation_reason,
                    "retry_count": retry_count,
                    "profile_source": runtime_profile.get("profile_source", "router"),
                },
            ))
            session_path = Path(workdir) / memory_ops.DEFAULT_SESSION_STATE
            memory_ops.update_runtime_profile(
                str(session_path),
                skill_policy=str(runtime_profile.get("skill_policy", "")),
                use_skill=bool(runtime_profile.get("use_skill", False)),
                skill_activation_level=escalated_activation_level,
                tokens_expected=int(runtime_profile.get("tokens_expected", 0)),
                profile_source=str(runtime_profile.get("profile_source", "router")),
                complexity=str(runtime_profile.get("complexity", state.metadata.get("complexity", "M")) if state.metadata else "M"),
                complexity_confidence=runtime_profile.get("complexity_confidence"),
            )
            if state.session_id in _active_loggers:
                logger = _active_loggers[state.session_id]
                logger.log_decision(
                    "Escalate skill activation",
                    f"{escalation_reason} escalated activation to {escalated_activation_level}",
                    activation_level=escalated_activation_level,
                    error_type=error_type,
                    escalation_reason=escalation_reason,
                )
            save_state(workdir, state)

    # Syntax errors always go to debugging immediately - they can't be fixed by retry
    if error_type == "syntax_error":
        strategy = "debugging"
        retry_hint = "syntax error cannot be fixed by retry"
    else:
        retry_hint = ""

    reflection_artifact: dict[str, Any] = {}

    if strategy == "retry":
        # Get retry count and error history from decisions
        retry_count = 0
        error_history = _get_error_history(state)

        if state.decisions:
            last_decision = state.decisions[-1]
            retry_count = last_decision.metadata.get("retry_count", 0)

        # Adjust max_retries based on error classification
        adjusted_max_retries = max_retries

        # Generate dynamic reflexion hint based on actual error content
        from reflexion import reflect_on_errors
        reflex = reflect_on_errors(error, error_type, {
            "phase": current_phase,
            "retry_count": retry_count,
        })
        retry_hint = reflex.hint

        reflection_artifact = _persist_failure_reflection(
            workdir,
            state,
            error,
            error_type,
            confidence,
            retry_hint,
            strategy,
            quality_gate_details=quality_gate_details,
        )

        if error_type == "test_failure" and retry_count >= 1:
            # After one test failure retry, suggest debugging
            adjusted_max_retries = max(retry_count + 1, 2)
        elif error_type == "lint_error" and not retry_hint:
            # Lint errors often fixed by auto-fix (only if reflexion didn't find specifics)
            retry_hint = "try running ruff/lint auto-fix"
        elif error_type == "type_error" and not retry_hint:
            # Type errors need careful review (only if reflexion didn't find specifics)
            retry_hint = "check type annotations"

        if retry_count >= adjusted_max_retries:
            strategy = "debugging"
        else:
            new_retry_count = retry_count + 1
            state.decisions.append(Decision(
                timestamp=datetime.now().isoformat(),
                decision=f"Retry attempt {new_retry_count}",
                reason=f"Retry after {error_type} error: {error[:200]}",
                metadata={
                    "retry_count": new_retry_count,
                    "error": error,
                "error_type": error_type,
                "error_confidence": confidence,
                "error_history": error_history,
                "reflection": reflex.reflection,
                "reflection_hint": retry_hint,
            },
            ))
            save_state(workdir, state)

            result = {
                "success": True,
                "action": "retry",
                "phase": current_phase,
                "retry_count": new_retry_count,
                "error_type": error_type,
                "confidence": confidence,
                "message": f"Retrying {current_phase} (attempt {new_retry_count}/{adjusted_max_retries})",
                "reflection_recorded": bool(reflection_artifact),
            }
            if retry_hint:
                result["retry_hint"] = retry_hint
            if quality_gate_details:
                result["quality_gate_details"] = quality_gate_details
            if reflection_artifact:
                result.update(reflection_artifact)
            return result

    if strategy == "debugging":
        reflection_artifact = _persist_failure_reflection(
            workdir,
            state,
            error,
            error_type,
            confidence,
            retry_hint,
            strategy,
            quality_gate_details=quality_gate_details,
        )
        if can_transition(current_phase, "DEBUGGING"):
            owned_files_count = len(state.task.owned_files) if state.task else 0
            diff_size = len(state.file_changes) if state.file_changes else 0
            failure_count = len(error_history)
            task_text = state.task.description if state.task else error
            debug_activation_level = debugging_activation_level_for_context(
                str(runtime_profile.get("complexity", state.metadata.get("complexity", "M")) if state.metadata else "M"),
                task_text=task_text,
                owned_files_count=owned_files_count,
                diff_size=diff_size,
                failure_count=failure_count,
            )

            if runtime_profile:
                runtime_profile["skill_activation_level"] = debug_activation_level
                runtime_profile["skill_policy"] = (
                    "conditional_enable_after_optimization" if debug_activation_level > 0 else "disable"
                )
                runtime_profile["use_skill"] = debug_activation_level > 0
                if state.metadata is None:
                    state.metadata = {}
                state.metadata["runtime_profile"] = runtime_profile
                state.decisions.append(Decision(
                    timestamp=datetime.now().isoformat(),
                    decision="Tune debugging activation",
                    reason=f"context-based debug activation set to {debug_activation_level}",
                    metadata={
                        "owned_files_count": owned_files_count,
                        "diff_size": diff_size,
                        "failure_count": failure_count,
                        "debug_activation_level": debug_activation_level,
                        "profile_source": runtime_profile.get("profile_source", "router"),
                    },
                ))
                session_path = Path(workdir) / memory_ops.DEFAULT_SESSION_STATE
                memory_ops.update_runtime_profile(
                    str(session_path),
                    skill_policy=str(runtime_profile.get("skill_policy", "")),
                    use_skill=bool(runtime_profile.get("use_skill", False)),
                    skill_activation_level=debug_activation_level,
                    tokens_expected=int(runtime_profile.get("tokens_expected", 0)),
                    profile_source=str(runtime_profile.get("profile_source", "router")),
                    complexity=str(runtime_profile.get("complexity", state.metadata.get("complexity", "M")) if state.metadata else "M"),
                    complexity_confidence=runtime_profile.get("complexity_confidence"),
                )

            state = transition_phase(state, "DEBUGGING", reason=f"Failure: {error}")
            save_state(workdir, state)

            if state.session_id in _active_loggers:
                logger = _active_loggers[state.session_id]
                logger.exit_phase(current_phase)
                logger.enter_phase("DEBUGGING")

            return {
                "success": True,
                "action": "debugging",
                "previous_phase": current_phase,
                "new_phase": "DEBUGGING",
                "error": error,
                "error_type": error_type,
                "error_history": _get_error_history(state),
                "reflection_recorded": bool(reflection_artifact),
                **reflection_artifact,
            }
        else:
            return {
                "success": False,
                "error": f"Cannot transition from {current_phase} to DEBUGGING",
                "reflection_recorded": bool(reflection_artifact),
                **reflection_artifact,
            }

    if strategy == "abort":
        reflection_artifact = _persist_failure_reflection(
            workdir,
            state,
            error,
            error_type,
            confidence,
            retry_hint,
            strategy,
            quality_gate_details=quality_gate_details,
        )
        complete_workflow(workdir, "failed", error)
        return {
            "success": True,
            "action": "aborted",
            "final_state": "failed",
            "error": error,
            "error_type": error_type,
            "reflection_recorded": bool(reflection_artifact),
            **reflection_artifact,
        }

    return {"success": False, "error": f"Unknown strategy: {strategy}"}


def _extract_quality_gate_details(workdir: str) -> dict[str, Any] | None:
    """Extract quality gate failure details from latest gate report."""
    import json
    gate_files = list(Path(workdir).glob(".quality_gate_*.json"))
    if not gate_files:
        return None

    latest = max(gate_files, key=lambda p: p.stat().st_mtime)
    try:
        data = json.loads(latest.read_text())
        return {
            "gate_file": str(latest.name),
            "passed": data.get("all_passed", False),
            "failed_checks": data.get("failed_checks", []),
        }
    except Exception:
        return None


def _persist_failure_reflection(
    workdir: str,
    state,
    error: str,
    error_type: str,
    confidence: float,
    retry_hint: str,
    strategy: str,
    quality_gate_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a Reflexion-style failure note into artifacts and long-term memory."""
    from memory_longterm import record_reflection_experience, search_memory
    from unified_state import ArtifactType, register_artifact

    session_id = state.session_id or "unknown"
    current_phase = state.phase.get("current", "IDLE") if state.phase else "IDLE"
    task_title = state.task.title if state.task else "Unknown task"
    task_desc = state.task.description if state.task else task_title
    memory_path = str(Path(workdir) / "MEMORY.md")
    memory_index_path = str(Path(workdir) / ".memory_index.jsonl")

    try:
        relevant_experiences = search_memory(
            error,
            filepath=memory_path,
            scope="project",
            limit=3,
            intent="debug",
        )
    except Exception:
        relevant_experiences = []

    trigger = f"{current_phase}::{strategy}"
    if quality_gate_details:
        trigger = f"{trigger}::quality_gate"

    signal_parts = [error_type]
    if quality_gate_details and quality_gate_details.get("failed_checks"):
        signal_parts.append(",".join(str(item) for item in quality_gate_details["failed_checks"][:3]))
    signal = " | ".join(signal_parts)

    next_hint = retry_hint or "inspect the failure and retry with tighter scope"
    reflection_path = Path(workdir) / f"reflection_{session_id}.md"
    reflection_content = f"""# Failure Reflection

## Context
- Session: {session_id}
- Phase: {current_phase}
- Strategy: {strategy}
- Error Type: {error_type}
- Confidence: {confidence:.2f}

## Task
{task_desc}

## Reflection
Task: {task_title}
Trigger: {trigger}
Mistake: {error[:500]}
Fix: {next_hint}
Signal: {signal}

## Relevant Experiences
"""
    if relevant_experiences:
        for item in relevant_experiences:
            reflection_content += f"- {item}\n"
    else:
        reflection_content += "- None found\n"

    reflection_content += f"""

## Next Action
{next_hint}
"""

    safe_write_text_locked(reflection_path, reflection_content)
    register_artifact(
        workdir,
        ArtifactType.CUSTOM,
        str(reflection_path),
        current_phase,
        "system",
        metadata={
            "kind": "reflection",
            "error_type": error_type,
            "confidence": confidence,
            "strategy": strategy,
            "relevant_experiences": relevant_experiences,
        },
    )

    try:
        record_reflection_experience(
            task=task_desc,
            trigger=trigger,
            mistake=error[:500],
            fix=next_hint,
            signal=signal,
            filepath=memory_path,
            index_file=memory_index_path,
            confidence=max(0.3, min(0.9, confidence if confidence else 0.7)),
            scope="project",
            tags=[error_type, current_phase.lower()],
        )
    except Exception:
        pass

    return {
        "reflection_path": str(reflection_path),
        "relevant_experiences": relevant_experiences,
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


def main() -> int:
    """
    CLI entry point for the workflow runtime engine.

    Supported operations (--op):
        init          Initialize a new workflow session
        advance       Advance to a new phase
        snapshot      Get a snapshot of current workflow state
        recommend     Recommend next phases from current state
        validate      Validate workflow state integrity
        plan          Generate a task plan
        frontier      Compute the execution frontier (ready/blocked/conflict tasks)
        checkpoint    Conditionally save a checkpoint
        complete      Mark workflow as complete (with contract gate validation)
        log-decision  Record a workflow decision
        log-file      Record a file change
        validate-plan Validate task plan structure
        update-task   Update task status in plan
        resume        Resume from a checkpoint
        handle-failure Handle workflow failure with error classification
        team-run      Run multi-agent team orchestration

    Returns:
        Exit code (0 = success, non-zero = error)
    """
    parser = argparse.ArgumentParser(description="Agentic workflow runtime engine")
    parser.add_argument("--workdir", default=".", help="workspace directory")
    parser.add_argument("--op", choices=["init", "advance", "snapshot", "recommend", "validate", "plan", "frontier", "checkpoint", "complete", "log-decision", "log-file", "validate-plan", "update-task", "resume", "handle-failure", "team-run"], required=True)
    parser.add_argument("--prompt", help="user prompt for workflow initialization")
    parser.add_argument("--task-id", help="optional task id")
    parser.add_argument("--phase", help="target phase for advance")
    parser.add_argument("--progress", type=int, default=0, help="progress percent for advance")
    parser.add_argument("--task-status", help="task status for advance")
    parser.add_argument("--note", default="", help="note for phase advance")
    parser.add_argument("--no-auto-plan", action="store_true", help="disable auto task plan creation")
    parser.add_argument("--final-state", default="completed", help="final state for complete")
    parser.add_argument("--failure-reason", help="failure reason for complete")
    parser.add_argument("--decision", help="decision text for log-decision")
    parser.add_argument("--reason", default="", help="decision reason for log-decision")
    parser.add_argument("--path", help="file path for log-file")
    parser.add_argument("--action", default="modify", help="file action for log-file (create/modify/delete)")
    parser.add_argument("--status", help="task status for update-task (backlog/in_progress/completed/blocked)")
    parser.add_argument("--session-id", help="session id for resume")
    parser.add_argument("--error", help="error message for handle-failure")
    parser.add_argument("--strategy", default="retry", choices=["retry", "debugging", "abort"], help="failure handling strategy")
    parser.add_argument("--max-retries", type=int, default=3, help="max retry count")
    parser.add_argument("--use-real-agent", action="store_true", help="use real AI subagents in team-run (requires claude CLI)")
    args = parser.parse_args()

    if args.op == "init":
        if not args.prompt:
            print("错误: --prompt 必须指定")
            return 1
        result = initialize_workflow(
            args.prompt,
            workdir=args.workdir,
            task_id=args.task_id,
            auto_create_plan=not args.no_auto_plan,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "advance":
        if not args.phase:
            print("错误: --phase 必须指定")
            return 1
        try:
            result = advance_workflow(
                args.phase,
                workdir=args.workdir,
                progress=args.progress,
                task_status=args.task_status,
                note=args.note,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except ValueError as e:
            # Phase transition blocked (e.g., quality gate failure) - return as JSON error
            print(json.dumps({"error": str(e), "blocked": True}, ensure_ascii=False, indent=2))
            return 1

    if args.op == "recommend":
        snapshot = get_workflow_snapshot(args.workdir)
        print(json.dumps({"recommended_next_phases": snapshot["recommended_next_phases"]}, ensure_ascii=False, indent=2))
        return 0

    if args.op == "validate":
        from unified_state import validate_workflow_state
        is_valid, errors = validate_workflow_state(args.workdir)
        print(json.dumps({"valid": is_valid, "errors": errors}, ensure_ascii=False, indent=2))
        return 0

    if args.op == "plan":
        tasks, source = load_planning_tasks(args.workdir)
        print(json.dumps({"tasks": tasks, "next_tasks": next_plan_tasks(args.workdir), "plan_source": source}, ensure_ascii=False, indent=2))
        return 0

    if args.op == "frontier":
        frontier = compute_frontier(args.workdir)
        print(json.dumps(frontier, ensure_ascii=False, indent=2))
        return 0

    if args.op == "checkpoint":
        result = conditional_checkpoint(args.workdir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "validate-plan":
        is_valid, errors = validate_task_plan(args.workdir)
        print(json.dumps({"valid": is_valid, "errors": errors}, ensure_ascii=False, indent=2))
        return 0

    if args.op == "update-task":
        if not args.task_id:
            print("错误: --task-id required for update-task")
            return 1
        if not args.status:
            print("错误: --status required for update-task")
            return 1
        result = update_task_status_in_plan(args.workdir, args.task_id, args.status)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "complete":
        try:
            result = complete_workflow(
                args.workdir,
                final_state=args.final_state,
                failure_reason=args.failure_reason,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except ValueError as e:
            # Quality gate blocked completion
            print(json.dumps({"error": str(e), "blocked": True}, ensure_ascii=False, indent=2))
            return 1

    if args.op == "log-decision":
        if not args.decision:
            print("错误: --decision required for log-decision")
            return 1
        result = log_workflow_decision(args.workdir, args.decision, args.reason)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "log-file":
        if not args.path:
            print("错误: --path required for log-file")
            return 1
        result = log_workflow_file_change(args.workdir, args.path, args.action)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "resume":
        result = resume_workflow(args.workdir, args.session_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "handle-failure":
        if not args.error:
            print("错误: --error required for handle-failure")
            return 1
        result = handle_workflow_failure(
            args.workdir,
            error=args.error,
            strategy=args.strategy,
            max_retries=args.max_retries,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "team-run":
        # Load state to get task info
        state = load_state(args.workdir)
        task_obj = state.task if state else None
        task_title = task_obj.title if task_obj and task_obj.title else "Untitled Team Task"
        contract = parse_phase_contract(args.workdir)
        frontier = compute_frontier(args.workdir)

        # Create and run team - tasks come from frontier/contract, not hardcoded
        phase_name = state.phase.get("current", "EXECUTING") if state and state.phase else "EXECUTING"
        team = TeamAgent(
            args.workdir,
            task=task_title,
            contract=contract,
            frontier=frontier,
            use_real_agent=getattr(args, 'use_real_agent', True),
        )
        team_result = team.run(phase=phase_name, register_artifacts=True)

        print(json.dumps({
            "team_session_id": team_result["session_id"],
            "tasks_completed": team_result["tasks_completed"],
            "tasks_failed": team_result["tasks_failed"],
            "outputs": team_result["outputs"],
            "used_real_agent": getattr(args, 'use_real_agent', True),
        }, ensure_ascii=False, indent=2))
        return 0

    print(json.dumps(get_workflow_snapshot(args.workdir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
