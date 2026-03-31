#!/usr/bin/env python3
"""
Unified State Schema - 统一状态Schema定义

定义了workflow的核心数据类型和验证规则。
所有状态文件必须符合此schema。

Schema版本: 1.0
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class PhaseStatus(Enum):
    """Phase执行状态"""
    IDLE = "IDLE"
    DIRECT_ANSWER = "DIRECT_ANSWER"
    PLANNING = "PLANNING"
    RESEARCH = "RESEARCH"
    THINKING = "THINKING"
    EXECUTING = "EXECUTING"
    REVIEWING = "REVIEWING"
    DEBUGGING = "DEBUGGING"
    COMPLETE = "COMPLETE"


class TriggerType(Enum):
    """触发类型"""
    DIRECT_ANSWER = "DIRECT_ANSWER"
    FULL_WORKFLOW = "FULL_WORKFLOW"
    STAGE = "STAGE"


class TaskStatus(Enum):
    """任务状态"""
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class Priority(Enum):
    """任务优先级"""
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class FileAction(Enum):
    """文件操作类型"""
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"


# ============================================================================
# Data Classes - 核心数据结构
# ============================================================================


@dataclass
class PhaseEntry:
    """Phase历史条目"""
    phase: str
    entered_at: str
    exited_at: Optional[str] = None
    reason: str = ""
    actions: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[Dict[str, str]] = field(default_factory=list)
    file_changes: List[Dict[str, str]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PhaseEntry:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Task:
    """任务 - 最小执行单元"""
    task_id: str
    title: str
    description: str = ""
    status: str = "backlog"
    priority: str = "P1"
    owned_files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    verification: str = ""
    created_at: str = ""
    completed_at: Optional[str] = None
    progress: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Task:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Decision:
    """决策记录"""
    timestamp: str
    decision: str
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        return result


@dataclass
class FileChange:
    """文件变更记录"""
    path: str
    action: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# Unified State - 统一状态文件
# ============================================================================


@dataclass
class WorkflowState:
    """统一工作流状态 - 单一真相来源"""
    version: str = "1.0"
    session_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    task: Optional[Task] = None
    phase: Dict[str, Any] = field(default_factory=dict)
    trigger_type: str = "FULL_WORKFLOW"  # 触发类型: DIRECT_ANSWER, FULL_WORKFLOW, STAGE
    artifacts: Dict[str, str] = field(default_factory=dict)
    decisions: List[Decision] = field(default_factory=list)
    file_changes: List[FileChange] = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.session_id:
            self.session_id = f"s{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "version": self.version,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "trigger_type": self.trigger_type,
            "artifacts": self.artifacts,
            "decisions": [d.to_dict() for d in self.decisions],
            "file_changes": [f.to_dict() for f in self.file_changes],
        }
        if self.task:
            result["task"] = self.task.to_dict()
        if self.phase:
            result["phase"] = self.phase
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowState:
        task = None
        if data.get("task"):
            task = Task.from_dict(data["task"])

        decisions = [Decision(**d) for d in data.get("decisions", [])]
        file_changes = [FileChange(**f) for f in data.get("file_changes", [])]

        return cls(
            version=data.get("version", "1.0"),
            session_id=data.get("session_id", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            trigger_type=data.get("trigger_type", "FULL_WORKFLOW"),
            task=task,
            phase=data.get("phase", {}),
            artifacts=data.get("artifacts", {}),
            decisions=decisions,
            file_changes=file_changes,
        )


# ============================================================================
# Trajectory - 轨迹记录
# ============================================================================


@dataclass
class TrajectoryPhase:
    """轨迹中的Phase条目"""
    phase: str
    entered_at: str
    exited_at: Optional[str] = None
    actions: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[Dict[str, str]] = field(default_factory=list)
    file_changes: List[Dict[str, str]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Trajectory:
    """单次运行的完整轨迹"""
    run_id: str
    session_id: str
    created_at: str = ""
    completed_at: Optional[str] = None
    prompt: str = ""
    trigger_type: str = ""
    phases: List[TrajectoryPhase] = field(default_factory=list)
    final_state: str = "running"
    failure_reason: Optional[str] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "prompt": self.prompt,
            "trigger_type": self.trigger_type,
            "phases": [p.to_dict() for p in self.phases],
            "final_state": self.final_state,
            "failure_reason": self.failure_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Trajectory:
        phases = [TrajectoryPhase(**p) for p in data.get("phases", [])]
        return cls(
            run_id=data["run_id"],
            session_id=data["session_id"],
            created_at=data.get("created_at", ""),
            completed_at=data.get("completed_at"),
            prompt=data.get("prompt", ""),
            trigger_type=data.get("trigger_type", ""),
            phases=phases,
            final_state=data.get("final_state", "running"),
            failure_reason=data.get("failure_reason"),
        )


# ============================================================================
# Validators - 验证函数
# ============================================================================


ALLOWED_PHASES = {p.value for p in PhaseStatus}
ALLOWED_TRIGGERS = {t.value for t in TriggerType}
ALLOWED_TASK_STATUS = {s.value for s in TaskStatus}
ALLOWED_PRIORITIES = {p.value for p in Priority}


def validate_phase(phase: str) -> List[str]:
    """验证phase是否合法"""
    errors = []
    if phase not in ALLOWED_PHASES:
        errors.append(f"invalid phase: {phase}, allowed: {ALLOWED_PHASES}")
    return errors


def validate_trigger_type(trigger_type: str) -> List[str]:
    """验证trigger_type是否合法"""
    errors = []
    if trigger_type not in ALLOWED_TRIGGERS:
        errors.append(f"invalid trigger_type: {trigger_type}, allowed: {ALLOWED_TRIGGERS}")
    return errors


def validate_task(task_data: Dict[str, Any]) -> List[str]:
    """验证任务数据"""
    errors = []

    if not task_data.get("task_id"):
        errors.append("task_id is required")
    if not task_data.get("title"):
        errors.append("title is required")

    status = task_data.get("status", "backlog")
    if status not in ALLOWED_TASK_STATUS:
        errors.append(f"invalid task status: {status}")

    priority = task_data.get("priority", "P1")
    if priority not in ALLOWED_PRIORITIES:
        errors.append(f"invalid priority: {priority}")

    return errors


def validate_state(state_data: Dict[str, Any]) -> List[str]:
    """验证完整状态数据"""
    errors = []

    # Version check
    if state_data.get("version") != "1.0":
        errors.append(f"unsupported schema version: {state_data.get('version')}")

    # Phase validation
    phase = state_data.get("phase", {})
    current = phase.get("current", "IDLE")
    errors.extend(validate_phase(current))

    # Trigger type validation
    trigger = state_data.get("trigger_type")
    if trigger:
        errors.extend(validate_trigger_type(trigger))

    # Task validation
    if state_data.get("task"):
        errors.extend(validate_task(state_data["task"]))

    # Phase history validation
    for i, entry in enumerate(phase.get("history", [])):
        if entry.get("phase") and entry["phase"] not in ALLOWED_PHASES:
            errors.append(f"phase_history[{i}] has invalid phase: {entry['phase']}")

    return errors


# ============================================================================
# Schema Version
# ============================================================================

SCHEMA_VERSION = "1.0"

# ============================================================================
# Schema Migration
# ============================================================================

SCHEMA_MIGRATIONS = {}


def register_migration(from_version: str, to_version: str):
    """注册一个迁移函数"""
    def decorator(func):
        SCHEMA_MIGRATIONS[(from_version, to_version)] = func
        return func
    return decorator


def migrate_state(state_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    将状态数据迁移到最新版本

    Args:
        state_data: 原始状态数据

    Returns:
        迁移后的状态数据
    """
    current_version = state_data.get("version", "1.0")
    target_version = SCHEMA_VERSION

    if current_version == target_version:
        return state_data

    # 按顺序执行迁移
    while current_version != target_version:
        next_version = _get_next_version(current_version)
        if next_version is None:
            raise ValueError(f"No migration path from version {current_version}")

        migration_key = (current_version, next_version)
        if migration_key not in SCHEMA_MIGRATIONS:
            raise ValueError(f"No migration function for {current_version} -> {next_version}")

        state_data = SCHEMA_MIGRATIONS[migration_key](state_data)
        current_version = next_version

    return state_data


def _get_next_version(version: str) -> Optional[str]:
    """获取下一个版本号"""
    version_order = ["1.0", "1.1", "2.0"]
    try:
        idx = version_order.index(version)
        if idx + 1 < len(version_order):
            return version_order[idx + 1]
    except ValueError:
        pass
    return None


# 示例迁移函数
@register_migration("1.0", "1.1")
def migrate_1_0_to_1_1(state: Dict[str, Any]) -> Dict[str, Any]:
    """迁移 1.0 -> 1.1: 添加新字段"""
    if "metadata" not in state:
        state["metadata"] = {}
    state["metadata"]["migrated_from"] = "1.0"
    return state
