#!/usr/bin/env python3
"""
Unified State Management

Manages workflow state based on the unified schema defined in state_schema.py.
Provides a single source of truth, reducing fragility from markdown parsing.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from memory_ops import get_planning_summary as get_session_planning_summary
from memory_ops import get_research_summary as get_session_research_summary
from memory_ops import get_review_summary as get_session_review_summary
from memory_ops import get_runtime_profile as get_session_runtime_profile
from memory_ops import get_thinking_summary as get_session_thinking_summary
from safe_io import safe_write_json_locked
from state_schema import (
    Decision,
    FileChange,
    PhaseEntry,
    Task,
    Trajectory,
    TrajectoryPhase,
    WorkflowState,
    validate_state,
)

# 默认文件名
WORKFLOW_STATE_FILE = ".workflow_state.json"
TRAJECTORY_DIR = "trajectories"
ARTIFACT_REGISTRY_FILE = ".artifacts.json"


# ============================================================================
# Artifact Registry - 工件注册表
# ============================================================================


class ArtifactType:
    """工件类型枚举"""
    STATE = "state"
    TRAJECTORY = "trajectory"
    PLAN = "plan"
    FINDINGS = "findings"
    REVIEW = "review"
    SUMMARY = "summary"
    PROGRESS = "progress"
    SESSION = "session"
    TRACKER = "tracker"
    CODE = "code"
    DEBUG = "debug"
    CUSTOM = "custom"


def register_artifact(
    workdir: str,
    artifact_type: str,
    file_path: str,
    phase: str,
    generated_by: str = "system",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    注册一个工件

    Args:
        workdir: 工作目录
        artifact_type: 工件类型
        file_path: 文件路径
        phase: 所属 phase
        generated_by: 生成者 (system/agent/user)
        metadata: 额外元数据

    Returns:
        工件记录
    """
    registry = _load_artifact_registry(workdir)

    artifact_id = f"{artifact_type}_{len(registry.get('artifacts', [])) + 1}"
    artifact = {
        "id": artifact_id,
        "type": artifact_type,
        "path": file_path,
        "phase": phase,
        "generated_by": generated_by,
        "created_at": datetime.now().isoformat(),
        "metadata": metadata or {},
    }

    if "artifacts" not in registry:
        registry["artifacts"] = []
    registry["artifacts"].append(artifact)
    registry["updated_at"] = datetime.now().isoformat()

    _save_artifact_registry(workdir, registry)
    return artifact


def get_artifacts(
    workdir: str,
    artifact_type: str | None = None,
    phase: str | None = None,
) -> list[dict[str, Any]]:
    """
    获取工件列表

    Args:
        workdir: 工作目录
        artifact_type: 可选的工件类型过滤
        phase: 可选的 phase 过滤

    Returns:
        工件列表
    """
    registry = _load_artifact_registry(workdir)
    artifacts_raw = registry.get("artifacts", [])
    if not isinstance(artifacts_raw, list):
        return []
    artifacts: list[dict[str, Any]] = artifacts_raw

    if artifact_type:
        artifacts = [a for a in artifacts if isinstance(a, dict) and a.get("type") == artifact_type]
    if phase:
        artifacts = [a for a in artifacts if isinstance(a, dict) and a.get("phase") == phase]

    return artifacts


def get_artifact_by_id(workdir: str, artifact_id: str) -> dict[str, Any] | None:
    """根据ID获取工件"""
    registry = _load_artifact_registry(workdir)
    artifacts = registry.get("artifacts", [])
    if not isinstance(artifacts, list):
        return None
    for artifact in artifacts:
        if isinstance(artifact, dict) and artifact.get("id") == artifact_id:
            return artifact
    return None


def _load_artifact_registry(workdir: str) -> dict[str, Any]:
    """加载工件注册表"""
    path = Path(workdir) / ARTIFACT_REGISTRY_FILE
    if not path.exists():
        return {"artifacts": [], "created_at": datetime.now().isoformat()}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {"artifacts": [], "created_at": datetime.now().isoformat()}
    except (OSError, json.JSONDecodeError):
        return {"artifacts": [], "created_at": datetime.now().isoformat()}


def _save_artifact_registry(workdir: str, registry: dict[str, Any]) -> Path:
    """保存工件注册表"""
    path = Path(workdir) / ARTIFACT_REGISTRY_FILE
    safe_write_json_locked(path, registry)
    return path


def workflow_state_path(workdir: str = ".") -> Path:
    """获取统一状态文件路径"""
    return Path(workdir) / WORKFLOW_STATE_FILE


def trajectory_dir_path(workdir: str = ".") -> Path:
    """获取轨迹目录路径"""
    return Path(workdir) / TRAJECTORY_DIR


def _init_phase_state(current_phase: str = "IDLE") -> dict[str, Any]:
    """初始化phase state，包含初始phase entry到history"""
    now = datetime.now().isoformat()
    return {
        "current": current_phase,
        "history": [
            {
                "phase": current_phase,
                "entered_at": now,
                "exited_at": None,
                "reason": "initial",
                "actions": [],
                "decisions": [],
                "file_changes": [],
                "error": None,
            }
        ],
        "entered_at": now,
    }


def create_initial_state(
    prompt: str,
    task_id: str | None = None,
    trigger_type: str = "FULL_WORKFLOW",
    initial_phase: str = "PLANNING",
) -> WorkflowState:
    """
    创建初始状态

    Args:
        prompt: 用户提示
        task_id: 可选的任务ID，默认自动生成
        trigger_type: 触发类型
        initial_phase: 初始phase

    Returns:
        WorkflowState实例
    """
    now = datetime.now()
    tid = task_id or f"T{now.strftime('%Y%m%d%H%M%S')}"

    task = Task(
        task_id=tid,
        title=prompt[:100] if prompt else "Untitled",
        description=prompt,
        status="in_progress",
        created_at=now.isoformat(),
    )

    state = WorkflowState(
        session_id=f"s{now.strftime('%Y%m%d%H%M%S')}",
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        trigger_type=trigger_type,
        task=task,
        phase=_init_phase_state(initial_phase),
        artifacts={},
    )

    # 添加初始决策记录
    state.decisions.append(Decision(
        timestamp=now.isoformat(),
        decision=f"Workflow initialized with trigger_type={trigger_type}",
        reason="create_initial_state",
    ))

    return state


def load_state(workdir: str = ".") -> WorkflowState | None:
    """
    加载状态文件

    Returns:
        WorkflowState实例，如果文件不存在则返回None
    """
    path = workflow_state_path(workdir)
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return WorkflowState.from_dict(data)


def save_state(workdir: str, state: WorkflowState) -> Path:
    """
    保存状态文件

    Args:
        workdir: 工作目录
        state: WorkflowState实例

    Returns:
        保存的文件路径
    """
    path = workflow_state_path(workdir)
    state.updated_at = datetime.now().isoformat()
    safe_write_json_locked(path, state)

    return path


def validate_workflow_state(workdir: str = ".") -> tuple[bool, list[str]]:
    """
    验证状态文件

    Returns:
        (is_valid, error_list)
    """
    state = load_state(workdir)
    if state is None:
        return False, ["state file does not exist"]

    data = state.to_dict()
    errors = validate_state(data)
    aligned, sidecar_errors = compare_state_sidecar_consistency(workdir, state)
    if not aligned:
        errors.extend(sidecar_errors)

    return len(errors) == 0, errors


def get_runtime_profile_summary(state: WorkflowState | None) -> dict[str, Any]:
    """Extract a compact runtime profile summary from workflow state metadata."""
    runtime_profile = state.metadata.get("runtime_profile", {}) if state and state.metadata else {}
    return {
        "skill_policy": runtime_profile.get("skill_policy") if runtime_profile else None,
        "use_skill": runtime_profile.get("use_skill") if runtime_profile else None,
        "skill_activation_level": runtime_profile.get("skill_activation_level") if runtime_profile else None,
        "tokens_expected": runtime_profile.get("tokens_expected") if runtime_profile else None,
        "profile_source": runtime_profile.get("profile_source") if runtime_profile else None,
        "complexity": state.metadata.get("complexity") if state and state.metadata else None,
        "complexity_confidence": state.metadata.get("complexity_confidence") if state and state.metadata else None,
    }


def get_planning_summary(workdir: str, state: WorkflowState | None = None) -> dict[str, Any]:
    """Extract a compact summary of the canonical planning chain.

    This mirrors the persistent-markdown planning pattern:
    keep the plan visible, expose progress, and warn when a worktree is
    appropriate for multi-step or multi-file work.
    """
    if state is None:
        state = load_state(workdir)

    return _build_planning_summary(workdir, state)


def get_research_summary(workdir: str, state: WorkflowState | None = None) -> dict[str, Any]:
    """Extract a compact summary of the latest research findings artifact."""
    session_state_path = Path(workdir) / "SESSION-STATE.md"
    summary = get_session_research_summary(str(session_state_path))
    if _is_meaningful_research_summary(summary):
        return _enrich_research_summary(summary)

    return _build_research_summary_from_state(workdir, state)


def _build_research_summary_from_state(workdir: str, state: WorkflowState | None = None) -> dict[str, Any]:
    """Build the canonical research summary without consulting the sidecar."""
    research_artifacts = get_artifacts(workdir, ArtifactType.FINDINGS, phase="RESEARCH")
    latest_artifact = research_artifacts[-1] if research_artifacts else None
    metadata = latest_artifact.get("metadata", {}) if isinstance(latest_artifact, dict) else {}
    findings_path = latest_artifact.get("path") if isinstance(latest_artifact, dict) else None
    if latest_artifact:
        summary = {
            "research_found": True,
            "research_source": "artifact_registry",
            "research_path": findings_path,
            "key_terms": metadata.get("key_terms"),
            "search_engine": metadata.get("search_engine"),
            "sources_count": metadata.get("sources_count", 0),
            "used_real_search": metadata.get("used_real_search", False),
            "degraded_mode": metadata.get("degraded_mode", False),
            "degraded_reason": metadata.get("degraded_reason"),
            "search_error": metadata.get("search_error"),
            "evidence_status": "verified" if metadata.get("used_real_search") and metadata.get("sources_count", 0) else "degraded",
        }
        return _enrich_research_summary(summary)

    if state is None:
        state = load_state(workdir)
    if state is None:
        return {}

    current_phase = state.phase.get("current") if state.phase else "IDLE"
    if current_phase in {"COMPLETE", "failed", "aborted", "IDLE"} or not state.task:
        return {}

    try:
        from findings_paths import findings_latest_path

        findings_path = findings_latest_path(workdir)
        if findings_path.exists():
            content = findings_path.read_text(encoding="utf-8", errors="ignore")
            degraded_mode = "degraded" in content.lower()
            return _enrich_research_summary({
                "research_found": True,
                "research_source": "findings_latest",
                "research_path": str(findings_path),
                "key_terms": state.task.title if state.task else "",
                "search_engine": None,
                "sources_count": 0,
                "used_real_search": not degraded_mode,
                "degraded_mode": degraded_mode,
                "degraded_reason": "derived from findings_latest",
                "search_error": None,
                "evidence_status": "degraded" if degraded_mode else "verified",
            })
    except Exception:
        return {}

    return {}


def _enrich_research_summary(summary: dict[str, Any] | None) -> dict[str, Any]:
    """Add evidence-grading metadata to a research summary."""
    if not summary:
        return {}

    enriched = dict(summary)
    evidence_status = str(enriched.get("evidence_status", "")).strip().lower()
    sources_count = int(enriched.get("sources_count", 0) or 0)
    used_real_search = bool(enriched.get("used_real_search", False))
    degraded_mode = bool(enriched.get("degraded_mode", False))

    if not evidence_status or evidence_status in {"unset", "none", "(未设置)"}:
        if used_real_search and sources_count >= 1:
            evidence_status = "verified"
        elif degraded_mode or sources_count > 0:
            evidence_status = "degraded"
        else:
            evidence_status = "missing"
    enriched["evidence_status"] = evidence_status

    if evidence_status == "verified" and used_real_search and sources_count >= 2:
        evidence_tier = "primary_verified"
        source_confidence = 0.9
    elif evidence_status == "verified":
        evidence_tier = "secondary_verified"
        source_confidence = 0.75
    elif evidence_status == "degraded" and sources_count > 0:
        evidence_tier = "heuristic"
        source_confidence = 0.45
    elif evidence_status == "degraded":
        evidence_tier = "degraded"
        source_confidence = 0.25
    else:
        evidence_tier = "missing"
        source_confidence = 0.0

    source_types = enriched.get("source_types")
    if not isinstance(source_types, list):
        source_types = []
    if enriched.get("research_source"):
        source_types.append(str(enriched["research_source"]))
    if enriched.get("search_engine"):
        source_types.append(f"search:{enriched['search_engine']}")
    if used_real_search:
        source_types.append("search_results")
    if enriched.get("research_path"):
        source_types.append("artifact")

    coverage_scope = "broad" if used_real_search and sources_count >= 3 else "normal" if sources_count >= 1 else "narrow"
    freshness = "current" if evidence_status == "verified" else "stale" if evidence_status == "degraded" else "unknown"

    enriched.update(
        {
            "evidence_tier": evidence_tier,
            "source_confidence": round(float(source_confidence), 2),
            "source_types": list(dict.fromkeys([str(item) for item in source_types if str(item).strip()])),
            "coverage_scope": coverage_scope,
            "freshness": freshness,
        }
    )
    return enriched


def _build_planning_summary(workdir: str, state: WorkflowState | None) -> dict[str, Any]:
    """Build the canonical planning summary from live plan/frontier state."""
    phase = state.phase.get("current", "IDLE") if state and state.phase else "IDLE"
    runtime_profile = get_runtime_profile_summary(state)

    try:
        import workflow_engine

        plan_tasks, plan_source = workflow_engine.load_planning_tasks(workdir)
        next_tasks = workflow_engine.next_plan_tasks(workdir)
        frontier = workflow_engine.compute_frontier(workdir)
    except Exception:
        plan_tasks = []
        plan_source = "none"
        next_tasks = []
        frontier = {
            "executable_frontier": [],
            "parallel_candidates": [],
            "conflict_groups": [],
        }

    status_counts = {"backlog": 0, "in_progress": 0, "blocked": 0, "completed": 0}
    for task in plan_tasks:
        status = str(task.get("status", "backlog"))
        if status in status_counts:
            status_counts[status] += 1
        else:
            status_counts["backlog"] += 1

    ready_tasks = frontier.get("executable_frontier", [])
    parallel_groups = frontier.get("parallel_candidates", [])
    conflict_groups = frontier.get("conflict_groups", [])
    complexity = str(runtime_profile.get("complexity") or "UNKNOWN")
    total_tasks = len(plan_tasks)
    ready_count = len(ready_tasks)
    parallel_group_count = len(parallel_groups)
    parallel_ready_task_count = sum(len(group) for group in parallel_groups)
    conflict_group_count = len(conflict_groups)
    next_task_ids = [str(task.get("id", "")) for task in next_tasks[:3] if task.get("id")]
    if plan_source == "tasks.md":
        planning_mode = "canonical"
    elif plan_source == "task_plan.md":
        planning_mode = "legacy"
    else:
        planning_mode = "lightweight"

    worktree_recommended = False
    worktree_reason = "single-stream or no canonical planning chain"
    if plan_source != "none":
        multi_step = total_tasks >= 4 or ready_count > 1 or parallel_group_count > 0 or conflict_group_count > 0
        complex_enough = complexity in {"M", "L", "XL"}
        branch_point = phase in {"PLANNING", "EXECUTING", "DEBUGGING", "REVIEWING"}
        if multi_step and complex_enough and branch_point:
            worktree_recommended = True
            worktree_reason = (
                f"{complexity} task with {total_tasks} planned item(s) and "
                f"{ready_count} ready task(s); use a git worktree for isolation"
            )
        elif multi_step:
            worktree_reason = (
                f"multi-step plan detected ({total_tasks} tasks, {parallel_group_count} parallel group(s)); "
                f"consider a worktree when edits fan out"
            )
        else:
            worktree_reason = f"single-stream plan via {plan_source}"

    plan_digest = (
        f"{plan_source}: {total_tasks} task(s), "
        f"{status_counts['completed']} done, {status_counts['in_progress']} in progress, "
        f"{status_counts['blocked']} blocked, {ready_count} ready"
    )
    if next_task_ids:
        plan_digest += f"; next={', '.join(next_task_ids)}"
    if plan_source != "none":
        plan_digest += f"; worktree={'yes' if worktree_recommended else 'no'}"

    return {
        "plan_source": plan_source,
        "plan_task_count": total_tasks,
        "completed_task_count": status_counts["completed"],
        "in_progress_task_count": status_counts["in_progress"],
        "blocked_task_count": status_counts["blocked"],
        "backlog_task_count": status_counts["backlog"],
        "ready_task_count": ready_count,
        "parallel_candidate_group_count": parallel_group_count,
        "parallel_ready_task_count": parallel_ready_task_count,
        "conflict_group_count": conflict_group_count,
        "next_task_ids": next_task_ids,
        "planning_mode": planning_mode,
        "worktree_recommended": worktree_recommended,
        "worktree_reason": worktree_reason,
        "plan_digest": plan_digest,
    }


def get_thinking_summary(workdir: str, state: WorkflowState | None = None) -> dict[str, Any]:
    """Extract THINKING summary from session sidecar or current state."""
    session_state_path = Path(workdir) / "SESSION-STATE.md"
    summary = get_session_thinking_summary(str(session_state_path))
    if _is_meaningful_thinking_summary(summary):
        summary = dict(summary)
        if not str(summary.get("thinking_mode", "")).strip() or str(summary.get("thinking_mode", "")).strip() in {"(未设置)", "unset"}:
            workflow = str(summary.get("workflow", "")).strip()
            workflow_label = str(summary.get("workflow_label", "")).strip()
            if workflow == "workflow_1_new_project" or "新项目" in workflow_label:
                summary["thinking_mode"] = "investigation_first"
                summary.setdefault("thinking_methods", ["调查研究", "矛盾分析", "群众路线", "持久战略"])
            elif workflow == "workflow_3_iteration" or "迭代" in workflow_label:
                summary["thinking_mode"] = "mass_line_iteration"
                summary.setdefault("thinking_methods", ["群众路线", "矛盾分析", "实践认知", "批评自我批评"])
            elif workflow == "workflow_2_complex_problem" or "复杂" in workflow_label:
                summary["thinking_mode"] = "contradiction_analysis"
                summary.setdefault("thinking_methods", ["调查研究", "矛盾分析", "集中力量", "实践认知", "批评自我批评"])
        if not summary.get("thinking_methods"):
            workflow = str(summary.get("workflow", "")).strip()
            workflow_label = str(summary.get("workflow_label", "")).strip()
            if workflow == "workflow_1_new_project" or "新项目" in workflow_label:
                summary["thinking_methods"] = ["调查研究", "矛盾分析", "群众路线", "持久战略"]
            elif workflow == "workflow_3_iteration" or "迭代" in workflow_label:
                summary["thinking_methods"] = ["群众路线", "矛盾分析", "实践认知", "批评自我批评"]
            elif workflow == "workflow_2_complex_problem" or "复杂" in workflow_label:
                summary["thinking_methods"] = ["调查研究", "矛盾分析", "集中力量", "实践认知", "批评自我批评"]
        return summary

    return _build_thinking_summary_from_state(workdir, state)


def _build_thinking_summary_from_state(workdir: str, state: WorkflowState | None = None) -> dict[str, Any]:
    """Build the canonical THINKING summary without consulting the sidecar."""
    if state is None:
        state = load_state(workdir)
    if state is None:
        return {}

    current_phase = state.phase.get("current") if state.phase else "IDLE"
    if current_phase in {"COMPLETE", "failed", "aborted", "IDLE"} or not state.task:
        return {}

    try:
        from runtime_profile import build_thinking_summary

        runtime_profile = get_runtime_profile_summary(state)
        research_summary = get_research_summary(workdir, state)
        task_desc = state.task.description or state.task.title or ""
        complexity = runtime_profile.get("complexity")
        if not complexity and state.metadata:
            complexity = state.metadata.get("complexity")
        contract_summary: dict[str, Any] = {}
        try:
            from workflow_engine import parse_phase_contract

            contract_summary = parse_phase_contract(workdir)
        except Exception:
            contract_summary = {}
        summary = build_thinking_summary(
            task_desc,
            str(complexity or "M"),
            research_summary=research_summary,
            contract_summary=contract_summary,
        )
        if not summary.get("thinking_methods"):
            summary["thinking_methods"] = ["调查研究", "矛盾分析", "集中力量", "实践认知", "批评自我批评"]
        return summary
    except Exception:
        return {}


def _is_meaningful_thinking_summary(summary: dict[str, Any] | None) -> bool:
    """Return True only for a THINKING summary with actual content, not placeholders."""
    if not summary:
        return False
    workflow_label = str(summary.get("workflow_label", "")).strip()
    major_contradiction = str(summary.get("major_contradiction", "")).strip()
    local_attack_point = str(summary.get("local_attack_point", "")).strip()
    if workflow_label in {"", "(未设置)", "unset"}:
        return False
    if major_contradiction in {"", "(未设置)", "unset"}:
        return False
    if local_attack_point in {"", "(未设置)", "unset"}:
        return False
    return True


def _is_meaningful_research_summary(summary: dict[str, Any] | None) -> bool:
    """Return True only for a research summary with actual content."""
    if not summary:
        return False
    research_source = str(summary.get("research_source", "")).strip()
    research_path = str(summary.get("research_path", "")).strip()
    key_terms = str(summary.get("key_terms", "")).strip()
    if research_source in {"", "(未设置)", "unset"}:
        return False
    if research_path in {"", "(未设置)", "unset"}:
        return False
    if key_terms in {"", "(未设置)", "unset"}:
        return False
    return True


def get_failure_event_summary(state: WorkflowState | None) -> dict[str, Any]:
    """Summarize failure-related decisions for snapshot/debugging views."""
    if state is None:
        return {
            "failure_event_count": 0,
            "escalation_event_count": 0,
            "latest_failure_event": None,
            "latest_escalation_event": None,
            "error_types": [],
        }

    failure_events: list[dict[str, Any]] = []
    escalation_events: list[dict[str, Any]] = []

    for decision in state.decisions:
        metadata = decision.metadata if hasattr(decision, "metadata") and isinstance(decision.metadata, dict) else {}
        error_type = metadata.get("error_type")
        if not error_type and decision.decision != "Escalate skill activation":
            continue

        event = {
            "timestamp": decision.timestamp,
            "decision": decision.decision,
            "reason": decision.reason,
            "error_type": error_type,
            "retry_count": metadata.get("retry_count"),
        }
        failure_events.append(event)

        if decision.decision == "Escalate skill activation":
            event = dict(event)
            event["current_activation_level"] = metadata.get("current_activation_level")
            event["escalated_activation_level"] = metadata.get("escalated_activation_level")
            event["escalation_reason"] = metadata.get("escalation_reason")
            escalation_events.append(event)

    error_types = sorted(
        {
            str(event["error_type"])
            for event in failure_events
            if event.get("error_type")
        }
    )

    return {
        "failure_event_count": len(failure_events),
        "escalation_event_count": len(escalation_events),
        "latest_failure_event": failure_events[-1] if failure_events else None,
        "latest_escalation_event": escalation_events[-1] if escalation_events else None,
        "error_types": error_types,
    }


def get_review_summary(workdir: str, state: WorkflowState | None = None) -> dict[str, Any]:
    """Summarize the latest review artifact for completion gates and snapshots."""
    from review_paths import legacy_review_paths, review_latest_path

    review_candidates = [review_latest_path(workdir), *legacy_review_paths(workdir)]
    review_path: Path | None = None
    for candidate in review_candidates:
        if candidate.exists():
            review_path = candidate
            break

    if review_path is None:
        fallback = _build_review_state_fallback(state)
        if fallback:
            return fallback
        return {
            "review_found": False,
            "review_path": None,
            "review_source": "none",
            "review_status": "missing",
            "stage_1_status": "unknown",
            "stage_2_status": "unknown",
            "risk_level": None,
            "verdict": None,
            "degraded_mode": False,
            "files_reviewed": 0,
            "contract_alignment": None,
            "contract_files_count": 0,
            "reviewed_targets_count": 0,
            "matched_contract_files_count": 0,
        }

    try:
        content = review_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {
            "review_found": False,
            "review_path": str(review_path),
            "review_source": "unreadable",
            "review_status": "error",
            "stage_1_status": "unknown",
            "stage_2_status": "unknown",
            "risk_level": None,
            "verdict": None,
            "degraded_mode": False,
            "files_reviewed": 0,
            "contract_alignment": None,
            "contract_files_count": 0,
            "reviewed_targets_count": 0,
            "matched_contract_files_count": 0,
        }

    def _extract(pattern: str) -> str | None:
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        return match.group(1).strip() if match else None

    review_status = "reviewed" if "## Verdict" in content or "## Risk Level" in content else "unknown"
    stage_1_status = "reviewed" if "## Stage 1: Spec Compliance" in content else "missing"
    stage_2_status = "reviewed" if "## Stage 2: Code Quality" in content else "missing"
    risk_level = _extract(r"^\s*\*\*Overall\*\*:\s*(.+)$")
    verdict = _extract(r"^-\s*Status:\s*(.+)$")
    files_reviewed_str = _extract(r"^\s*\*\*Files Reviewed\*\*:\s*(\d+)\s*code files$")
    if not files_reviewed_str:
        files_reviewed_str = _extract(r"^## Reviewed Files \((\d+)\s*files analyzed\)$")
    files_reviewed = int(files_reviewed_str) if files_reviewed_str and files_reviewed_str.isdigit() else 0
    contract_alignment = _extract(r"^\s*-\s*Contract alignment:\s*(.+)$")
    contract_files_count_str = _extract(r"^\s*-\s*Contract files count:\s*(\d+)$")
    reviewed_targets_count_str = _extract(r"^\s*-\s*Reviewed targets count:\s*(\d+)$")
    matched_contract_files_count_str = _extract(r"^\s*-\s*Matched contract files:\s*(\d+)$")
    degraded_mode = "Degraded Mode" in content or "degraded mode" in content.lower()
    if review_status == "reviewed" and files_reviewed <= 0 and "template-based fallback" in content.lower():
        degraded_mode = True

    return {
        "review_found": True,
        "review_path": str(review_path),
        "review_source": "review_latest" if review_path.name == "review_latest.md" else "legacy_or_session",
        "review_status": review_status,
        "stage_1_status": stage_1_status,
        "stage_2_status": stage_2_status,
        "risk_level": risk_level,
        "verdict": verdict,
        "degraded_mode": degraded_mode,
        "files_reviewed": files_reviewed,
        "contract_alignment": contract_alignment,
        "contract_files_count": int(contract_files_count_str) if contract_files_count_str and contract_files_count_str.isdigit() else 0,
        "reviewed_targets_count": int(reviewed_targets_count_str) if reviewed_targets_count_str and reviewed_targets_count_str.isdigit() else 0,
        "matched_contract_files_count": int(matched_contract_files_count_str) if matched_contract_files_count_str and matched_contract_files_count_str.isdigit() else 0,
    }


def _build_review_state_fallback(state: WorkflowState | None) -> dict[str, Any]:
    """Build a minimal review summary from live state when no review artifact exists."""
    if state is None or state.phase.get("current") != "REVIEWING":
        return {}
    if not state.task:
        return {}

    reviewed_files = 0
    for file_change in getattr(state, "file_changes", []) or []:
        path = str(getattr(file_change, "path", ""))
        if Path(path).suffix in {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".c", ".cpp"}:
            reviewed_files += 1

    return {
        "review_found": False,
        "review_path": None,
        "review_source": "state_fallback",
        "review_status": "pending",
        "stage_1_status": "pending",
        "stage_2_status": "pending",
        "risk_level": None,
        "verdict": None,
        "degraded_mode": True,
        "files_reviewed": reviewed_files,
        "contract_alignment": "state_fallback",
        "contract_files_count": 0,
        "reviewed_targets_count": reviewed_files,
        "matched_contract_files_count": 0,
    }


def _compare_field(errors: list[str], section: str, field: str, expected: Any, actual: Any) -> None:
    def _normalize(value: Any) -> Any:
        if isinstance(value, str):
            normalized = value.strip()
            if normalized.lower() in {"", "none", "null", "unset", "(未设置)"}:
                return None
            return normalized
        return value

    if _normalize(expected) != _normalize(actual):
        errors.append(f"{section}.{field}: state={expected!r} sidecar={actual!r}")


def compare_state_sidecar_consistency(workdir: str = ".", state: WorkflowState | None = None) -> tuple[bool, list[str]]:
    """Compare canonical state summaries against SESSION-STATE sidecar summaries."""
    if state is None:
        state = load_state(workdir)
    if state is None:
        return False, ["state file does not exist"]

    session_path = Path(workdir) / "SESSION-STATE.md"
    sidecar_runtime = get_session_runtime_profile(str(session_path))
    sidecar_planning = get_session_planning_summary(str(session_path))
    sidecar_research = get_session_research_summary(str(session_path))
    sidecar_thinking = get_session_thinking_summary(str(session_path))
    sidecar_review = get_session_review_summary(str(session_path))

    state_runtime = get_runtime_profile_summary(state)
    state_planning = _build_planning_summary(workdir, state)
    state_research = _build_research_summary_from_state(workdir, state)
    state_thinking = _build_thinking_summary_from_state(workdir, state)
    state_review = get_review_summary(workdir, state)

    errors: list[str] = []
    current_phase = state.phase.get("current", "IDLE") if state.phase else "IDLE"

    runtime_fields = [
        "skill_policy",
        "use_skill",
        "skill_activation_level",
        "tokens_expected",
        "profile_source",
        "complexity",
        "complexity_confidence",
    ]
    planning_fields = [
        "plan_source",
        "planning_mode",
        "plan_task_count",
        "completed_task_count",
        "in_progress_task_count",
        "blocked_task_count",
        "ready_task_count",
        "parallel_candidate_group_count",
        "parallel_ready_task_count",
        "conflict_group_count",
        "worktree_recommended",
        "worktree_reason",
        "plan_digest",
    ]
    research_fields = [
        "research_found",
        "research_source",
        "research_path",
        "key_terms",
        "search_engine",
        "sources_count",
        "used_real_search",
        "degraded_mode",
        "degraded_reason",
        "search_error",
        "evidence_status",
        "evidence_tier",
        "source_confidence",
        "source_types",
        "coverage_scope",
        "freshness",
    ]
    thinking_fields = [
        "workflow_label",
        "workflow",
        "thinking_mode",
        "thinking_methods",
        "major_contradiction",
        "stage_judgment",
        "local_attack_point",
        "recommendation",
        "memory_hints_count",
        "research_inputs",
        "memory_inputs",
        "contract_inputs",
        "reasoning_trace_id",
        "confidence_level",
    ]
    review_fields = [
        "review_found",
        "review_source",
        "review_status",
        "stage_1_status",
        "stage_2_status",
        "risk_level",
        "verdict",
        "degraded_mode",
        "files_reviewed",
        "contract_alignment",
        "contract_files_count",
        "reviewed_targets_count",
        "matched_contract_files_count",
    ]

    for field in runtime_fields:
        _compare_field(errors, "runtime_profile", field, state_runtime.get(field), sidecar_runtime.get(field))
    for field in planning_fields:
        _compare_field(errors, "planning_summary", field, state_planning.get(field), sidecar_planning.get(field))
    state_has_research = _is_meaningful_research_summary(state_research)
    if current_phase == "RESEARCH" and state_has_research:
        for field in research_fields:
            _compare_field(errors, "research_summary", field, state_research.get(field), sidecar_research.get(field))
    state_has_thinking = _is_meaningful_thinking_summary(state_thinking)
    if current_phase == "THINKING" and state_has_thinking:
        for field in thinking_fields:
            _compare_field(errors, "thinking_summary", field, state_thinking.get(field), sidecar_thinking.get(field))
    state_has_review = bool(state_review.get("review_found")) and str(state_review.get("review_source", "")).strip() not in {"", "none", "template"}
    if current_phase == "REVIEWING" and state_has_review:
        for field in review_fields:
            _compare_field(errors, "review_summary", field, state_review.get(field), sidecar_review.get(field))

    return len(errors) == 0, errors


# ============================================================================
# Phase Transitions
# ============================================================================

TRANSITIONS = {
    "IDLE": {"DIRECT_ANSWER", "SUBAGENT", "PLANNING", "ANALYZING", "RESEARCH", "THINKING", "EXECUTING", "REVIEWING", "DEBUGGING", "REFINING", "EXPLORING", "OFFICE_HOURS"},
    "DIRECT_ANSWER": {"COMPLETE"},
    "SUBAGENT": {"COMPLETE"},
    "PLANNING": {"ANALYZING", "RESEARCH", "THINKING", "EXECUTING", "REVIEWING", "REFINING", "COMPLETE"},
    "ANALYZING": {"EXECUTING", "PLANNING", "COMPLETE"},
    "RESEARCH": {"THINKING", "PLANNING", "EXECUTING", "COMPLETE"},
    "THINKING": {"PLANNING", "EXECUTING", "REVIEWING", "REFINING", "COMPLETE"},
    "EXECUTING": {"REVIEWING", "DEBUGGING", "REFINING", "COMPLETE"},
    "REVIEWING": {"DEBUGGING", "COMPLETE", "EXECUTING", "REFINING"},
    "DEBUGGING": {"EXECUTING", "REVIEWING", "COMPLETE"},
    "REFINING": {"EXECUTING", "REVIEWING", "COMPLETE"},
    "EXPLORING": {"PLANNING", "RESEARCH", "THINKING", "EXECUTING", "REVIEWING", "COMPLETE"},
    "OFFICE_HOURS": {"PLANNING", "EXECUTING", "COMPLETE"},
    "COMPLETE": set(),
}


def can_transition(from_phase: str, to_phase: str) -> bool:
    """检查是否可以从from_phase转换到to_phase"""
    return to_phase in TRANSITIONS.get(from_phase, set())


def get_allowed_transitions(phase: str) -> list[str]:
    """获取允许的下一个phase列表"""
    return sorted(TRANSITIONS.get(phase, set()))


def transition_phase(
    state: WorkflowState,
    new_phase: str,
    reason: str = "",
    actions: list[dict[str, Any]] | None = None,
    error: str | None = None,
) -> WorkflowState:
    """
    执行phase转换

    Args:
        state: 当前状态
        new_phase: 目标phase
        reason: 转换原因
        actions: 执行的动作列表
        error: 错误信息（如果有）

    Returns:
        更新后的状态副本
    """
    current_phase = state.phase.get("current", "IDLE")

    if not can_transition(current_phase, new_phase):
        raise ValueError(f"illegal phase transition: {current_phase} -> {new_phase}")

    # 更新history
    now = datetime.now().isoformat()
    history = state.phase.get("history", [])

    # 退出当前phase
    if history:
        history[-1]["exited_at"] = now

    # 添加新phase entry
    new_entry = PhaseEntry(
        phase=new_phase,
        entered_at=now,
        reason=reason,
        actions=actions or [],
    )
    if error:
        new_entry.error = error

    history.append(new_entry.to_dict())

    # 更新current
    new_state = WorkflowState.from_dict(state.to_dict())
    new_state.phase = {
        "current": new_phase,
        "history": history,
        "entered_at": now,
    }

    # 添加决策记录
    new_state.decisions.append(Decision(
        timestamp=now,
        decision=f"Transition: {current_phase} -> {new_phase}",
        reason=reason,
    ))

    return new_state


# ============================================================================
# Task Management
# ============================================================================


def update_task_status(
    state: WorkflowState,
    task_id: str,
    status: str,
    progress: int | None = None,
) -> WorkflowState:
    """更新任务状态"""
    if state.task and state.task.task_id == task_id:
        new_state = WorkflowState.from_dict(state.to_dict())
        task = cast(Task, new_state.task)
        task.status = status
        if progress is not None:
            task.progress = progress
        if status == "completed":
            task.completed_at = datetime.now().isoformat()
        return new_state

    # 如果不匹配，尝试在tasks列表中查找
    raise ValueError(f"task {task_id} not found in state")


def add_file_change(
    state: WorkflowState,
    file_path: str,
    action: str,
) -> WorkflowState:
    """添加文件变更记录"""
    new_state = WorkflowState.from_dict(state.to_dict())
    new_state.file_changes.append(FileChange(
        path=file_path,
        action=action,
        timestamp=datetime.now().isoformat(),
    ))
    return new_state


# ============================================================================
# Trajectory Management
# ============================================================================


def _get_trajectory_path(workdir: str, run_id: str) -> Path:
    """获取轨迹文件路径"""
    date_dir = trajectory_dir_path(workdir) / run_id[:8]  # YYYYMMDD
    date_dir.mkdir(parents=True, exist_ok=True)
    return date_dir / f"{run_id}.json"


def save_trajectory(workdir: str, trajectory: Trajectory) -> Path:
    """保存轨迹"""
    path = _get_trajectory_path(workdir, trajectory.run_id)
    safe_write_json_locked(path, trajectory)

    return path


def load_trajectory(workdir: str, run_id: str) -> Trajectory | None:
    """加载轨迹"""
    path = _get_trajectory_path(workdir, run_id)
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return Trajectory.from_dict(data)


def list_trajectories(workdir: str, date: str | None = None) -> list[str]:
    """
    列出轨迹

    Args:
        workdir: 工作目录
        date: 可选的日期过滤 (YYYYMMDD格式)

    Returns:
        run_id列表
    """
    base = trajectory_dir_path(workdir)

    if date:
        base = base / date
        if not base.exists():
            return []

    if not base.exists():
        return []

    run_ids = []
    for path in base.glob("*.json"):
        run_ids.append(path.stem)

    return sorted(run_ids, reverse=True)


def create_trajectory(
    run_id: str,
    session_id: str,
    prompt: str,
    trigger_type: str,
) -> Trajectory:
    """创建新轨迹"""
    return Trajectory(
        run_id=run_id,
        session_id=session_id,
        prompt=prompt,
        trigger_type=trigger_type,
        created_at=datetime.now().isoformat(),
        final_state="running",
    )


def append_trajectory_phase(
    trajectory: Trajectory,
    phase: str,
    actions: list[dict[str, Any]] | None = None,
    decisions: list[dict[str, str]] | None = None,
    file_changes: list[dict[str, str]] | None = None,
) -> Trajectory:
    """追加phase到轨迹"""
    new_trajectory = Trajectory.from_dict(trajectory.to_dict())
    new_trajectory.phases.append(TrajectoryPhase(
        phase=phase,
        entered_at=datetime.now().isoformat(),
        actions=actions or [],
        decisions=decisions or [],
        file_changes=file_changes or [],
    ))
    return new_trajectory


def complete_trajectory(
    trajectory: Trajectory,
    final_state: str = "completed",
    failure_reason: str | None = None,
) -> Trajectory:
    """完成轨迹"""
    new_trajectory = Trajectory.from_dict(trajectory.to_dict())
    new_trajectory.completed_at = datetime.now().isoformat()
    new_trajectory.final_state = final_state
    new_trajectory.failure_reason = failure_reason
    return new_trajectory


# ============================================================================
# Snapshot & Resume
# ============================================================================


def get_state_snapshot(workdir: str = ".") -> dict[str, Any]:
    """
    获取状态快照

    Returns:
        包含状态、任务、验证结果的字典
    """
    state = load_state(workdir)
    if state is None:
        return {
            "exists": False,
            "valid": False,
            "errors": ["state file does not exist"],
            "runtime_profile_summary": get_runtime_profile_summary(None),
            "planning_summary": get_planning_summary(workdir, None),
            "research_summary": get_research_summary(workdir, None),
            "thinking_summary": get_thinking_summary(workdir, None),
            "review_summary": get_review_summary(workdir, None),
            "failure_event_summary": get_failure_event_summary(None),
        }

    is_valid, errors = validate_workflow_state(workdir)

    return {
        "exists": True,
        "valid": is_valid,
        "errors": errors,
        "state": state.to_dict(),
        "current_phase": state.phase.get("current", "IDLE"),
        "session_id": state.session_id,
        "task_id": state.task.task_id if state.task else None,
        "allowed_transitions": get_allowed_transitions(state.phase.get("current", "IDLE")),
        "runtime_profile_summary": get_runtime_profile_summary(state),
        "planning_summary": get_planning_summary(workdir, state),
        "research_summary": get_research_summary(workdir, state),
        "thinking_summary": get_thinking_summary(workdir, state),
        "review_summary": get_review_summary(workdir, state),
        "failure_event_summary": get_failure_event_summary(state),
    }


def get_last_resume_point(workdir: str = ".") -> dict[str, Any] | None:
    """
    从轨迹中获取最后可恢复点

    Returns:
        包含phase、actions、状态的字典，如果无可恢复点返回None
    """
    state = load_state(workdir)
    if state is None:
        return None

    # 找到最后一个completed或failed的phase
    history = state.phase.get("history", [])
    if not history:
        return None

    last_entry = history[-1]
    current_phase = state.phase.get("current", "IDLE")

    return {
        "phase": current_phase,
        "last_completed_phase": last_entry.get("phase"),
        "session_id": state.session_id,
        "task_id": state.task.task_id if state.task else None,
        "state": state.to_dict(),
    }


# ============================================================================
# CLI Entry Point
# ============================================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Unified State Management")
    parser.add_argument("--workdir", default=".", help="workspace directory")
    parser.add_argument("--op", choices=["init", "load", "save", "validate", "compare-sidecar", "snapshot", "list-trajectories"], required=True)
    parser.add_argument("--prompt", help="user prompt for init")
    parser.add_argument("--task-id", help="optional task id for init")
    parser.add_argument("--trigger-type", default="FULL_WORKFLOW", help="trigger type")
    parser.add_argument("--phase", help="target phase")
    parser.add_argument("--run-id", help="run id for trajectory operations")
    parser.add_argument("--date", help="date filter for list-trajectories (YYYYMMDD)")
    args = parser.parse_args()

    if args.op == "init":
        if not args.prompt:
            print("错误: --prompt required for init")
            return 1

        state = create_initial_state(
            args.prompt,
            task_id=args.task_id,
            trigger_type=args.trigger_type,
            initial_phase=args.phase or "PLANNING",
        )
        path = save_state(args.workdir, state)
        print(f"Created: {path}")
        print(json.dumps(state.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.op == "load":
        state = load_state(args.workdir)
        if state is None:
            print("No state file found")
            return 1
        print(json.dumps(state.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.op == "validate":
        is_valid, errors = validate_workflow_state(args.workdir)
        print(json.dumps({"valid": is_valid, "errors": errors}, ensure_ascii=False, indent=2))
        return 0

    if args.op == "compare-sidecar":
        is_aligned, errors = compare_state_sidecar_consistency(args.workdir)
        print(json.dumps({"aligned": is_aligned, "errors": errors}, ensure_ascii=False, indent=2))
        return 0

    if args.op == "snapshot":
        print(json.dumps(get_state_snapshot(args.workdir), ensure_ascii=False, indent=2))
        return 0

    if args.op == "list-trajectories":
        trajectories = list_trajectories(args.workdir, args.date)
        print(json.dumps({"trajectories": trajectories}, ensure_ascii=False, indent=2))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
