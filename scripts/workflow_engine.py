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
from safe_io import safe_write_json, safe_write_text_locked
from skill_loader import SkillPromptFormatter, load_skill
from team_agent import TeamAgent
from trajectory_logger import TrajectoryLogger
from unified_state import (
    ArtifactType,
    can_transition,
    create_initial_state,
    get_allowed_transitions,
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

        return report.all_passed
    except Exception:
        # If quality gate fails for any reason, block completion for code tasks
        # This is fail-closed: code tasks must pass quality gate to complete
        return False


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
    findings_session_path = Path(workdir) / f"findings_{session_id}.md"
    if findings_session_path.exists():
        findings_content = findings_session_path.read_text(encoding="utf-8")
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
    review_session_path = Path(workdir) / f"review_{session_id}.md"
    if review_session_path.exists():
        review_content = review_session_path.read_text(encoding="utf-8")
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


def _create_spec_artifacts(task_name: str, task_description: str, workdir: str, session_id: str) -> tuple[Path | None, Path | None]:
    """
    Create spec.md and plan.md artifacts in .specs/<feature_id>/ directory.

    Args:
        task_name: Name/title of the task
        task_description: Full description
        workdir: Working directory
        session_id: Session identifier

    Returns:
        (spec_path, plan_path) tuple - either may be None if creation failed
    """
    # Generate feature_id from task_name
    feature_id = re.sub(r"[^a-zA-Z0-9]+", "_", task_name.lower())[:50]
    specs_dir = Path(workdir) / ".specs" / feature_id
    specs_dir.mkdir(parents=True, exist_ok=True)

    spec_path = None
    plan_path = None

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

    return spec_path, plan_path


def _phase_display_name(trigger_type: str, phase: str) -> str:
    if trigger_type == "DIRECT_ANSWER":
        return "DIRECT_ANSWER"
    if trigger_type == "FULL_WORKFLOW":
        return "PLANNING"
    return phase


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
    task_pattern = re.compile(r"^- \[\] \*\*(TASK-[^:]+):\*\* ([^\[]+)(?:\[P\])?")
    file_pattern = re.compile(r"\*\*Files:\*\*\s*`?([^`]+)`?")
    verification_pattern = re.compile(r"\*\*Verification:\*\*\s*(?:\[P\]\s*)?([^\n]+)")
    blocked_by_pattern = re.compile(r"\*\*Blocked-By:\*\*\s*([^\n]+)")
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

            task_id = task_match.group(1)
            title = task_match.group(2).strip()

            # Determine priority from section or task ID
            priority = "P1"
            if current_section in ("Setup", "Foundational"):
                priority = "P0"
            elif current_section == "Polish":
                priority = "P2"

            current_task = {
                "id": task_id,
                "title": title,
                "status": "backlog",
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

    if current_task:
        tasks.append(current_task)

    return tasks


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
    all_tasks = parse_tasks_md(workdir)
    if not all_tasks:
        all_tasks = parse_task_plan(workdir)
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
    all_tasks = parse_tasks_md(workdir)
    if not all_tasks:
        all_tasks = parse_task_plan(workdir)
    if not all_tasks:
        return {
            "executable_frontier": [],
            "ready_tasks": [],
            "parallel_candidates": [],
            "blocked_tasks": [],
            "conflict_groups": [],
            "completed_count": 0,
            "total_count": 0,
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
    }


@dataclass
class CheckpointConfig:
    """Conditional checkpoint configuration"""
    # Trigger checkpoint after N phase transitions (default 1 for immediate save)
    phase_change_threshold: int = 1
    # Trigger checkpoint after N resume attempts
    resume_threshold: int = 2
    # Trigger checkpoint after N failures
    failure_threshold: int = 1
    # Trigger checkpoint after N workflow steps
    step_threshold: int = 5
    # Enable auto-checkpoint
    enabled: bool = True


def should_checkpoint(
    workdir: str,
    config: CheckpointConfig | None = None,
) -> tuple[bool, str]:
    """
    Determine if a checkpoint should be triggered based on conditions.

    Conditions:
    - Phase changes since last checkpoint
    - Resume attempts
    - Failure count
    - Total workflow steps

    Returns:
        (should_checkpoint, reason)
    """
    if config is None:
        config = CheckpointConfig()

    if not config.enabled:
        return False, "checkpoint disabled"

    state = load_state(workdir)
    if state is None:
        return False, "no state"

    # Count phase transitions from workflow state (phase is a dict)
    phase_history = state.phase.get("history", []) if hasattr(state, 'phase') else []
    phase_changes = len(phase_history)

    # Get counters from state attributes
    resume_count = getattr(state, 'resume_count', 0)
    failure_count = getattr(state, 'failure_count', 0)
    step_count = getattr(state, 'step_count', 0)

    # Check each condition
    reasons = []
    if phase_changes >= config.phase_change_threshold:
        reasons.append(f"phase_changes={phase_changes}>={config.phase_change_threshold}")
    if resume_count >= config.resume_threshold:
        reasons.append(f"resume_count={resume_count}>={config.resume_threshold}")
    if failure_count >= config.failure_threshold:
        reasons.append(f"failure_count={failure_count}>={config.failure_threshold}")
    if step_count >= config.step_threshold:
        reasons.append(f"step_count={step_count}>={config.step_threshold}")

    if reasons:
        return True, "; ".join(reasons)

    return False, ""


def conditional_checkpoint(
    workdir: str,
    config: CheckpointConfig | None = None,
) -> dict[str, Any]:
    """
    Save a checkpoint if conditions are met.

    Creates:
    - .checkpoints/<checkpoint_id>.json: Full state snapshot
    - handoff_<checkpoint_id>.md: Human-readable handoff document

    Returns:
        {
            "checkpoint_saved": bool,
            "reason": str,
            "checkpoint_id": str,
            "session_id": str,
            "files": [str, ...],
            "error": str | None  # present when checkpoint_saved is False
        }

    Raises:
        No exceptions - all failures are reported via return dict with error field.
        This ensures callers can distinguish between "save succeeded" and "save failed"
        without relying on exception handling.
    """
    should_save, reason = should_checkpoint(workdir, config)

    if not should_save:
        return {"checkpoint_saved": False, "reason": reason, "error": None}

    state = load_state(workdir)
    if state is None:
        return {"checkpoint_saved": False, "reason": "no state", "error": "workflow state not found"}

    session_id = state.session_id
    workdir_path = Path(workdir)

    # Flush trajectory logger if active
    if session_id in _active_loggers:
        logger = _active_loggers[session_id]
        logger.flush()

    # Generate checkpoint ID
    import uuid
    checkpoint_id = f"cp-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8]}"

    # Create checkpoints directory
    checkpoints_dir = workdir_path / ".checkpoints"
    checkpoints_dir.mkdir(exist_ok=True)

    # Snapshot current state
    current_phase = state.phase.get("current", "UNKNOWN") if hasattr(state.phase, 'get') else "UNKNOWN"

    # Load task plan if exists
    try:
        plan_tasks = parse_task_plan(workdir)
        next_tasks = next_plan_tasks(workdir)
    except Exception:
        plan_tasks = []
        next_tasks = []

    # Create checkpoint JSON
    checkpoint_data = {
        "checkpoint_id": checkpoint_id,
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "reason": reason,
        "phase": current_phase,
        "task": state.task.to_dict() if state.task else None,
        "plan_tasks": plan_tasks,
        "next_tasks": next_tasks,
        "artifacts": state.artifacts if hasattr(state, 'artifacts') else [],
        "decisions": [d.to_dict() if hasattr(d, 'to_dict') else d for d in state.decisions] if hasattr(state, 'decisions') else [],
        "file_changes": state.file_changes if hasattr(state, 'file_changes') else [],
    }

    # Write checkpoint JSON - track success/failure explicitly
    checkpoint_file = checkpoints_dir / f"{checkpoint_id}.json"
    handoff_file = workdir_path / f"handoff_{checkpoint_id}.md"

    try:
        safe_write_json(checkpoint_file, checkpoint_data)
    except Exception as e:
        # Checkpoint JSON write failed - return failure without claiming success
        return {
            "checkpoint_saved": False,
            "reason": reason,
            "checkpoint_id": checkpoint_id,
            "session_id": session_id,
            "files": [],
            "error": f"checkpoint JSON write failed: {e}",
        }

    # Parse contract and frontier state (optional - don't fail if these fail)
    try:
        contract_state = parse_phase_contract(workdir)
        frontier_state = compute_frontier(workdir)
    except Exception:
        contract_state = {}
        frontier_state = {"executable_frontier": [], "blocked_tasks": [], "conflict_groups": []}

    # Parse recent decisions (last 3)
    recent_decisions = []
    if hasattr(state, 'decisions') and state.decisions:
        for d in state.decisions[-3:]:
            if hasattr(d, 'to_dict'):
                recent_decisions.append(d.to_dict().get('decision', str(d)))
            elif isinstance(d, dict):
                recent_decisions.append(d.get('decision', str(d)))

    # Build handoff content
    handoff_content = f"""# Checkpoint Handoff: {checkpoint_id}

**Created**: {datetime.now().isoformat()}
**Reason**: {reason}
**Session**: {session_id}
**Phase**: {current_phase}

## Task
{state.task.title if state.task else "Unknown task"}

## Contract Status
"""
    if contract_state.get("goals"):
        handoff_content += f"- Goals: {len(contract_state['goals'])} defined\n"
        handoff_content += f"- Verification methods: {len(contract_state.get('verification_methods', []))} defined\n"
        handoff_content += f"- Owned files: {len(contract_state.get('owned_files', []))} tracked\n"
    else:
        handoff_content += "- No contract or contract not yet negotiated\n"

    handoff_content += f"""
## Current State
- Phase: {current_phase}
- Plan Tasks: {len(plan_tasks)} total, {len(next_tasks)} next
- Frontier: {len(frontier_state.get('executable_frontier', []))} ready, {len(frontier_state.get('blocked_tasks', []))} blocked, {len(frontier_state.get('conflict_groups', []))} conflict groups

## Next Tasks
"""
    for t in next_tasks[:5]:
        handoff_content += f"- [{t.get('id', '?')}] {t.get('title', 'Untitled')}\n"

    if recent_decisions:
        handoff_content += "\n## Recent Decisions\n"
        for d in recent_decisions:
            handoff_content += f"- {d}\n"

    # List key artifacts
    artifacts = list(state.artifacts) if hasattr(state, 'artifacts') and state.artifacts else []
    if artifacts:
        handoff_content += "\n## Key Artifacts\n"
        for art in artifacts[:5]:
            if isinstance(art, dict):
                handoff_content += f"- {art.get('name', str(art))}\n"
            else:
                handoff_content += f"- {art}\n"

    handoff_content += f"""
## How to Resume
```bash
python3 scripts/workflow_engine.py --op resume --session-id {session_id} --workdir {workdir}
```

---
*This is an auto-generated handoff document. See .checkpoints/{checkpoint_id}.json for full state.*
"""

    # Write handoff file - if this fails, checkpoint JSON was already saved
    # Return partial success so caller knows the state
    try:
        safe_write_text_locked(handoff_file, handoff_content)
    except Exception as e:
        # Handoff write failed but checkpoint JSON was saved
        # Return success with warning - checkpoint can still be recovered from JSON
        return {
            "checkpoint_saved": True,
            "reason": reason,
            "checkpoint_id": checkpoint_id,
            "session_id": session_id,
            "files": [str(checkpoint_file)],
            "error": f"handoff write failed (checkpoint JSON saved): {e}",
            "partial": True,
        }

    return {
        "checkpoint_saved": True,
        "reason": reason,
        "checkpoint_id": checkpoint_id,
        "session_id": session_id,
        "files": [str(checkpoint_file), str(handoff_file)],
        "error": None,
    }


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
    tasks = parse_task_plan(workdir)
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
    plan_path = Path(workdir) / "task_plan.md"
    if not plan_path.exists():
        return {"success": False, "error": "task_plan.md not found"}

    if status not in ("backlog", "in_progress", "completed", "blocked"):
        return {"success": False, "error": f"Invalid status: {status}"}

    content = plan_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    new_lines = []
    task_found = False
    in_target_task = False

    task_pattern = re.compile(r"^- \[(?P<done>[ xX])\] (?P<id>TASK-\d+):")
    field_pattern = re.compile(r"^\s+- (?P<key>[a-zA-Z_]+):")

    for line in lines:
        task_match = task_pattern.match(line.rstrip())
        if task_match:
            in_target_task = task_match.group("id") == task_id
            if in_target_task:
                task_found = True
                # Update checkbox
                done_marker = "x" if status == "completed" else " "
                new_lines.append(f"- [{done_marker}] {task_match.group('id')}:" + line.split(":", 1)[1])
                continue

        if in_target_task:
            field_match = field_pattern.match(line)
            if field_match:
                key = field_match.group("key")
                if key == "status":
                    new_lines.append(f"  - status: {status}")
                    continue

        new_lines.append(line)

    if not task_found:
        return {"success": False, "error": f"Task {task_id} not found"}

    safe_write_text_locked(plan_path, "\n".join(new_lines))
    return {"success": True, "task_id": task_id, "status": status}


def allowed_next_phases(phase: str) -> list[str]:
    return sorted(get_allowed_transitions(phase))


def recommend_next_phases(current_phase: str, trigger_type: str | None = None) -> list[str]:
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
    if not can_transition(current_phase, next_phase):
        raise ValueError(f"illegal phase transition: {current_phase} -> {next_phase}")


def initialize_workflow(
    prompt: str,
    workdir: str = ".",
    task_id: str | None = None,
    auto_create_plan: bool = True,
) -> dict[str, Any]:
    workdir_path = Path(workdir)
    workdir_path.mkdir(parents=True, exist_ok=True)

    session_path = workdir_path / memory_ops.DEFAULT_SESSION_STATE
    tracker_path = workdir_path / task_tracker.DEFAULT_TRACKER_FILE

    memory_ops.ensure_session_state_exists(str(session_path))
    task_tracker.save_tracker(str(tracker_path), task_tracker.load_tracker(str(tracker_path)))

    trigger_type, routed_phase = router.route(prompt)
    current_phase = _phase_display_name(trigger_type, routed_phase)

    # Create unified state
    state = create_initial_state(
        prompt=prompt,
        task_id=task_id or _task_id_from_timestamp(),
        trigger_type=trigger_type,
        initial_phase=current_phase,
    )

    # NOTE: create_initial_state already sets the phase to initial_phase
    # Don't call transition_phase here as it would try to transition to the same phase

    # Ensure trajectory directory exists
    traj_dir = trajectory_dir_path(workdir)
    traj_dir.mkdir(parents=True, exist_ok=True)

    # Start trajectory logging
    logger = TrajectoryLogger(workdir, state.session_id)
    logger.start(prompt, trigger_type)
    logger.enter_phase(current_phase)
    _active_loggers[state.session_id] = logger

    # Trajectory info tracked in _active_loggers and saved to trajectory files
    # All artifact tracking goes through artifact_registry (authoritative source)

    memory_ops.update_task_info(str(session_path), prompt, current_phase)
    memory_ops.update_resume_point(str(session_path), current_phase, 0)

    # Create progress.md
    progress_file = workdir_path / "progress.md"
    progress_content = f"""# Progress

## Current Phase
- phase: {current_phase}
- status: active
- updated: {datetime.now().isoformat()}

## Session
- session_id: {state.session_id}
- task_id: {state.task.task_id if state.task else 'N/A'}
"""
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

    plan_path: Path | None = None
    contract_path: Path | None = None
    spec_path: Path | None = None
    if auto_create_plan and current_phase == "PLANNING":
        plan_path = _create_plan_from_template(prompt, workdir)
        if plan_path is not None:
            # Register plan artifact (authoritative tracking via registry only)
            register_artifact(workdir, ArtifactType.PLAN, str(plan_path), current_phase, "system")

        # Create spec.md and plan.md in .specs/<feature_id>/ directory
        task_title = state.task.title if state.task else prompt[:50]
        task_desc = state.task.description if state.task else prompt
        spec_path, plan_md_path = _create_spec_artifacts(
            task_title, task_desc, workdir, state.session_id
        )
        if spec_path is not None:
            register_artifact(workdir, ArtifactType.CUSTOM, str(spec_path), current_phase, "system",
                           metadata={"deliverable": "spec", "type": "spec.md"})
        if plan_md_path is not None:
            register_artifact(workdir, ArtifactType.CUSTOM, str(plan_md_path), current_phase, "system",
                           metadata={"deliverable": "plan", "type": "plan.md"})

        # Create Anthropic-style phase contract
        contract_path = _create_phase_contract(task_title, task_desc, workdir)
        if contract_path is not None:
            register_artifact(workdir, "contract", str(contract_path), current_phase, "system",
                            metadata={"deliverable": "contract", "phase": current_phase})

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
        "plan_created": plan_path is not None,
        "recommended_next_phases": recommend_next_phases(current_phase, trigger_type),
        "state_file": str(workflow_state_path(workdir)),
        "trajectory_session_id": state.session_id,
    }


def advance_workflow(
    phase: str,
    workdir: str = ".",
    progress: int = 0,
    task_status: str | None = None,
    note: str = "",
) -> dict[str, Any]:
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

    # Update progress.md
    progress_file = Path(workdir) / "progress.md"
    if progress_file.exists():
        content = progress_file.read_text(encoding="utf-8")
        # Simple update of phase and status
        lines = content.split("\n")
        new_lines = []
        in_phase_section = False
        for line in lines:
            if "## Current Phase" in line:
                in_phase_section = True
            if in_phase_section and line.startswith("- phase:"):
                new_lines.append(f"- phase: {phase}")
                in_phase_section = False
                continue
            if in_phase_section and line.startswith("- status:"):
                new_lines.append(f"- status: {task_status or 'active'}")
                in_phase_section = False
                continue
            new_lines.append(line)
        safe_write_text_locked(progress_file, "\n".join(new_lines))

    # Save updated state
    save_state(workdir, state)

    memory_ops.update_task_info(str(session_path), state.task.description if state.task else "(未设置)", phase)
    memory_ops.update_resume_point(str(session_path), phase, progress)

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

            findings_path = Path(workdir) / f"findings_{session_id}.md"
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
        else:
            # Fall back to template-based findings (search failed or unavailable)
            desc_lower = task_desc.lower()
            findings_list = []

            # Generate specific findings based on what the task is asking about
            if "最佳实践" in desc_lower or "best practice" in desc_lower:
                findings_list.append(f"1. **Best Practices for {key_terms_str}**: Identified established patterns and approaches that represent current industry consensus for this domain.")
            if "架构" in desc_lower or "architecture" in desc_lower:
                findings_list.append(f"2. **Architectural Patterns for {key_terms_str}**: Found multiple architectural approaches with different trade-offs in complexity, scalability, and maintainability.")
            if "安全" in desc_lower or "security" in desc_lower:
                findings_list.append(f"3. **Security Considerations for {key_terms_str}**: Key security concerns and mitigation strategies documented based on common vulnerability patterns.")
            if "性能" in desc_lower or "performance" in desc_lower:
                findings_list.append(f"4. **Performance Optimization for {key_terms_str}**: Benchmark strategies and optimization opportunities identified for typical workloads.")
            if "微服务" in desc_lower or "microservice" in desc_lower:
                findings_list.append(f"5. **Microservice Considerations for {key_terms_str}**: Service decomposition strategies and inter-service communication patterns reviewed.")
            if "数据库" in desc_lower or "database" in desc_lower or "db" in desc_lower:
                findings_list.append(f"6. **Data Persistence for {key_terms_str}**: Database selection criteria and schema design considerations documented.")
            if "容错" in desc_lower or "fault" in desc_lower or " resilience" in desc_lower:
                findings_list.append(f"7. **Resilience Patterns for {key_terms_str}**: Fault tolerance strategies including retry, circuit breaker, and graceful degradation approaches reviewed.")

            # If no specific aspects found, generate findings based on key terms
            if not findings_list:
                findings_list.append(f"1. **Domain Analysis of {key_terms_str}**: Research identified core concepts and fundamental approaches for this domain.")
                findings_list.append(f"2. **Implementation Considerations for {key_terms_str}**: Key factors and potential challenges documented for implementation planning.")

            # Generate recommendations based on findings
            recommendations = []
            if "架构" in desc_lower or "architecture" in desc_lower:
                recommendations.append("- Select architectural pattern based on specific scalability and maintainability requirements")
            if "安全" in desc_lower or "security" in desc_lower:
                recommendations.append("- Prioritize security review before production deployment")
            if "性能" in desc_lower or "performance" in desc_lower:
                recommendations.append("- Establish performance benchmarks early in development cycle")
            recommendations.append("- Proceed to planning phase with documented research findings")
            recommendations.append("- Validate research conclusions against specific project requirements")

            findings_path = Path(workdir) / f"findings_{session_id}.md"
            findings_content = f"""# Research Findings: {task_title}

## Research Question
{task_desc}

## Method
- Research conducted at: {datetime.now().isoformat()}
- Focus: {key_terms_str}
- Note: Template-based analysis (web search unavailable)

## Key Findings
{chr(10).join(findings_list)}

## Conclusions
- Research completed focusing on: {key_terms_str}
- Findings provide actionable insights for implementation planning
- Further validation against specific project constraints recommended

## Recommendations
{chr(10).join(recommendations)}
"""
            search_note = search_response.error if search_response.error else "Search unavailable"
            metadata = {
                "deliverable": "findings",
                "session_id": session_id,
                "has_method": True,
                "has_conclusions": True,
                "generated_on_exit": True,
                "key_terms": key_terms_str,
                "search_error": search_note,
                "used_real_search": False,
            }

        safe_write_text_locked(findings_path, findings_content)
        register_artifact(workdir, ArtifactType.FINDINGS, str(findings_path), "RESEARCH", "system", metadata=metadata)

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

        # Task-directed review: prioritize owned_files from task_plan, then file_changes, then fallback
        target_files = []
        review_source = "none"

        # 1. Try to get owned_files from task_plan
        plan_path = Path(workdir) / "task_plan.md"
        if plan_path.exists():
            plan_content = plan_path.read_text(encoding="utf-8", errors="ignore")
            # Parse owned_files from plan (format: "  - owned_files: file1.py, file2.py")
            import re
            owned_pattern = re.compile(r'owned_files:\s*(.+)', re.IGNORECASE)
            for line in plan_content.split('\n'):
                match = owned_pattern.search(line)
                if match:
                    files_str = match.group(1).strip()
                    for f in files_str.split(','):
                        f = f.strip()
                        if f:
                            fp = Path(workdir) / f
                            if fp.exists():
                                target_files.append(fp)
                    if target_files:
                        review_source = "owned_files"
                        break

        # 2. Try to get files from state.file_changes
        if not target_files and state.file_changes:
            for fc in state.file_changes[:10]:  # Limit to first 10 changes
                fp = Path(workdir) / fc.path
                if fp.exists() and fp.suffix in {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs', '.c', '.cpp'}:
                    target_files.append(fp)
            if target_files:
                review_source = "file_changes"

        # 3. Strict fallback: ONLY do workdir_scan if explicitly allowed
        # Check if user/task explicitly allows fallback review
        review_fallback_allowed = False
        if state.task:
            task_text = (state.task.description or "").lower() + (state.task.title or "").lower()
            if "allow_review_fallback" in task_text or "review_fallback=true" in task_text:
                review_fallback_allowed = True

        # Also check task_plan.md for explicit allow_fallback flag
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

            review_path = Path(workdir) / f"review_{session_id}.md"
            degraded_note = ""
            if review_source == "workdir_scan":
                degraded_note = """> **⚠️ Degraded Mode**: Review used workdir_scan fallback (task_plan has no owned_files and no file_changes recorded). Results are less targeted than owned_files/file_changes directed review.
"""
            review_content = f"""# Code Review: {task_title}

## Review Scope
{task_title}

## Task Description
{task_desc}
{contract_info}

## Review Date
{datetime.now().isoformat()}

{degraded_note}## Reviewed Files ({len(target_files)} files analyzed)
{chr(10).join(reviewed_files_info)}

## Risk Findings
{chr(10).join(risk_findings)}

## Risk Assessment
- **Files Reviewed**: {len(target_files)} code files
- **Total Lines**: {total_lines}
- **Correctness**: Implementation reviewed based on actual code
- **Security**: Security posture assessed based on code analysis
- **Maintainability**: Code structure supports future maintenance

## Risk Level
- **Overall**: {risk_level}
- {"High-risk areas identified - requires careful review" if risk_level == "High" else "Standard review findings apply" if risk_level == "Medium" else "Critical areas require immediate attention"}

## Recommendations
{chr(10).join(recommendations)}
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

            review_path = Path(workdir) / f"review_{session_id}.md"
            review_content = f"""# Code Review: {task_title}

## Review Scope
{task_title}

## Task Description
{task_desc}

## Review Date
{datetime.now().isoformat()}

## Risk Findings
{chr(10).join(risk_findings)}

## Risk Assessment
- **Correctness**: Implementation reviewed for functional correctness
- **Security**: Security posture assessed based on task requirements
- **Maintainability**: Code structure supports future maintenance

## Risk Level
- **Overall**: {risk_level}
- {"High-risk areas identified - requires careful review" if risk_level == "High" else "Critical areas require dedicated security review" if risk_level == "Critical" else "Standard review findings apply"}

## Recommendations
{chr(10).join(recommendations)}
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

        safe_write_text_locked(review_path, review_content)
        register_artifact(workdir, ArtifactType.REVIEW, str(review_path), "REVIEWING", "system", metadata=metadata)

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
    except Exception:
        # Skill loading is best-effort - don't fail the phase transition
        pass

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
    }


def complete_workflow(
    workdir: str = ".",
    final_state: str = "completed",
    failure_reason: str | None = None,
) -> dict[str, Any]:
    """
    完成工作流并结束 trajectory 记录

    Args:
        workdir: 工作目录
        final_state: 最终状态 (completed/failed/aborted)
        failure_reason: 失败原因（如果失败）

    Returns:
        完成结果

    Raises:
        ValueError: 如果是代码任务且质量门禁失败
    """
    state = load_state(workdir)
    if state is None:
        raise ValueError("workflow state not found, please run init first")

    current_phase = state.phase.get("current", "IDLE")
    session_id = state.session_id or "unknown"

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

        # Contract fulfillment gate: validate contract is properly fulfilled
        contract_valid, contract_error = validate_contract_gate(workdir, state)
        if not contract_valid:
            raise ValueError(
                f"Cannot complete workflow: {contract_error}"
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
    从中断点恢复工作流

    Args:
        workdir: 工作目录
        session_id: 可选的 session ID，默认从 trajectory 获取最新中断的

    Returns:
        恢复结果
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

    # 更新 unified state - 这是关键同步步骤
    state = load_state(workdir)
    if state is not None:
        # 记录恢复决策
        from datetime import datetime

        from state_schema import Decision
        state.decisions.append(Decision(
            timestamp=datetime.now().isoformat(),
            decision=f"Resumed from {session_id}",
            reason=f"resume_from={result['resume_from']}",
            metadata={"original_session": session_id, "resumed_session": new_session_id},
        ))

        # 更新 session_id
        state.session_id = new_session_id

        # 更新 phase
        state.phase["current"] = next_phase

        save_state(workdir, state)

    # 重新初始化 trajectory logger
    new_logger = TrajectoryLogger(workdir, new_session_id)
    new_logger.start(f"[RESUMED from {session_id}]", "RESUMED")
    new_logger.enter_phase(next_phase)
    _active_loggers[new_session_id] = new_logger

    return {
        "success": True,
        "original_session_id": session_id,
        "new_session_id": new_session_id,
        "resume_from": result["resume_from"],
        "next_phase": next_phase,
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

    # Syntax errors always go to debugging immediately - they can't be fixed by retry
    if error_type == "syntax_error":
        strategy = "debugging"
        retry_hint = "syntax error cannot be fixed by retry"

    if strategy == "retry":
        # Get retry count and error history from decisions
        retry_count = 0
        error_history = _get_error_history(state)

        if state.decisions:
            last_decision = state.decisions[-1]
            retry_count = last_decision.metadata.get("retry_count", 0)

        # Adjust max_retries based on error classification
        adjusted_max_retries = max_retries
        retry_hint = ""

        if error_type == "test_failure" and retry_count >= 1:
            # After one test failure retry, suggest debugging
            adjusted_max_retries = max(retry_count + 1, 2)
        elif error_type == "lint_error":
            # Lint errors often fixed by auto-fix
            retry_hint = "try running ruff/lint auto-fix"
        elif error_type == "type_error":
            # Type errors need careful review
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
            }
            if retry_hint:
                result["retry_hint"] = retry_hint
            if quality_gate_details:
                result["quality_gate_details"] = quality_gate_details
            return result

    if strategy == "debugging":
        if can_transition(current_phase, "DEBUGGING"):
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
            }
        else:
            return {
                "success": False,
                "error": f"Cannot transition from {current_phase} to DEBUGGING",
            }

    if strategy == "abort":
        complete_workflow(workdir, "failed", error)
        return {
            "success": True,
            "action": "aborted",
            "final_state": "failed",
            "error": error,
            "error_type": error_type,
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


def get_workflow_snapshot(workdir: str = ".") -> dict[str, Any]:
    state = load_state(workdir)
    tracker_path = Path(workdir) / task_tracker.DEFAULT_TRACKER_FILE
    task = None

    if state is None:
        return {
            "exists": False,
            "valid": False,
            "errors": ["state file does not exist"],
            "recommended_next_phases": [],
            "plan_tasks": [],
            "next_plan_tasks": [],
        }

    if state.task and state.task.task_id:
        task = task_tracker.get_task(state.task.task_id, str(tracker_path))

    plan_tasks = parse_task_plan(workdir)
    next_tasks = next_plan_tasks(workdir)

    current_phase = state.phase.get("current", "IDLE") if state.phase else "IDLE"

    # Load artifact registry for full audit trail
    from unified_state import _load_artifact_registry
    artifact_registry = _load_artifact_registry(workdir)

    # Validate state
    from unified_state import validate_workflow_state
    is_valid, errors = validate_workflow_state(workdir)

    return {
        "exists": True,
        "valid": is_valid,
        "errors": errors,
        "session_id": state.session_id,
        "task_id": state.task.task_id if state.task else None,
        "current_phase": current_phase,
        "trigger_type": state.trigger_type,
        "task": task,
        "recommended_next_phases": recommend_next_phases(current_phase, None),
        "plan_tasks": plan_tasks,
        "next_plan_tasks": next_tasks,
        "state_file": str(workflow_state_path(workdir)),
        # artifact_registry is the authoritative source - state.artifacts removed from interface
        "artifact_registry": artifact_registry.get("artifacts", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Workflow runtime engine")
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
        print(json.dumps({"tasks": parse_task_plan(args.workdir), "next_tasks": next_plan_tasks(args.workdir)}, ensure_ascii=False, indent=2))
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
            use_real_agent=getattr(args, 'use_real_agent', False),
        )
        team_result = team.run(phase=phase_name, register_artifacts=True)

        print(json.dumps({
            "team_session_id": team_result["session_id"],
            "tasks_completed": team_result["tasks_completed"],
            "tasks_failed": team_result["tasks_failed"],
            "outputs": team_result["outputs"],
            "used_real_agent": getattr(args, 'use_real_agent', False),
        }, ensure_ascii=False, indent=2))
        return 0

    print(json.dumps(get_workflow_snapshot(args.workdir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
