#!/usr/bin/env python3
"""
Small Team Agent - 轻量级多Agent小团队编排

稳定版小团队拓扑:
- 1 Lead Agent (lead): 负责任务分配和协调
- Typed Workers: researcher, coder, reviewer, debugger
- 简单文件通信 via artifacts (无重型 message bus)

基于 contract + frontier 模式工作:
1. Lead 接收任务和 phase_contract
2. Lead 计算 frontier，决定分配给哪个 worker
3. Worker 执行任务，结果写回 artifact
4. Lead 汇总结果，推进 workflow

Usage:
    from team_agent import TeamAgent, WorkerType

    team = TeamAgent(workdir, task="实现REST API", contract=contract)
    result = team.run()

    # 或单独使用 worker
    worker = WorkerAgent(WorkerType.CODER, workdir)
    output = worker.execute(task="实现 /users endpoint")
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

import search_adapter
from safe_io import safe_write_text_locked
from unified_state import register_artifact


# ============================================================================
# Worker Type Definitions
# ============================================================================

class WorkerType(Enum):
    """Worker类型枚举"""
    RESEARCHER = "researcher"   # 研究搜索
    CODER = "coder"            # 代码实现
    REVIEWER = "reviewer"      # 代码审查
    DEBUGGER = "debugger"      # 调试修复
    LEAD = "lead"              # 领导协调


WORKER_DESCRIPTIONS: Dict[WorkerType, str] = {
    WorkerType.RESEARCHER: "信息搜索、最佳实践调研、技术方案研究",
    WorkerType.CODER: "代码实现、TDD驱动开发、功能实现",
    WorkerType.REVIEWER: "代码审查、质量门禁、验收测试",
    WorkerType.DEBUGGER: "错误定位、问题修复、调试执行",
    WorkerType.LEAD: "任务分配、进度协调、结果汇总",
}


class TeamRunResults(TypedDict):
    """Team run results type"""
    session_id: str
    task: str
    tasks_completed: int
    tasks_failed: int
    outputs: List[Dict[str, Any]]
    artifacts: List[str]


# ============================================================================
# Message Types for Team Communication
# ============================================================================

class MessageType(Enum):
    """消息类型"""
    TASK_ASSIGN = "task_assign"       # 任务分配
    TASK_RESULT = "task_result"       # 任务结果
    TASK_ERROR = "task_error"         # 任务错误
    STATUS_UPDATE = "status_update"   # 状态更新
    FRONTIER_UPDATE = "frontier_update"  # frontier 更新


@dataclass
class TeamMessage:
    """团队消息"""
    id: str
    msg_type: MessageType
    from_worker: WorkerType
    to_worker: Optional[WorkerType]  # None = broadcast
    content: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    parent_id: Optional[str] = None  # for tracing

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.msg_type.value,
            "from": self.from_worker.value,
            "to": self.to_worker.value if self.to_worker else "broadcast",
            "content": self.content,
            "timestamp": self.timestamp,
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> TeamMessage:
        return cls(
            id=d["id"],
            msg_type=MessageType(d["type"]),
            from_worker=WorkerType(d["from"]),
            to_worker=WorkerType(d["to"]) if d.get("to") and d["to"] != "broadcast" else None,
            content=d["content"],
            timestamp=d.get("timestamp", datetime.now().isoformat()),
            parent_id=d.get("parent_id"),
        )


# ============================================================================
# Worker Agent
# ============================================================================

@dataclass
class WorkerResult:
    """Worker执行结果"""
    worker_type: WorkerType
    task: str
    output: str
    success: bool
    artifacts: List[str] = field(default_factory=list)
    error: Optional[str] = None
    duration_seconds: float = 0.0


class WorkerAgent:
    """
    轻量级 Worker Agent

    每个 worker 只做一件事:
    - Researcher: 搜索研究
    - Coder: 实现代码
    - Reviewer: 审查代码
    - Debugger: 调试修复
    """

    def __init__(self, worker_type: WorkerType, workdir: str = "."):
        self.worker_type = worker_type
        self.workdir = Path(workdir)
        self.session_id = f"{worker_type.value}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> WorkerResult:
        """
        执行任务

        Args:
            task: 任务描述
            context: 上下文信息 (可选)

        Returns:
            WorkerResult: 执行结果
        """
        start_time = datetime.now()

        try:
            if self.worker_type == WorkerType.RESEARCHER:
                output, artifacts = self._do_research(task, context)
            elif self.worker_type == WorkerType.CODER:
                output, artifacts = self._do_code(task, context)
            elif self.worker_type == WorkerType.REVIEWER:
                output, artifacts = self._do_review(task, context)
            elif self.worker_type == WorkerType.DEBUGGER:
                output, artifacts = self._do_debug(task, context)
            else:
                output = f"Unknown worker type: {self.worker_type}"
                artifacts = []

            duration = (datetime.now() - start_time).total_seconds()
            return WorkerResult(
                worker_type=self.worker_type,
                task=task,
                output=output,
                success=True,
                artifacts=artifacts,
                duration_seconds=duration,
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return WorkerResult(
                worker_type=self.worker_type,
                task=task,
                output="",
                success=False,
                error=str(e),
                duration_seconds=duration,
            )

    def _do_research(self, task: str, context: Optional[Dict[str, Any]]) -> tuple[str, List[str]]:
        """Research worker: 搜索研究"""
        query = task
        response, used_fallback = search_adapter.search_with_fallback(query, num_results=5)

        findings = []
        for r in response.results:
            findings.append(f"## {r.title}\n{r.snippet}\nSource: {r.url}")

        output = f"# Research Findings\n\nQuery: {query}\n\n" + "\n\n".join(findings)
        output += f"\n\n**Search Engine**: {response.search_engine}"
        if response.metadata.get("degraded_mode"):
            output += f"\n**Warning**: {response.metadata.get('degraded_reason', 'Degraded mode')}"

        # Write findings artifact
        findings_path = self.workdir / f"findings_{self.session_id}.md"
        findings_path.write_text(output, encoding="utf-8")

        return output, [str(findings_path)]

    def _do_code(self, task: str, context: Optional[Dict[str, Any]]) -> tuple[str, List[str]]:
        """Coder worker: 代码实现 (生成代码片段/建议)"""
        # 注意: 实际代码实现由 EXECUTING phase 负责
        # 这里只生成实现建议
        output = f"# Code Implementation Plan\n\nTask: {task}\n\n"

        if context and context.get("owned_files"):
            output += "## Target Files\n"
            for f in context["owned_files"]:
                output += f"- {f}\n"

        if context and context.get("verification"):
            output += f"\n## Verification\n{context['verification']}\n"

        output += "\n## Implementation Notes\n"
        output += "TDD approach recommended:\n1. Write failing test\n2. Implement minimal code\n3. Refactor\n"

        return output, []

    def _do_review(self, task: str, context: Optional[Dict[str, Any]]) -> tuple[str, List[str]]:
        """Reviewer worker: 代码审查"""
        output = f"# Code Review\n\nTask: {task}\n\n"
        output += "## Review Focus\n"
        output += "- Correctness\n"
        output += "- Security\n"
        output += "- Performance\n"
        output += "- Maintainability\n"

        if context and context.get("owned_files"):
            output += "\n## Files to Review\n"
            for f in context["owned_files"]:
                output += f"- {f}\n"

        return output, []

    def _do_debug(self, task: str, context: Optional[Dict[str, Any]]) -> tuple[str, List[str]]:
        """Debugger worker: 调试修复"""
        output = f"# Debug Analysis\n\nTask: {task}\n\n"
        output += "## Debugging Steps\n"
        output += "1. Reproduce the issue\n"
        output += "2. Identify root cause\n"
        output += "3. Implement fix\n"
        output += "4. Verify fix\n"
        output += "5. Check for regressions\n"

        if context and context.get("error"):
            output += f"\n## Error Context\n{context['error']}\n"

        return output, []


# ============================================================================
# Team Agent (Lead Orchestrator)
# ============================================================================

@dataclass
class TeamTask:
    """团队任务"""
    id: str
    description: str
    assigned_worker: Optional[WorkerType] = None
    status: str = "pending"  # pending, assigned, completed, failed
    result: Optional[WorkerResult] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class TeamAgent:
    """
    Lead Agent - 小团队协调者

    负责任务分配和协调:
    1. 解析 contract 和 frontier
    2. 分配任务给合适的 worker
    3. 收集结果并汇总
    4. 推进 workflow

    Usage:
        team = TeamAgent(workdir, task="实现REST API")
        result = team.run()
    """

    def __init__(
        self,
        workdir: str = ".",
        task: Optional[str] = None,
        contract: Optional[Dict[str, Any]] = None,
        frontier: Optional[Dict[str, Any]] = None,
    ):
        self.workdir = Path(workdir)
        self.task = task or "Untitled task"
        self.contract = contract or {}
        self.frontier = frontier or {}
        self.session_id = f"team-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.tasks: Dict[str, TeamTask] = {}
        self.messages: List[TeamMessage] = []

    def add_task(self, description: str, worker_type: Optional[WorkerType] = None) -> str:
        """添加任务"""
        task_id = str(uuid.uuid4())[:8]
        # If worker_type is provided, auto-assign
        status = "assigned" if worker_type else "pending"
        task = TeamTask(
            id=task_id,
            description=description,
            assigned_worker=worker_type,
            status=status,  # pending, assigned, completed, failed
        )
        self.tasks[task_id] = task
        return task_id

    def assign_task(self, task_id: str, worker_type: WorkerType) -> None:
        """分配任务给 worker"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        self.tasks[task_id].assigned_worker = worker_type
        self.tasks[task_id].status = "assigned"

    def execute_task(self, task_id: str) -> WorkerResult:
        """执行单个任务"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]
        if not task.assigned_worker:
            raise ValueError(f"Task {task_id} has no assigned worker")

        worker = WorkerAgent(task.assigned_worker, str(self.workdir))
        result = worker.execute(task.description, context=self.contract)

        task.result = result
        task.status = "completed" if result.success else "failed"

        # Log message
        msg = TeamMessage(
            id=str(uuid.uuid4())[:8],
            msg_type=MessageType.TASK_RESULT if result.success else MessageType.TASK_ERROR,
            from_worker=task.assigned_worker,
            to_worker=WorkerType.LEAD,
            content={
                "task_id": task_id,
                "success": result.success,
                "output": result.output[:500] if result.output else "",
                "error": result.error,
            },
            parent_id=task_id,
        )
        self.messages.append(msg)

        return result

    def run(self, phase: str = "EXECUTING", register_artifacts: bool = False) -> TeamRunResults:
        """
        运行团队任务

        基于 contract 和 frontier 自动分配任务
        使用 frontier 分组进行调度:
        - parallel_candidates: 可并行的任务候选（顺序执行，当前为 parallel-ready 而非真正并行）
        - conflict_groups: 冲突任务串行执行

        Args:
            phase: Current workflow phase for artifact registration
            register_artifacts: Whether to register artifacts with the artifact registry

        Returns:
            TeamRunResults with results summary
        """
        results: TeamRunResults = {
            "session_id": self.session_id,
            "task": self.task,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "outputs": [],
            "artifacts": [],
        }

        executed_ids: set = set()

        # 如果有 frontier，使用 frontier 分配任务
        if self.frontier.get("executable_frontier"):
            for task_data in self.frontier["executable_frontier"]:
                task_desc = f"Execute: {task_data.get('title', 'Untitled')}"
                worker_type = self._infer_worker_type(task_data)
                self.add_task(task_desc, worker_type)

        # 如果有 contract goals，为每个 goal 添加任务
        if self.contract.get("goals"):
            for goal in self.contract["goals"]:
                task_desc = f"Goal: {goal}"
                self.add_task(task_desc, WorkerType.CODER)

        # 执行 parallel_candidates (顺序执行，当前为 parallel-ready)
        parallel_candidates = self.frontier.get("parallel_candidates", [])
        for parallel_group in parallel_candidates:
            # 并行执行组内所有任务
            for task_data in parallel_group:
                task_desc = f"Parallel: {task_data.get('title', 'Untitled')}"
                worker_type = self._infer_worker_type(task_data)
                task_id = self.add_task(task_desc, worker_type)
                self._execute_single_task(task_id, results, executed_ids)

        # 2. 执行 conflict_groups (冲突任务串行)
        conflict_groups = self.frontier.get("conflict_groups", [])
        for conflict_group in conflict_groups:
            for task_data in conflict_group:
                task_desc = f"Conflict: {task_data.get('title', 'Untitled')}"
                worker_type = self._infer_worker_type(task_data)
                task_id = self.add_task(task_desc, worker_type)
                self._execute_single_task(task_id, results, executed_ids)

        # 3. 执行通过 add_task 直接添加的任务（非 frontier 任务）
        for task_id, task in self.tasks.items():
            if task.status == "assigned" and task.assigned_worker and task_id not in executed_ids:
                self._execute_single_task(task_id, results, executed_ids)

        # Save team snapshot for recoverability
        self.save_snapshot(str(self.workdir))

        # Register artifacts with authoritative pipeline if requested
        if register_artifacts and results.get("artifacts"):
            for artifact in results["artifacts"]:
                register_artifact(str(self.workdir), "team_output", artifact, phase)

        return results

    def _execute_single_task(self, task_id: str, results: TeamRunResults, executed_ids: set) -> None:
        """执行单个任务并更新 results"""
        task = self.tasks.get(task_id)
        if not task or not task.assigned_worker:
            return
        if task_id in executed_ids:
            return

        result = self.execute_task(task_id)
        executed_ids.add(task_id)

        if result.success:
            results["tasks_completed"] += 1
            results["artifacts"].extend(result.artifacts)
        else:
            results["tasks_failed"] += 1
        results["outputs"].append({
            "task_id": task_id,
            "worker": task.assigned_worker.value,
            "success": result.success,
            "output": result.output[:200] if result.output else "",
            "error": result.error,
        })

    def _infer_worker_type(self, task_data: Dict[str, Any]) -> WorkerType:
        """根据任务数据推断合适的 worker 类型"""
        title = task_data.get("title", "").lower()
        desc = task_data.get("description", "").lower()

        combined = title + " " + desc

        if any(k in combined for k in ["research", "search", "调研", "研究", "查找"]):
            return WorkerType.RESEARCHER
        if any(k in combined for k in ["review", "审查", "检查", "验证"]):
            return WorkerType.REVIEWER
        if any(k in combined for k in ["debug", "fix", "error", "bug", "调试", "修复"]):
            return WorkerType.DEBUGGER
        if any(k in combined for k in ["implement", "code", "实现", "代码", "功能"]):
            return WorkerType.CODER

        # 默认分配给 coder
        return WorkerType.CODER

    def get_state(self) -> Dict[str, Any]:
        """获取团队状态"""
        return {
            "session_id": self.session_id,
            "task": self.task,
            "total_tasks": len(self.tasks),
            "tasks": {
                tid: {
                    "description": t.description,
                    "assigned_worker": t.assigned_worker.value if t.assigned_worker else None,
                    "status": t.status,
                    "success": t.result.success if t.result else None,
                }
                for tid, t in self.tasks.items()
            },
            "messages_count": len(self.messages),
        }

    def save_snapshot(self, workdir: str) -> None:
        """Save team state snapshot to .team_registry.json for recoverability"""
        registry_path = Path(workdir) / ".team_registry.json"

        # Load existing registry or create new
        if registry_path.exists():
            try:
                import json as json_lib
                registry = json_lib.loads(registry_path.read_text(encoding="utf-8"))
            except (json_lib.JSONDecodeError, OSError):
                registry = {"team_sessions": []}
        else:
            registry = {"team_sessions": []}

        # Add/update this session
        snapshot = {
            "session_id": self.session_id,
            "task": self.task,
            "timestamp": datetime.now().isoformat(),
            "total_tasks": len(self.tasks),
            "completed_tasks": sum(1 for t in self.tasks.values() if t.status == "completed"),
            "failed_tasks": sum(1 for t in self.tasks.values() if t.status == "failed"),
            "state": self.get_state(),
        }

        # Update or append
        found = False
        for i, sess in enumerate(registry.get("team_sessions", [])):
            if sess.get("session_id") == self.session_id:
                registry["team_sessions"][i] = snapshot
                found = True
                break
        if not found:
            registry["team_sessions"].append(snapshot)

        # Write registry
        import json as json_lib
        safe_write_text_locked(registry_path, json_lib.dumps(registry, indent=2, ensure_ascii=False))


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Small Team Agent")
    parser.add_argument("--workdir", default=".", help="workspace directory")
    parser.add_argument("--task", required=True, help="task description")
    parser.add_argument("--type", choices=["researcher", "coder", "reviewer", "debugger"],
                        help="worker type (for single worker mode)")
    args = parser.parse_args()

    if args.type:
        # 单 worker 模式
        worker_type = WorkerType(args.type)
        worker = WorkerAgent(worker_type, args.workdir)
        result = worker.execute(args.task)
        print(f"Worker: {worker_type.value}")
        print(f"Success: {result.success}")
        print(f"Output:\n{result.output}")
        if result.error:
            print(f"Error: {result.error}")
        print(f"Artifacts: {result.artifacts}")
        print(f"Duration: {result.duration_seconds:.2f}s")
    else:
        # 团队模式
        team = TeamAgent(args.workdir, task=args.task)
        team.add_task(args.task, WorkerType.CODER)
        result = team.run()
        print(f"Team Session: {result['session_id']}")
        print(f"Tasks: {result['tasks_completed']} completed, {result['tasks_failed']} failed")
        for output in result["outputs"]:
            print(f"  - [{output['worker']}] {'✓' if output['success'] else '✗'}")


if __name__ == "__main__":
    main()
