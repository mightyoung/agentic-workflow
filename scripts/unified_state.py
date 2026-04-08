#!/usr/bin/env python3
"""
Unified State Management

Manages workflow state based on the unified schema defined in state_schema.py.
Provides a single source of truth, reducing fragility from markdown parsing.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

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
    }


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
    parser.add_argument("--op", choices=["init", "load", "save", "validate", "snapshot", "list-trajectories"], required=True)
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
