#!/usr/bin/env python3
"""
Trajectory Logger - 轨迹记录器

实现真正的执行轨迹持久化：
- 单run的统一日志
- phase切换、决策、文件变更、失败原因统一写入
- 支持断点恢复和事后分析

轨迹存储结构:
./trajectories/{date}/{session_id}/
  trajectory.json      # 主轨迹文件
  decisions.jsonl      # 决策审计日志
  file_changes.jsonl   # 文件修改日志
  errors.jsonl         # 错误日志
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

from safe_io import safe_write_json_locked

TRAJECTORY_DIR = "trajectories"


def trajectory_base_path(workdir: str = ".") -> Path:
    """获取轨迹根目录"""
    return Path(workdir) / TRAJECTORY_DIR


def trajectory_date_dir(workdir: str, session_id: str) -> Path:
    """获取特定日期的轨迹目录"""
    # session_id格式: sYYYYMMDDHHMMSS
    date_part = session_id[1:] if session_id.startswith("s") else session_id[:8]
    return trajectory_base_path(workdir) / date_part / session_id


@dataclass
class PhaseRecord:
    """Phase执行记录"""
    phase: str
    entered_at: str
    exited_at: str | None = None
    actions: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, str]] = field(default_factory=list)
    file_changes: list[dict[str, str]] = field(default_factory=list)
    error: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionRecord:
    """决策记录"""
    timestamp: str
    decision: str
    reason: str = ""
    phase: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "decision": self.decision,
            "reason": self.reason,
            "phase": self.phase,
            **self.metadata,
        }

    def to_jsonl(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class FileChangeRecord:
    """文件变更记录"""
    timestamp: str
    path: str
    action: str  # create, modify, delete
    phase: str = ""
    size: int | None = None
    checksum: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "path": self.path,
            "action": self.action,
            "phase": self.phase,
            "size": self.size,
            "error": self.error,
        }

    def to_jsonl(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class ErrorRecord:
    """错误记录"""
    timestamp: str
    error: str
    phase: str = ""
    stack_trace: str | None = None
    recoverable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "error": self.error,
            "phase": self.phase,
            "stack_trace": self.stack_trace,
            "recoverable": self.recoverable,
            **self.metadata,
        }

    def to_jsonl(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class Trajectory:
    """完整轨迹"""
    run_id: str
    session_id: str
    created_at: str
    prompt: str = ""
    trigger_type: str = ""
    runtime_profile: dict[str, Any] = field(default_factory=dict)
    current_phase: str = "IDLE"
    phases: list[PhaseRecord] = field(default_factory=list)
    resume_summary: dict[str, Any] = field(default_factory=dict)
    final_state: str = "running"  # running, completed, failed, aborted
    failure_reason: str | None = None
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "prompt": self.prompt,
            "trigger_type": self.trigger_type,
            "runtime_profile": self.runtime_profile,
            "current_phase": self.current_phase,
            "phases": [p.to_dict() for p in self.phases],
            "resume_summary": self.resume_summary,
            "final_state": self.final_state,
            "failure_reason": self.failure_reason,
            "completed_at": self.completed_at,
        }


class TrajectoryLogger:
    """
    轨迹记录器

    用法:
        logger = TrajectoryLogger(workdir, session_id)
        logger.start(prompt, trigger_type)

        logger.enter_phase("PLANNING")
        logger.log_decision("Split into 3 tasks", "Independent modules")
        logger.log_file_change("task_plan.md", "create")
        logger.exit_phase("PLANNING")

        logger.enter_phase("EXECUTING")
        ...
        logger.complete("completed")
    """

    def __init__(self, workdir: str = ".", session_id: str | None = None):
        self.workdir = workdir
        self.session_id = session_id or f"s{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.base_dir = trajectory_date_dir(workdir, self.session_id)
        self._current_phase: str | None = None
        self._phase_start: str | None = None
        self._current_actions: list[dict[str, Any]] = []
        self._current_decisions: list[dict[str, str]] = []
        self._current_file_changes: list[dict[str, str]] = []
        self._current_error: str | None = None

        # 主轨迹文件
        self._trajectory_file: Path | None = None
        # JSONL文件句柄
        self._decisions_file: TextIO | None = None
        self._file_changes_file: TextIO | None = None
        self._errors_file: TextIO | None = None

        # 元数据
        self._prompt: str = ""
        self._trigger_type: str = ""
        self._run_id: str = f"R{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self._runtime_profile: dict[str, Any] = {}

    def _ensure_dirs(self):
        """确保目录存在"""
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def start(
        self,
        prompt: str,
        trigger_type: str,
        runtime_profile: dict[str, Any] | None = None,
        resume_summary: dict[str, Any] | None = None,
    ) -> str:
        """
        开始轨迹记录

        Returns:
            run_id
        """
        self._ensure_dirs()
        self._prompt = prompt
        self._trigger_type = trigger_type
        self._runtime_profile = runtime_profile or {}

        # 创建主轨迹文件
        self._trajectory_file = self.base_dir / "trajectory.json"

        # 创建JSONL文件
        decisions_path = self.base_dir / "decisions.jsonl"
        file_changes_path = self.base_dir / "file_changes.jsonl"
        errors_path = self.base_dir / "errors.jsonl"

        self._decisions_file = decisions_path.open("a", encoding="utf-8")
        self._file_changes_file = file_changes_path.open("a", encoding="utf-8")
        self._errors_file = errors_path.open("a", encoding="utf-8")

        # 保存初始轨迹
        trajectory = Trajectory(
            run_id=self._run_id,
            session_id=self.session_id,
            created_at=datetime.now().isoformat(),
            prompt=prompt,
            trigger_type=trigger_type,
            runtime_profile=self._runtime_profile,
            current_phase="IDLE",
            resume_summary=resume_summary or {},
        )

        self._save_trajectory(trajectory)

        return self._run_id

    def enter_phase(self, phase: str, actions: list[dict[str, Any]] | None = None):
        """进入新phase"""
        # 退出当前phase
        if self._current_phase:
            self.exit_phase(self._current_phase)

        self._current_phase = phase
        self._phase_start = datetime.now().isoformat()
        self._current_actions = actions or []
        self._current_decisions = []
        self._current_file_changes = []
        self._current_error = None

        # 更新trajectory文件中的current_phase
        if self._trajectory_file and self._trajectory_file.exists():
            try:
                data = json.loads(self._trajectory_file.read_text(encoding="utf-8"))
                data["current_phase"] = phase
                safe_write_json_locked(self._trajectory_file, data)
            except (OSError, json.JSONDecodeError):
                pass

    def exit_phase(self, phase: str, error: str | None = None):
        """退出phase"""
        if self._current_phase != phase:
            # 忽略不匹配的退出
            return

        exited_at = datetime.now().isoformat()

        # 记录phase
        phase_record = PhaseRecord(
            phase=phase,
            entered_at=self._phase_start or exited_at,
            exited_at=exited_at,
            actions=self._current_actions.copy(),
            decisions=self._current_decisions.copy(),
            file_changes=self._current_file_changes.copy(),
            error=error,
        )

        # 更新轨迹文件
        self._update_trajectory_phases(phase_record)

        # 追加到JSONL文件
        if self._decisions_file:
            for decision in self._current_decisions:
                decision_rec = DecisionRecord(
                    timestamp=exited_at,
                    decision=decision["decision"],
                    reason=decision.get("reason", ""),
                    phase=phase,
                )
                self._decisions_file.write(decision_rec.to_jsonl() + "\n")

        if self._file_changes_file:
            for fc in self._current_file_changes:
                fc_rec = FileChangeRecord(
                    timestamp=exited_at,
                    path=fc["path"],
                    action=fc["action"],
                    phase=phase,
                )
                self._file_changes_file.write(fc_rec.to_jsonl() + "\n")

        if error and self._errors_file:
            err_rec = ErrorRecord(
                timestamp=exited_at,
                error=error,
                phase=phase,
            )
            self._errors_file.write(err_rec.to_jsonl() + "\n")

        # 重置状态
        self._current_phase = None
        self._phase_start = None

    def log_decision(self, decision: str, reason: str = "", **metadata):
        """记录决策"""
        self._current_decisions.append({
            "decision": decision,
            "reason": reason,
            **metadata,
        })

    def log_file_change(self, path: str, action: str):
        """记录文件变更"""
        self._current_file_changes.append({
            "path": path,
            "action": action,
            "timestamp": datetime.now().isoformat(),
        })

    def log_error(self, error: str, recoverable: bool = False, stack_trace: str | None = None):
        """记录错误"""
        self._current_error = error

        if self._errors_file:
            err_rec = ErrorRecord(
                timestamp=datetime.now().isoformat(),
                error=error,
                phase=self._current_phase or "",
                recoverable=recoverable,
                stack_trace=stack_trace,
            )
            self._errors_file.write(err_rec.to_jsonl() + "\n")

    def log_action(self, action: dict[str, Any]):
        """记录动作"""
        self._current_actions.append({
            **action,
            "timestamp": datetime.now().isoformat(),
        })

    def complete(self, final_state: str = "completed", failure_reason: str | None = None):
        """完成轨迹"""
        # 如果还在某个phase中，先退出
        if self._current_phase:
            self.exit_phase(self._current_phase, error=failure_reason if final_state == "failed" else None)

        now = datetime.now().isoformat()

        # 更新轨迹文件
        trajectory = Trajectory(
            run_id=self._run_id,
            session_id=self.session_id,
            created_at=now,
            prompt=self._prompt,
            trigger_type=self._trigger_type,
            runtime_profile=self._runtime_profile,
            current_phase=self._current_phase or "COMPLETE",
            phases=self._load_phases(),
            final_state=final_state,
            failure_reason=failure_reason,
            completed_at=now,
        )

        self._save_trajectory(trajectory)

        # 关闭文件句柄
        self._close_files()

    def flush(self) -> dict[str, Any]:
        """
        Flush current trajectory state to disk.

        Returns:
            Summary of flushed state
        """
        # Load and re-save full trajectory
        phases = self._load_phases()
        trajectory = Trajectory(
            run_id=self._run_id,
            session_id=self.session_id,
            created_at=self._prompt[:50] if self._prompt else "",
            prompt=self._prompt,
            trigger_type=self._trigger_type,
            current_phase=self._current_phase or "UNKNOWN",
            phases=phases,
            final_state="running",
        )
        self._save_trajectory(trajectory)

        return {
            "session_id": self.session_id,
            "current_phase": self._current_phase,
            "phase_count": len(phases),
        }

    def _close_files(self):
        """关闭所有文件句柄"""
        if self._decisions_file:
            self._decisions_file.close()
        if self._file_changes_file:
            self._file_changes_file.close()
        if self._errors_file:
            self._errors_file.close()

    def _load_phases(self) -> list[PhaseRecord]:
        """从轨迹文件加载phases"""
        if not self._trajectory_file or not self._trajectory_file.exists():
            return []

        try:
            data = json.loads(self._trajectory_file.read_text(encoding="utf-8"))
            return [PhaseRecord(**p) for p in data.get("phases", [])]
        except (json.JSONDecodeError, TypeError):
            return []

    def _update_trajectory_phases(self, new_phase: PhaseRecord):
        """更新轨迹文件中的phases"""
        if not self._trajectory_file:
            return
        phases = self._load_phases()
        phases.append(new_phase)

        # 读取现有轨迹更新
        try:
            existing = {}
            if self._trajectory_file.exists():
                existing = json.loads(self._trajectory_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, TypeError):
            existing = {}

        existing["phases"] = [p.to_dict() for p in phases]
        existing["current_phase"] = new_phase.phase

        safe_write_json_locked(self._trajectory_file, existing)

    def _save_trajectory(self, trajectory: Trajectory):
        """保存完整轨迹"""
        if not self._trajectory_file:
            return
        safe_write_json_locked(self._trajectory_file, trajectory.to_dict())

    def get_summary(self) -> dict[str, Any]:
        """获取轨迹摘要"""
        phases = self._load_phases()

        total_duration = 0.0
        phase_durations = {}
        for p in phases:
            if p.exited_at and p.entered_at:
                start = datetime.fromisoformat(p.entered_at)
                end = datetime.fromisoformat(p.exited_at)
                duration = (end - start).total_seconds()
                phase_durations[p.phase] = duration
                total_duration += duration

        return {
            "run_id": self._run_id,
            "session_id": self.session_id,
            "phase_count": len(phases),
            "total_duration_seconds": total_duration,
            "phase_durations": phase_durations,
            "final_state": "completed" if not phases[-1].error else "failed" if phases[-1].error else "unknown",
        }


# ============================================================================
# Trajectory Analysis & Resume
# ============================================================================


def load_trajectory(workdir: str, session_id: str) -> dict[str, Any] | None:
    """加载轨迹"""
    base_dir = trajectory_date_dir(workdir, session_id)
    trajectory_file = base_dir / "trajectory.json"

    if not trajectory_file.exists():
        return None

    try:
        data = json.loads(trajectory_file.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        return None
    except (json.JSONDecodeError, TypeError):
        return None


def _build_resume_summary(
    original_session_id: str,
    original_trajectory: dict[str, Any],
    resume_from: str,
    next_phase: str | None,
    research_summary: dict[str, Any] | None = None,
    planning_summary: dict[str, Any] | None = None,
    review_summary: dict[str, Any] | None = None,
    debug_summary: dict[str, Any] | None = None,
    thinking_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构建恢复摘要，写入恢复轨迹根节点。"""
    phases = original_trajectory.get("phases", [])
    errored_phases: list[dict[str, Any]] = []
    for phase in phases:
        error = phase.get("error")
        if error:
            errored_phases.append(
                {
                    "phase": phase.get("phase", ""),
                    "error": error,
                    "entered_at": phase.get("entered_at"),
                    "exited_at": phase.get("exited_at"),
                }
            )

    latest_error = errored_phases[-1] if errored_phases else None
    runtime_profile = original_trajectory.get("runtime_profile", {})
    research_summary = research_summary or {}
    planning_summary = planning_summary or {}
    review_summary = review_summary or {}
    debug_summary = debug_summary or {}
    thinking_summary = thinking_summary or {}
    return {
        "original_session_id": original_session_id,
        "original_run_id": original_trajectory.get("run_id", ""),
        "original_trigger_type": original_trajectory.get("trigger_type", ""),
        "original_current_phase": original_trajectory.get("current_phase", "IDLE"),
        "resume_from": resume_from,
        "next_phase": next_phase,
        "runtime_profile": runtime_profile,
        "research_summary": research_summary,
        "planning_summary": planning_summary,
        "review_summary": review_summary,
        "debug_summary": debug_summary,
        "thinking_summary": thinking_summary,
        "phase_count": len(phases),
        "errored_phase_count": len(errored_phases),
        "latest_errored_phase": latest_error,
    }


def save_trajectory(workdir: str, trajectory: Trajectory) -> Path:
    """保存轨迹"""
    base_dir = trajectory_date_dir(workdir, trajectory.session_id)
    base_dir.mkdir(parents=True, exist_ok=True)
    trajectory_file = base_dir / "trajectory.json"
    safe_write_json_locked(trajectory_file, trajectory.to_dict())
    return trajectory_file


def list_trajectories(workdir: str, date: str | None = None) -> list[dict[str, Any]]:
    """
    列出所有轨迹

    Args:
        workdir: 工作目录
        date: 可选的日期过滤 (YYYYMMDD格式)

    Returns:
        轨迹摘要列表
    """
    base = trajectory_base_path(workdir)

    if date:
        base = base / date
        if not base.exists():
            return []

    if not base.exists():
        return []

    trajectories = []
    for session_dir in base.rglob("*"):
        if not session_dir.is_dir():
            continue

        trajectory_file = session_dir / "trajectory.json"
        if not trajectory_file.exists():
            continue

        try:
            data = json.loads(trajectory_file.read_text(encoding="utf-8"))
            trajectories.append({
                "session_id": data.get("session_id"),
                "run_id": data.get("run_id"),
                "created_at": data.get("created_at"),
                "completed_at": data.get("completed_at"),
                "final_state": data.get("final_state"),
                "phase_count": len(data.get("phases", [])),
                "prompt": data.get("prompt", "")[:100],
            })
        except (json.JSONDecodeError, TypeError):
            continue

    return sorted(trajectories, key=lambda x: x.get("created_at", ""), reverse=True)


def get_resume_point(workdir: str, session_id: str) -> dict[str, Any] | None:
    """
    获取恢复点

    Returns:
        包含phase、actions、state的字典
    """
    trajectory = load_trajectory(workdir, session_id)
    if not trajectory:
        return None

    phases = trajectory.get("phases", [])
    if not phases:
        return None

    last_phase = phases[-1]
    current_phase = trajectory.get("current_phase", "IDLE")

    # 检查是否可以恢复
    can_resume = current_phase not in ("COMPLETE", "failed", "aborted")

    return {
        "session_id": session_id,
        "run_id": trajectory.get("run_id"),
        "current_phase": current_phase,
        "last_completed_phase": last_phase.get("phase"),
        "can_resume": can_resume,
        "last_actions": last_phase.get("actions", []),
        "last_error": last_phase.get("error"),
        "trajectory": trajectory,
    }


def resume_from_point(workdir: str, session_id: str, resume_phase: str | None = None) -> dict[str, Any] | None:
    """
    从恢复点继续工作流

    Args:
        workdir: 工作目录
        session_id: 要恢复的session ID
        resume_phase: 可选的指定恢复phase，默认从last completed phase继续

    Returns:
        恢复结果包含:
        - session_id: 新的session ID
        - resume_from: 从哪个phase恢复
        - next_phase: 建议的下一个phase
        - trajectory: 新创建的恢复trajectory
    """
    # 获取原始trajectory
    original_trajectory = load_trajectory(workdir, session_id)
    if not original_trajectory:
        return None

    thinking_summary: dict[str, Any] = {}
    research_summary: dict[str, Any] = {}
    planning_summary: dict[str, Any] = {}
    review_summary: dict[str, Any] = {}
    debug_summary: dict[str, Any] = {}
    try:
        from memory_ops import get_planning_summary, get_research_summary, get_review_summary
        from unified_state import get_debug_summary as get_state_debug_summary, get_thinking_summary as get_state_thinking_summary, load_state

        session_state = str(Path(workdir) / "SESSION-STATE.md")
        planning_summary = get_planning_summary(session_state)
        research_summary = get_research_summary(session_state)
        review_summary = get_review_summary(session_state)
        debug_summary = get_state_debug_summary(workdir, load_state(workdir))
        thinking_summary = get_state_thinking_summary(workdir, load_state(workdir))
    except Exception:
        thinking_summary = {}
        research_summary = {}
        planning_summary = {}
        review_summary = {}
        debug_summary = {}

    if not planning_summary:
        try:
            from unified_state import get_planning_summary as get_state_planning_summary, get_research_summary as get_state_research_summary, load_state

            planning_state = load_state(workdir)
            planning_summary = get_state_planning_summary(workdir, planning_state)
            research_summary = get_state_research_summary(workdir, planning_state)
        except Exception:
            planning_summary = {}
            research_summary = {}

    if not review_summary:
        try:
            from unified_state import get_review_summary as get_state_review_summary, load_state

            review_state = load_state(workdir)
            review_summary = get_state_review_summary(workdir, review_state)
        except Exception:
            review_summary = {}

    if not research_summary:
        try:
            from unified_state import get_research_summary as get_state_research_summary, load_state

            research_state = load_state(workdir)
            research_summary = get_state_research_summary(workdir, research_state)
        except Exception:
            research_summary = {}

    if not debug_summary:
        debug_summary = {
            "debug_found": False,
            "debug_source": "state_fallback",
            "strategy": "debugging" if original_trajectory.get("current_phase") in {"EXECUTING", "REVIEWING", "DEBUGGING"} else "retry",
            "error_type": "unknown",
            "retry_count": 0,
            "activation_level": 0,
            "escalation_reason": None,
            "root_cause": None,
            "minimal_fix": "inspect the failure and retry with tighter scope",
            "regression_check": "rerun affected tests and quality gate",
            "reflection_path": None,
            "quality_gate_failed": False,
        }

    # 获取当前活跃phase
    original_phase = original_trajectory.get("current_phase", "IDLE")

    # 获取最后一个completed的phase
    phases = original_trajectory.get("phases", [])

    # 如果从未退出任何phase（phases为空），但有current_phase，可以从current_phase恢复
    if not phases:
        if original_phase not in ("COMPLETE", "failed", "aborted", "IDLE"):
            next_phase = _get_next_phase_after(original_phase, original_phase)
            resume_summary = _build_resume_summary(
                session_id,
                original_trajectory,
                original_phase,
                next_phase,
                research_summary=research_summary,
                planning_summary=planning_summary,
                review_summary=review_summary,
                debug_summary=debug_summary,
                thinking_summary=thinking_summary,
            )
            resume_summary["debug_summary"] = debug_summary
            return {
                "session_id": f"r{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "run_id": f"R{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "original_session_id": session_id,
                "resume_from": original_phase,
                "next_phase": next_phase,
                "can_resume": True,
                "original_trajectory": original_trajectory,
                "resume_summary": resume_summary,
                "resumed_trajectory": None,
            }
        return None

    # 找到可以恢复的点

    # 找到可以恢复的点
    last_completed = None
    for phase_record in reversed(phases):
        if phase_record.get("exited_at"):  # 有退出时间的才是completed
            last_completed = phase_record
            break

    # 处理"未完成首phase"的session：所有phase都没有exited_at
    # 这种情况下，当前的phase就是要恢复的点
    if not last_completed:
        # 所有phase都还没有退出，使用current_phase作为resume_from
        resume_from = resume_phase or original_phase
    else:
        # 有已完成的phase，检查是否需要恢复当前活跃phase
        last_completed_phase = last_completed.get("phase")
        if last_completed_phase != original_phase:
            # current_phase不同于last_completed，说明当前phase还未退出
            # 应该从当前活跃phase恢复
            resume_from = resume_phase or original_phase
        else:
            # current_phase等于last_completed，说明最后一个phase已正确退出
            resume_from = resume_phase or last_completed_phase

    # 确定下一个应该进入的phase
    next_phase = _get_next_phase_after(resume_from, original_phase)
    resume_summary = _build_resume_summary(
        session_id,
        original_trajectory,
        resume_from,
        next_phase,
        research_summary=research_summary,
        planning_summary=planning_summary,
        review_summary=review_summary,
        debug_summary=debug_summary,
        thinking_summary=thinking_summary,
    )
    resume_summary["debug_summary"] = debug_summary

    # 创建新的恢复trajectory
    new_session_id = f"r{ datetime.now().strftime('%Y%m%d%H%M%S')}"
    new_run_id = f"R{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # 保存原始trajectory的备份
    original_base = trajectory_date_dir(workdir, session_id)
    if original_base.exists():
        backup_dir = original_base.parent / f"{session_id}_resumed"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 复制原始trajectory到备份目录
        for f in original_base.glob("*"):
            shutil.copy2(f, backup_dir / f.name)

    # 创建新的恢复trajectory
    resumed_trajectory = Trajectory(
        run_id=new_run_id,
        session_id=new_session_id,
        created_at=datetime.now().isoformat(),
        prompt=f"[RESUMED from {session_id}] {original_trajectory.get('prompt', '')}",
        trigger_type="RESUMED",
        current_phase=resume_from,
        resume_summary=resume_summary,
    )

    # 添加恢复信息到phases
    resumed_trajectory.phases.append(PhaseRecord(
        phase=f"RESUME_FROM_{resume_from}",
        entered_at=datetime.now().isoformat(),
        actions=[{
            "type": "resume",
            "from_session": session_id,
            "from_phase": resume_from,
            "original_phase": original_phase,
            "resume_summary": resume_summary,
            "reason": "workflow resumed from interrupted point",
        }],
        notes=[
            f"Resumed from {session_id} at {resume_from}",
            f"Next phase: {next_phase or 'unknown'}",
        ],
    ))

    # 保存恢复trajectory
    save_trajectory(workdir, resumed_trajectory)

    return {
        "session_id": new_session_id,
        "run_id": new_run_id,
        "original_session_id": session_id,
        "resume_from": resume_from,
        "next_phase": next_phase,
        "can_resume": next_phase is not None,
        "original_trajectory": original_trajectory,
        "resume_summary": resume_summary,
        "resumed_trajectory": resumed_trajectory.to_dict(),
    }


def _get_next_phase_after(completed_phase: str, current_phase: str) -> str | None:
    """
    根据已完成的phase和当前phase，计算下一个应该进入的phase

    Returns:
        下一个phase，如果无法恢复则返回None
    """
    # 从COMPLETE, failed, aborted无法恢复
    if current_phase in ("COMPLETE", "failed", "aborted"):
        return None

    # 定义phase顺序
    phase_order = [
        "IDLE",
        "ROUTER",
        "OFFICE-HOURS",
        "EXPLORING",
        "RESEARCH",
        "THINKING",
        "PLANNING",
        "EXECUTING",
        "REVIEWING",
        "DEBUGGING",
        "REFINING",
        "COMPLETE",
    ]

    try:
        completed_idx = phase_order.index(completed_phase)
        # 下一个应该是completed_phase的下一个
        if completed_idx + 1 < len(phase_order):
            next_p = phase_order[completed_idx + 1]
            # 如果下一个是COMPLETE但current不是COMPLETE，可能需要回到前一个
            if next_p == "COMPLETE" and current_phase != "COMPLETE":
                # 返回最后一个非COMPLETE phase
                return phase_order[completed_idx] if completed_idx > 0 else current_phase
            return next_p
    except ValueError:
        pass

    # 默认返回current_phase
    return current_phase if current_phase != current_phase else None


class TrajectoryResumer:
    """
    Trajectory恢复器

    用于从中断点恢复工作流执行。
    """

    def __init__(self, workdir: str = "."):
        self.workdir = workdir
        self.resumed_session_id: str | None = None
        self.resumed_run_id: str | None = None

    def list_interrupted(self) -> list[dict[str, Any]]:
        """列出所有可以恢复的中断工作流"""
        trajectories = list_trajectories(self.workdir)
        interrupted = []

        for traj in trajectories:
            if traj.get("final_state") == "running":
                interrupted.append(traj)

        return interrupted

    def resume(self, session_id: str, resume_phase: str | None = None) -> dict[str, Any] | None:
        """
        恢复指定session的工作流

        Args:
            session_id: 要恢复的session ID
            resume_phase: 可选的指定恢复phase

        Returns:
            恢复结果
        """
        result = resume_from_point(self.workdir, session_id, resume_phase)
        if result:
            self.resumed_session_id = result["session_id"]
            self.resumed_run_id = result["run_id"]
        return result

    def get_resume_status(self) -> dict[str, Any]:
        """获取当前恢复状态"""
        if not self.resumed_session_id:
            return {"resumed": False}

        return {
            "resumed": True,
            "session_id": self.resumed_session_id,
            "run_id": self.resumed_run_id,
            "trajectories_dir": str(trajectory_base_path(self.workdir)),
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Trajectory Logger")
    parser.add_argument("--workdir", default=".", help="workspace directory")
    parser.add_argument("--session-id", help="session id")
    parser.add_argument("--op", choices=["start", "enter-phase", "exit-phase", "log-decision", "log-file", "log-error", "complete", "list", "resume-point", "resume", "list-interrupted"], required=True)
    parser.add_argument("--phase", help="phase name")
    parser.add_argument("--prompt", help="prompt for start")
    parser.add_argument("--trigger-type", default="FULL_WORKFLOW", help="trigger type")
    parser.add_argument("--decision", help="decision text")
    parser.add_argument("--reason", help="decision reason")
    parser.add_argument("--path", help="file path")
    parser.add_argument("--action", help="file action")
    parser.add_argument("--error", help="error message")
    parser.add_argument("--date", help="date filter for list (YYYYMMDD)")
    args = parser.parse_args()

    # 简单的单命令接口
    if args.op == "start":
        logger = TrajectoryLogger(args.workdir, args.session_id)
        run_id = logger.start(args.prompt or "", args.trigger_type)
        print(json.dumps({"run_id": run_id, "session_id": logger.session_id}))
        return 0

    if args.op == "list":
        trajectories = list_trajectories(args.workdir, args.date)
        print(json.dumps({"trajectories": trajectories}, ensure_ascii=False, indent=2))
        return 0

    if args.op == "resume-point":
        if not args.session_id:
            print("错误: --session-id required")
            return 1
        point = get_resume_point(args.workdir, args.session_id)
        if point is None:
            print("No trajectory found")
            return 1
        print(json.dumps(point, ensure_ascii=False, indent=2))
        return 0

    if args.op == "resume":
        if not args.session_id:
            print("错误: --session-id required for resume")
            return 1
        resumer = TrajectoryResumer(args.workdir)
        result = resumer.resume(args.session_id, args.phase)
        if result is None:
            print("错误: 无法恢复指定的session")
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "list-interrupted":
        resumer = TrajectoryResumer(args.workdir)
        interrupted = resumer.list_interrupted()
        print(json.dumps({"interrupted": interrupted}, ensure_ascii=False, indent=2))
        return 0

    # 需要session的操作
    if not args.session_id:
        print("错误: --session-id required")
        return 1

    logger = TrajectoryLogger(args.workdir, args.session_id)

    if args.op == "enter-phase":
        logger.enter_phase(args.phase or "")
        print(json.dumps({"status": "ok", "phase": args.phase}))
        return 0

    if args.op == "exit-phase":
        logger.exit_phase(args.phase or "")
        print(json.dumps({"status": "ok", "phase": args.phase}))
        return 0

    if args.op == "log-decision":
        logger.log_decision(args.decision or "", args.reason or "")
        print(json.dumps({"status": "ok"}))
        return 0

    if args.op == "log-file":
        logger.log_file_change(args.path or "", args.action or "")
        print(json.dumps({"status": "ok"}))
        return 0

    if args.op == "log-error":
        logger.log_error(args.error or "")
        print(json.dumps({"status": "ok"}))
        return 0

    if args.op == "complete":
        logger.complete()
        summary = logger.get_summary()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
