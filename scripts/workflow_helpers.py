"""
Workflow helper utilities: quality gates, summary generation, plan/spec creation.

Provides:
- _run_quality_gate_if_applicable: run quality gate for code tasks
- _run_review_gate_if_applicable: validate two-stage review completion
- _task_id_from_timestamp: generate a timestamp-based task ID
- _generate_and_register_summary: build and persist a completion summary artifact
- _derive_phase_contract_fields: derive contract fields from planning output
- _create_plan_from_template: create task_plan.md from a template file
- _create_spec_artifacts: create .specs/<feature_id>/ spec/plan/tasks files
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from findings_paths import (
    findings_latest_path,
    findings_session_path,
    legacy_findings_paths,
)
from review_paths import (
    legacy_review_paths,
    review_latest_path,
    review_session_path,
)
from safe_io import safe_write_json, safe_write_text_locked
from unified_state import (
    ArtifactType,
    _load_artifact_registry,
    get_review_summary,
    load_state,
    register_artifact,
)


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
    if int(review_summary.get("reviewed_targets_count", review_summary.get("files_reviewed", 0)) or 0) <= 0:
        return False, "review did not target any contract or task files"
    if review_summary.get("degraded_mode"):
        return False, "review is degraded"
    if review_summary.get("review_source") in {"template", "none", "workdir_scan"}:
        return False, f"review source is {review_summary.get('review_source')}"
    contract_alignment = str(review_summary.get("contract_alignment", "") or "").strip().lower()
    if contract_alignment in {"template", "fallback", "workdir_scan", "contract_miss"}:
        return False, f"review contract alignment is {contract_alignment or 'unset'}"
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
