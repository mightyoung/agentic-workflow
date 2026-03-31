#!/usr/bin/env python3
"""
Agent Spawner - 多Agent编排器 (v2.0)

借鉴 ruflo 设计最佳实践:

1. Domain-Based Routing - 领域路由代替简单Agent选择
2. Queen Coordinator - 任务分解 + 5维度Agent评分 + 健康监控
3. Agent Registry - Agent状态机 + 心跳机制
4. TaskOrchestrator - 双向依赖图 + 拓扑排序 + 循环检测
5. Message Bus - 优先级队列 + TTL + 确认机制
6. Consensus Mechanisms - 多数/权重/Queen-Override模式
7. Rollback - 失败时反向依赖顺序回滚

Usage:
    from agent_spawner import (
        AgentSpawner, AgentTask, AgentDomain,
        QueenCoordinator, AgentRegistry,
        TaskOrchestrator, MessageBus,
        ConsensusMode
    )

    # Domain-based spawning
    spawner = AgentSpawner(workdir)
    results = spawner.spawn_by_domain(Domain.THINKING, "分析架构设计")
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ============================================================================
# Domain & Agent Definitions (借鉴 ruflo domain-based routing)
# ============================================================================

class Domain(Enum):
    """Agent领域分类 (借鉴 ruflo 5-domain结构)"""
    RESEARCH = "research"      # 信息搜索与分析
    THINKING = "thinking"     # 专家推理
    PLANNING = "planning"     # 任务规划
    EXECUTION = "execution"   # 代码实现
    REVIEW = "review"         # 代码审查
    DEBUG = "debug"           # 调试修复
    COORDINATION = "coordination"  # 顶层协调


# Agent定义目录
AGENTS_DIR = "agents"


@dataclass
class AgentCapability:
    """Agent能力描述"""
    domain: Domain
    keywords: List[str]  # 触发关键词
    priority: int = 0    # 同domain内的优先级


@dataclass
class AgentMetadata:
    """Agent元数据"""
    name: str
    domain: Domain
    description: str
    responsibility: str
    triggers: List[str]
    tools: List[str]
    capabilities: List[AgentCapability] = field(default_factory=list)
    max_concurrent: int = 3


# ============================================================================
# Agent Registry with Health Monitoring (借鉴 ruflo agent-registry)
# ============================================================================

class AgentState(Enum):
    """Agent状态机 (借鉴 ruflo)"""
    INITIALIZING = "initializing"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    UNHEALTHY = "unhealthy"
    TERMINATED = "terminated"


@dataclass
class AgentHealth:
    """Agent健康状态"""
    state: AgentState
    last_heartbeat: str
    miss_count: int = 0
    error_count: int = 0
    task_count: int = 0
    avg_duration: float = 0.0


@dataclass
class AgentRegistration:
    """注册的Agent"""
    metadata: AgentMetadata
    health: AgentHealth
    current_task: Optional[str] = None


class AgentRegistry:
    """
    Agent注册表 (借鉴 ruflo agent-registry)

    功能:
    - Agent注册/注销
    - 状态跟踪
    - 心跳监控
    - 5维度评分 (capability, load, performance, health, availability)
    """

    def __init__(self):
        self._agents: Dict[str, AgentRegistration] = {}
        self._lock = threading.RLock()
        self._heartbeat_interval = 30  # 秒
        self._max_miss = 3

    def register(self, metadata: AgentMetadata) -> str:
        """注册Agent"""
        with self._lock:
            health = AgentHealth(
                state=AgentState.INITIALIZING,
                last_heartbeat=datetime.now().isoformat(),
            )
            reg = AgentRegistration(metadata=metadata, health=health)
            self._agents[metadata.name] = reg
            # 初始化后变为idle
            health.state = AgentState.IDLE
            return metadata.name

    def unregister(self, name: str):
        """注销Agent"""
        with self._lock:
            if name in self._agents:
                self._agents[name].health.state = AgentState.TERMINATED
                del self._agents[name]

    def get_agents_by_domain(self, domain: Domain) -> List[str]:
        """获取指定领域的Agent"""
        with self._lock:
            return [
                name for name, reg in self._agents.items()
                if reg.metadata.domain == domain and
                reg.health.state in (AgentState.IDLE, AgentState.BUSY)
            ]

    def get_available_agents(self) -> List[str]:
        """获取所有可用Agent"""
        with self._lock:
            return [
                name for name, reg in self._agents.items()
                if reg.health.state == AgentState.IDLE
            ]

    def update_state(self, name: str, state: AgentState, task_id: Optional[str] = None):
        """更新Agent状态"""
        with self._lock:
            if name not in self._agents:
                return
            reg = self._agents[name]
            reg.health.state = state
            reg.current_task = task_id
            reg.health.last_heartbeat = datetime.now().isoformat()

            if state == AgentState.IDLE:
                reg.health.miss_count = 0

    def heartbeat(self, name: str) -> bool:
        """
        处理心跳

        Returns:
            True if agent is healthy, False if should be marked unhealthy
        """
        with self._lock:
            if name not in self._agents:
                return False
            reg = self._agents[name]
            reg.health.last_heartbeat = datetime.now().isoformat()
            reg.health.miss_count = 0
            return True

    def check_health(self) -> Dict[str, bool]:
        """检查所有Agent健康状态"""
        now = datetime.now()
        result = {}
        with self._lock:
            for name, reg in self._agents.items():
                if reg.health.state == AgentState.TERMINATED:
                    continue
                last = datetime.fromisoformat(reg.health.last_heartbeat)
                elapsed = (now - last).total_seconds()
                if elapsed > self._heartbeat_interval * self._max_miss:
                    reg.health.state = AgentState.UNHEALTHY
                    reg.health.miss_count += 1
                    result[name] = False
                else:
                    result[name] = True
        return result

    def score_agent(self, name: str) -> Dict[str, float]:
        """
        5维度Agent评分 (借鉴 ruflo queen-coordinator)

        Returns:
            capability, load, performance, health, availability
        """
        with self._lock:
            if name not in self._agents:
                return {"capability": 0, "load": 0, "performance": 0, "health": 0, "availability": 0}
            reg = self._agents[name]

            # capability: 基于domain优先级
            capability = 1.0 - (reg.metadata.capabilities[0].priority / 10) if reg.metadata.capabilities else 0.5

            # load: 基于当前任务
            load = 1.0 if reg.health.state == AgentState.IDLE else 0.3

            # performance: 基于平均执行时间
            perf = max(0.1, 1.0 - (reg.health.avg_duration / 300)) if reg.health.avg_duration > 0 else 0.8

            # health: 基于错误率和心跳
            health = 1.0 if reg.health.error_count < 3 else max(0.1, 1.0 - reg.health.error_count * 0.2)

            # availability: 基于状态
            avail = 1.0 if reg.health.state == AgentState.IDLE else 0.0

            return {
                "capability": capability,
                "load": load,
                "performance": perf,
                "health": health,
                "availability": avail,
            }

    def select_best_agent(self, domain: Domain) -> Optional[str]:
        """
        基于5维度评分选择最佳Agent (借鉴 ruflo queen-coordinator)
        """
        candidates = self.get_agents_by_domain(domain)
        if not candidates:
            return None

        best_score = -1.0
        best_agent = None

        for name in candidates:
            scores = self.score_agent(name)
            # 综合评分: capability权重最高
            total = (
                scores["capability"] * 0.35 +
                scores["load"] * 0.25 +
                scores["performance"] * 0.15 +
                scores["health"] * 0.15 +
                scores["availability"] * 0.10
            )
            if total > best_score:
                best_score = total
                best_agent = name

        return best_agent


# ============================================================================
# Task State Machine (借鉴 ruflo Task.ts)
# ============================================================================

class TaskState(Enum):
    """任务状态机"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# TaskOrchestrator - 双向依赖图 + 拓扑排序 (借鉴 ruflo task-orchestrator)
# ============================================================================

@dataclass
class OrchestratedTask:
    """编排任务"""
    task_id: str
    agent_type: str
    task: str
    domain: Domain
    context: Optional[Dict[str, Any]] = None
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)  # 反向依赖
    state: TaskState = TaskState.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class CycleDetectedError(Exception):
    """循环依赖检测异常"""
    pass


class TaskOrchestrator:
    """
    任务编排器 (借鉴 ruflo task-orchestrator)

    功能:
    - 双向依赖图 (dependency + dependent)
    - 拓扑排序执行顺序
    - 循环检测
    - 自动解锁依赖完成的task
    """

    def __init__(self):
        self._tasks: Dict[str, OrchestratedTask] = {}
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)  # task -> dependencies
        self._dependent_graph: Dict[str, Set[str]] = defaultdict(set)   # task -> dependents
        self._lock = threading.RLock()

    def add_task(self, task: OrchestratedTask) -> str:
        """添加任务"""
        with self._lock:
            self._tasks[task.task_id] = task
            self._dependency_graph[task.task_id] = set(task.dependencies)
            for dep in task.dependencies:
                self._dependent_graph[dep].add(task.task_id)
            return task.task_id

    def add_dependency(self, task_id: str, dependency: str):
        """添加依赖关系"""
        with self._lock:
            if task_id not in self._tasks or dependency not in self._tasks:
                raise ValueError(f"Task not found: {task_id} or {dependency}")

            self._dependency_graph[task_id].add(dependency)
            self._dependent_graph[dependency].add(task_id)
            self._tasks[task_id].dependencies.append(dependency)
            self._tasks[dependency].dependents.append(task_id)

    def detect_cycle(self) -> Optional[List[str]]:
        """
        检测循环依赖 (DFS)

        Returns:
            循环路径，如果无循环则返回None
        """
        with self._lock:
            visited = set()
            rec_stack = set()
            path = []

            def dfs(task_id: str) -> Optional[List[str]]:
                visited.add(task_id)
                rec_stack.add(task_id)
                path.append(task_id)

                for dep in self._dependency_graph.get(task_id, set()):
                    if dep not in visited:
                        result = dfs(dep)
                        if result:
                            return result
                    elif dep in rec_stack:
                        cycle_start = path.index(dep)
                        return path[cycle_start:] + [dep]

                path.pop()
                rec_stack.remove(task_id)
                return None

            for task_id in self._tasks:
                if task_id not in visited:
                    cycle = dfs(task_id)
                    if cycle:
                        return cycle

            return None

    def get_execution_order(self) -> List[str]:
        """
        拓扑排序获取执行顺序 (Kahn算法)

        Returns:
            按依赖顺序排列的任务ID列表
        """
        with self._lock:
            cycle = self.detect_cycle()
            if cycle:
                raise CycleDetectedError(f"Cycle detected: {' -> '.join(cycle)}")

            in_degree = defaultdict(int)
            for task_id in self._tasks:
                in_degree[task_id] = len(self._dependency_graph[task_id])

            queue = [t for t, d in in_degree.items() if d == 0]
            result = []

            while queue:
                # 按优先级排序
                queue.sort(key=lambda t: self._tasks[t].task_id)
                task_id = queue.pop(0)
                result.append(task_id)

                for dependent in self._dependent_graph[task_id]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

            if len(result) != len(self._tasks):
                raise CycleDetectedError("Not all tasks can be scheduled")

            return result

    def get_ready_tasks(self) -> List[str]:
        """获取所有依赖已满足的任务"""
        with self._lock:
            ready = []
            for task_id, task in self._tasks.items():
                if task.state != TaskState.PENDING:
                    continue
                deps_satisfied = all(
                    self._tasks[dep].state == TaskState.COMPLETED
                    for dep in task.dependencies
                )
                if deps_satisfied:
                    ready.append(task_id)
            return ready

    def mark_completed(self, task_id: str, result: Any = None, error: Optional[str] = None):
        """标记任务完成"""
        with self._lock:
            if task_id not in self._tasks:
                return
            task = self._tasks[task_id]
            task.state = TaskState.COMPLETED if error is None else TaskState.FAILED
            task.result = result
            task.error = error
            task.completed_at = datetime.now().isoformat()

    def get_rollback_order(self) -> List[str]:
        """获取回滚顺序 (反向依赖拓扑)"""
        with self._lock:
            completed = [
                t for t, task in self._tasks.items()
                if task.state == TaskState.COMPLETED
            ]
            # 按依赖反向排序
            result = []
            visited = set()

            def dfs(task_id: str):
                if task_id in visited:
                    return
                visited.add(task_id)
                for dep in self._tasks[task_id].dependents:
                    dfs(dep)
                result.append(task_id)

            for task_id in completed:
                dfs(task_id)

            return result


# ============================================================================
# Message Bus (借鉴 ruflo message-bus)
# ============================================================================

class MessagePriority(Enum):
    """消息优先级"""
    URGENT = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class AgentMessage:
    """Agent间消息"""
    id: str
    from_agent: str
    to_agent: str
    priority: MessagePriority
    content: Any
    timestamp: str
    ttl: int = 60  # 秒
    acknowledged: bool = False


class MessageBus:
    """
    消息总线 (借鉴 ruflo message-bus)

    功能:
    - 优先级队列
    - TTL处理
    - 确认机制
    - O(1)入队/出队
    """

    def __init__(self):
        self._queues: Dict[MessagePriority, List[AgentMessage]] = {
            p: [] for p in MessagePriority
        }
        self._lock = threading.RLock()
        self._counter = 0

    def publish(self, from_agent: str, to_agent: str, content: Any,
                priority: MessagePriority = MessagePriority.NORMAL,
                ttl: int = 60) -> str:
        """发布消息"""
        with self._lock:
            self._counter += 1
            msg_id = f"msg_{self._counter}_{int(time.time())}"
            msg = AgentMessage(
                id=msg_id,
                from_agent=from_agent,
                to_agent=to_agent,
                priority=priority,
                content=content,
                timestamp=datetime.now().isoformat(),
                ttl=ttl,
            )
            self._queues[priority].append(msg)
            return msg_id

    def receive(self, agent: str, timeout: float = 1.0) -> Optional[AgentMessage]:
        """接收消息 (阻塞)"""
        start = time.time()
        while time.time() - start < timeout:
            with self._lock:
                for priority in MessagePriority:
                    queue = self._queues[priority]
                    for i, msg in enumerate(queue):
                        if msg.to_agent == agent and not msg.acknowledged:
                            if msg.ttl > 0:
                                queue.pop(i)
                                return msg
            time.sleep(0.01)
        return None

    def acknowledge(self, msg_id: str) -> bool:
        """确认消息"""
        with self._lock:
            for queue in self._queues.values():
                for msg in queue:
                    if msg.id == msg_id:
                        msg.acknowledged = True
                        return True
            return False

    def cleanup_expired(self) -> int:
        """清理过期消息"""
        count = 0
        now = datetime.now()
        with self._lock:
            for priority in MessagePriority:
                queue = self._queues[priority]
                expired = []
                for i, msg in enumerate(queue):
                    msg_ttl = (now - datetime.fromisoformat(msg.timestamp)).total_seconds()
                    if msg_ttl > msg.ttl:
                        expired.append(i)
                # 逆序删除
                for i in reversed(expired):
                    queue.pop(i)
                    count += 1
        return count


# ============================================================================
# Consensus Mechanisms (借鉴 ruflo queen-coordinator)
# ============================================================================

class ConsensusMode(Enum):
    """共识模式"""
    MAJORITY = "majority"           # 多数同意
    SUPERMAJORITY = "supermajority" # 超多数 (2/3+)
    UNANIMOUS = "unanimous"         # 全票同意
    WEIGHTED = "weighted"           # 权重投票
    QUEEN_OVERRIDE = "queen_override"  # Queen强制决定


@dataclass
class Vote:
    """投票"""
    agent: str
    decision: bool
    weight: float = 1.0
    reason: str = ""


class ConsensusProtocol:
    """
    共识协议 (借鉴 ruflo queen-coordinator)

    支持5种共识模式
    """

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def vote(self, agents: List[str], proposal: str,
             mode: ConsensusMode = ConsensusMode.MAJORITY) -> tuple[bool, List[Vote]]:
        """
        投票决策

        Returns:
            (accepted, votes)
        """
        votes: List[Vote] = []

        for agent in agents:
            scores = self.registry.score_agent(agent)
            # 简单模拟: 健康且可用的agent投赞成票
            decision = scores["health"] > 0.5 and scores["availability"] > 0
            weight = (
                scores["capability"] * 0.35 +
                scores["performance"] * 0.25 +
                scores["health"] * 0.40
            )
            votes.append(Vote(
                agent=agent,
                decision=decision,
                weight=weight,
                reason=f"health={scores['health']:.2f}, avail={scores['availability']:.2f}"
            ))

        # 统计
        yes_votes = sum(1 for v in votes if v.decision)
        total = len(votes)
        yes_weight = sum(v.weight for v in votes if v.decision)
        total_weight = sum(v.weight for v in votes)

        if mode == ConsensusMode.MAJORITY:
            accepted = yes_votes > total / 2
        elif mode == ConsensusMode.SUPERMAJORITY:
            accepted = yes_votes >= total * 2 / 3
        elif mode == ConsensusMode.UNANIMOUS:
            accepted = yes_votes == total
        elif mode == ConsensusMode.WEIGHTED:
            accepted = yes_weight > total_weight / 2
        elif mode == ConsensusMode.QUEEN_OVERRIDE:
            # Queen永远接受 (简化)
            accepted = True
        else:
            accepted = yes_votes > total / 2

        return accepted, votes


# ============================================================================
# Queen Coordinator (借鉴 ruflo queen-coordinator)
# ============================================================================

class QueenCoordinator:
    """
    Queen协调器 (借鉴 ruflo queen-coordinator)

    战略大脑:
    - 任务分解和复杂度评分
    - 5维度Agent评分
    - 健康监控和瓶颈检测
    - 5种共识模式
    """

    def __init__(self, workdir: str = "."):
        self.workdir = Path(workdir)
        self.registry = AgentRegistry()
        self.orchestrator = TaskOrchestrator()
        self.message_bus = MessageBus()
        self.consensus = ConsensusProtocol(self.registry)
        self._load_agent_definitions()
        self._start_health_monitor()

    def _load_agent_definitions(self):
        """加载Agent定义"""
        agents_dir = self.workdir / AGENTS_DIR
        if not agents_dir.exists():
            return

        for agent_file in agents_dir.glob("*.md"):
            if agent_file.stem == "README":
                continue
            metadata = self._parse_agent_file(agent_file)
            if metadata:
                self.registry.register(metadata)

    def _parse_agent_file(self, path: Path) -> Optional[AgentMetadata]:
        """解析Agent定义文件"""
        content = path.read_text(encoding="utf-8")
        name = path.stem

        import re

        # 提取domain
        domain = Domain.EXECUTION
        for d in Domain:
            if d.value in name.lower():
                domain = d
                break

        # 提取description
        desc_match = re.search(r'description:\s*\|?\s*\n((?:[ \t]+.+\n?)+)', content)
        description = desc_match.group(1).strip() if desc_match else ""

        # 提取responsibility
        resp_match = re.search(r'responsibility:\s*([^\n]+)', content)
        responsibility = resp_match.group(1).strip() if resp_match else ""

        # 提取triggers
        triggers_match = re.search(r'triggers?:\s*\[([^\]]+)\]', content)
        triggers = []
        if triggers_match:
            triggers = [t.strip() for t in triggers_match.group(1).split(',')]

        # 提取tools
        tools_match = re.search(r'tools?:\s*\[([^\]]+)\]', content)
        tools = []
        if tools_match:
            tools = [t.strip() for t in tools_match.group(1).split(',')]

        return AgentMetadata(
            name=name,
            domain=domain,
            description=description,
            responsibility=responsibility,
            triggers=triggers,
            tools=tools,
        )

    def _start_health_monitor(self):
        """启动健康监控线程"""
        def monitor():
            while True:
                self.registry.check_health()
                self.message_bus.cleanup_expired()
                time.sleep(10)

        self._monitor_thread = threading.Thread(target=monitor, daemon=True)
        self._monitor_thread.start()

    def decompose_task(self, task: str, prompt: str = "") -> List[OrchestratedTask]:
        """
        任务分解 (借鉴 ruflo)

        Returns:
            分解后的任务列表
        """
        tasks: List[OrchestratedTask] = []

        # 简单的基于关键词的分解
        task_lower = task.lower()

        if any(k in task_lower for k in ["研究", "搜索", "调研", "research"]):
            tasks.append(OrchestratedTask(
                task_id=f"T{len(tasks)+1}",
                agent_type="researcher",
                task=f"搜索: {task}",
                domain=Domain.RESEARCH,
            ))

        if any(k in task_lower for k in ["分析", "思考", "thinking", "思考"]):
            tasks.append(OrchestratedTask(
                task_id=f"T{len(tasks)+1}",
                agent_type="planner",
                task=f"分析: {task}",
                domain=Domain.THINKING,
            ))

        if any(k in task_lower for k in ["实现", "开发", "写代码", "implement"]):
            tasks.append(OrchestratedTask(
                task_id=f"T{len(tasks)+1}",
                agent_type="coder",
                task=f"实现: {task}",
                domain=Domain.EXECUTION,
                dependencies=[tasks[-1].task_id] if tasks else [],
            ))

        if any(k in task_lower for k in ["审查", "review", "检查"]):
            tasks.append(OrchestratedTask(
                task_id=f"T{len(tasks)+1}",
                agent_type="reviewer",
                task=f"审查: {task}",
                domain=Domain.REVIEW,
                dependencies=[tasks[-1].task_id] if tasks else [],
            ))

        if any(k in task_lower for k in ["调试", "修复", "debug", "fix"]):
            tasks.append(OrchestratedTask(
                task_id=f"T{len(tasks)+1}",
                agent_type="debugger",
                task=f"调试: {task}",
                domain=Domain.DEBUG,
            ))

        # 默认执行任务
        if not tasks:
            tasks.append(OrchestratedTask(
                task_id=f"T{len(tasks)+1}",
                agent_type="coder",
                task=task,
                domain=Domain.EXECUTION,
            ))

        # 添加到orchestrator
        for t in tasks:
            self.orchestrator.add_task(t)

        return tasks

    def select_agent_for_task(self, task: OrchestratedTask) -> Optional[str]:
        """为任务选择最佳Agent"""
        return self.registry.select_best_agent(task.domain)

    def execute_with_consensus(self, task: OrchestratedTask,
                               mode: ConsensusMode = ConsensusMode.MAJORITY) -> bool:
        """
        使用共识执行任务

        Returns:
            是否成功
        """
        # 获取同domain的agents
        agents = self.registry.get_agents_by_domain(task.domain)
        if not agents:
            agents = self.registry.get_available_agents()
        if not agents:
            return False

        # 投票
        proposal = f"Execute task {task.task_id} with {task.agent_type}"
        accepted, votes = self.consensus.vote(agents, proposal, mode)

        if not accepted:
            return False

        # 执行
        return True

    def get_bottlenecks(self) -> List[str]:
        """检测瓶颈 (某domain任务堆积)"""
        domain_counts: Dict[Domain, int] = defaultdict(int)
        for task in self.orchestrator._tasks.values():
            if task.state == TaskState.IN_PROGRESS:
                domain_counts[task.domain] += 1

        bottlenecks: List[str] = []
        for domain, count in domain_counts.items():
            if count > 3:  # 阈值
                bottlenecks.append(f"{domain.value}: {count} tasks")

        return bottlenecks


# ============================================================================
# Agent Executor (实际执行逻辑)
# ============================================================================

class AgentStatus(Enum):
    """Agent执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class AgentTask:
    """Agent任务"""
    agent_type: str
    task: str
    context: Optional[Dict[str, Any]] = None
    timeout: int = 300
    priority: int = 0


@dataclass
class AgentResult:
    """Agent执行结果"""
    agent_type: str
    task: str
    status: AgentStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    duration: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "task": self.task,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "duration": self.duration,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class AgentDefinition:
    """Agent定义"""
    name: str
    description: str
    responsibility: str
    phase: str
    triggers: List[str]
    tools: List[str]

    @classmethod
    def from_file(cls, path: Path) -> Optional[AgentDefinition]:
        """从文件加载Agent定义"""
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8")
        name = path.stem
        description = ""
        responsibility = ""
        phase = ""
        triggers: List[str] = []
        tools: List[str] = []

        import re
        desc_match = re.search(r'description:\s*\|?\s*\n((?:[ \t]+.+\n?)+)', content)
        if desc_match:
            description = desc_match.group(1).strip()

        resp_match = re.search(r'responsibility:\s*([^\n]+)', content)
        if resp_match:
            responsibility = resp_match.group(1).strip()

        phase_match = re.search(r'phase:\s*([^\n]+)', content)
        if phase_match:
            phase = phase_match.group(1).strip()

        return cls(
            name=name,
            description=description,
            responsibility=responsibility,
            phase=phase,
            triggers=triggers,
            tools=tools,
        )


class AgentSpawner:
    """
    Agent编排器 (v2.0)

    支持:
    - 领域路由
    - 并行/串行执行
    - 共识执行
    - 回滚机制
    """

    def __init__(self, workdir: str = "."):
        self.workdir = Path(workdir)
        self.agents_dir = self.workdir / AGENTS_DIR
        self._agent_definitions: Dict[str, AgentDefinition] = {}
        self.coordinator = QueenCoordinator(workdir)
        self._load_agent_definitions()

    def _load_agent_definitions(self):
        """加载所有Agent定义"""
        if not self.agents_dir.exists():
            return

        for agent_file in self.agents_dir.glob("*.md"):
            if agent_file.stem == "README":
                continue
            definition = AgentDefinition.from_file(agent_file)
            if definition:
                self._agent_definitions[definition.name] = definition

    def get_agent_definition(self, agent_type: str) -> Optional[AgentDefinition]:
        """获取指定Agent的定义"""
        return self._agent_definitions.get(agent_type)

    def list_agents(self) -> List[AgentDefinition]:
        """列出所有可用Agent"""
        return list(self._agent_definitions.values())

    def spawn_by_domain(self, domain: Domain, task: str,
                        context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """领域路由执行"""
        best_agent = self.coordinator.registry.select_best_agent(domain)
        if not best_agent:
            # 降级到通用agent
            best_agent = domain.value

        return self.spawn(AgentTask(best_agent, task, context))

    def spawn(self, task: AgentTask,
              context: Optional[Dict[str, Any]] = None) -> AgentResult:
        """派发单个Agent任务"""
        start_time = time.time()
        started_at = datetime.now().isoformat()

        definition = self.get_agent_definition(task.agent_type)

        result = AgentResult(
            agent_type=task.agent_type,
            task=task.task,
            status=AgentStatus.RUNNING,
            started_at=started_at,
        )

        try:
            instruction = self._build_instruction(task, context, definition)
            agent_output = self._execute_agent(task, instruction)

            result.status = AgentStatus.COMPLETED
            result.result = agent_output
            result.completed_at = datetime.now().isoformat()

        except Exception as e:
            result.status = AgentStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.now().isoformat()

        result.duration = time.time() - start_time
        return result

    def spawn_parallel(self, tasks: List[AgentTask],
                      context: Optional[Dict[str, Any]] = None,
                      max_workers: int = 3) -> List[AgentResult]:
        """并行派发多个Agent任务"""
        sorted_tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)
        results: List[AgentResult] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_task = {
                executor.submit(self.spawn, task, context): task
                for task in sorted_tasks
            }

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(AgentResult(
                        agent_type=task.agent_type,
                        task=task.task,
                        status=AgentStatus.FAILED,
                        error=str(e),
                    ))

        return results

    def spawn_sequential(self, tasks: List[AgentTask],
                        context: Optional[Dict[str, Any]] = None) -> List[AgentResult]:
        """串行派发多个Agent任务"""
        results: List[AgentResult] = []

        for task in tasks:
            result = self.spawn(task, context)
            results.append(result)
            if result.status == AgentStatus.FAILED:
                break

        return results

    def spawn_with_orchestration(self, task_description: str,
                                 use_consensus: bool = True,
                                 consensus_mode: ConsensusMode = ConsensusMode.MAJORITY) -> Dict[str, Any]:
        """
        完整编排流程 (借鉴 ruflo)

        1. 分解任务
        2. 拓扑排序
        3. 共识执行
        4. 回滚机制
        """
        # 1. 分解
        _ = self.coordinator.decompose_task(task_description)

        # 2. 拓扑排序
        try:
            exec_order = self.coordinator.orchestrator.get_execution_order()
        except CycleDetectedError as e:
            return {
                "status": "failed",
                "error": str(e),
                "phase": "cycle_detection",
            }

        # 3. 执行
        results: Dict[str, Dict[str, Any]] = {}
        for task_id in exec_order:
            task = self.coordinator.orchestrator._tasks[task_id]

            # 共识
            if use_consensus:
                if not self.coordinator.execute_with_consensus(task, consensus_mode):
                    # 回滚
                    rollback_order = self.coordinator.orchestrator.get_rollback_order()
                    return {
                        "status": "rolled_back",
                        "failed_task": task_id,
                        "rollback_order": rollback_order,
                        "partial_results": results,
                    }

            # 执行
            agent_task = AgentTask(task.agent_type, task.task, task.context)
            result = self.spawn(agent_task)

            self.coordinator.orchestrator.mark_completed(
                task_id,
                result=result.to_dict(),
                error=result.error,
            )
            results[task_id] = result.to_dict()

        return {
            "status": "completed",
            "results": results,
            "execution_order": exec_order,
        }

    def _build_instruction(self, task: AgentTask,
                          context: Optional[Dict[str, Any]],
                          definition: Optional[AgentDefinition]) -> str:
        """构建Agent执行指令"""
        instruction_parts = []

        if definition:
            instruction_parts.append(f"## Agent: {definition.name}")
            instruction_parts.append(f"## Responsibility: {definition.responsibility}")
            if definition.description:
                instruction_parts.append(f"## Description: {definition.description}")
            instruction_parts.append("")

        instruction_parts.append("## Task")
        instruction_parts.append(task.task)
        instruction_parts.append("")

        if context:
            instruction_parts.append("## Context")
            instruction_parts.append(json.dumps(context, ensure_ascii=False, indent=2))
            instruction_parts.append("")

        return "\n".join(instruction_parts)

    def _execute_agent(self, task: AgentTask, instruction: str) -> Dict[str, Any]:
        """执行Agent (模拟)"""
        time.sleep(0.1)
        return {
            "agent_type": task.agent_type,
            "task": task.task,
            "status": "completed",
            "instruction": instruction,
            "output": f"Mock output for {task.agent_type}: {task.task}",
        }


# ============================================================================
# MultiAgentCoordinator - 预定义工作流
# ============================================================================

class MultiAgentCoordinator:
    """
    多Agent协调器 (v2.0)

    使用Queen Coordinator的领域路由和共识机制
    """

    def __init__(self, workdir: str = "."):
        self.workdir = Path(workdir)
        self.spawner = AgentSpawner(workdir)
        self.session_id = f"ma{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.results: List[AgentResult] = []

    def run_research_and_plan(self, query: str) -> Dict[str, Any]:
        """执行研究+规划流程"""
        result = self.spawner.spawn_with_orchestration(
            f"研究并规划: {query}",
            use_consensus=True,
            consensus_mode=ConsensusMode.MAJORITY,
        )
        return {
            "session_id": self.session_id,
            "query": query,
            "result": result,
        }

    def run_code_and_review(self, task_description: str) -> Dict[str, Any]:
        """执行代码+审查流程"""
        result = self.spawner.spawn_with_orchestration(
            f"实现并审查: {task_description}",
            use_consensus=True,
            consensus_mode=ConsensusMode.SUPERMAJORITY,
        )
        return {
            "session_id": self.session_id,
            "task": task_description,
            "result": result,
        }

    def run_debug_and_fix(self, bug_description: str) -> Dict[str, Any]:
        """执行调试+修复流程"""
        result = self.spawner.spawn_with_orchestration(
            f"调试并修复: {bug_description}",
            use_consensus=True,
            consensus_mode=ConsensusMode.MAJORITY,
        )
        return {
            "session_id": self.session_id,
            "bug": bug_description,
            "result": result,
        }


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Agent Spawner v2.0")
    parser.add_argument("--workdir", default=".", help="workspace directory")
    parser.add_argument("--op", choices=[
        "list", "spawn", "spawn-domain", "orchestrate",
        "research-plan", "code-review", "debug-fix",
        "health", "consensus-test"
    ], required=True)
    parser.add_argument("--agent-type", help="agent type to spawn")
    parser.add_argument("--domain", help="domain for domain-based routing")
    parser.add_argument("--task", help="task description")
    parser.add_argument("--mode", choices=["parallel", "sequential"], default="parallel")
    parser.add_argument("--consensus", choices=["majority", "supermajority", "unanimous", "weighted", "queen"], default="majority")
    args = parser.parse_args()

    spawner = AgentSpawner(args.workdir)

    if args.op == "list":
        agents = spawner.list_agents()
        print(f"Available agents ({len(agents)}):")
        for agent in agents:
            print(f"  - {agent.name}: {agent.responsibility}")
        return 0

    if args.op == "health":
        registry = spawner.coordinator.registry
        print("Agent Registry Status:")
        for name in registry.get_available_agents():
            scores = registry.score_agent(name)
            print(f"  - {name}: scores={scores}")
        bottlenecks = spawner.coordinator.get_bottlenecks()
        if bottlenecks:
            print(f"Bottlenecks: {bottlenecks}")
        return 0

    if args.op == "consensus-test":
        agents = spawner.coordinator.registry.get_available_agents()
        if not agents:
            print("No agents available for consensus test")
            return 1

        mode = ConsensusMode(args.consensus)
        accepted, votes = spawner.coordinator.consensus.vote(
            agents[:3],
            f"Test proposal at {datetime.now().isoformat()}",
            mode,
        )
        print(f"Consensus test ({mode.value}): accepted={accepted}")
        for v in votes:
            print(f"  - {v.agent}: decision={v.decision}, weight={v.weight:.2f}")
        return 0

    if args.op == "spawn":
        if not args.agent_type or not args.task:
            print("错误: --agent-type and --task required")
            return 1

        task = AgentTask(args.agent_type, args.task)
        result = spawner.spawn(task)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.op == "spawn-domain":
        if not args.domain or not args.task:
            print("错误: --domain and --task required")
            return 1

        domain = Domain(args.domain)
        result = spawner.spawn_by_domain(domain, args.task)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.op == "orchestrate":
        if not args.task:
            print("错误: --task required")
            return 1

        mode = ConsensusMode(args.consensus)
        result = spawner.spawn_with_orchestration(args.task, use_consensus=True, consensus_mode=mode)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "research-plan":
        if not args.task:
            print("错误: --task required")
            return 1

        coordinator = MultiAgentCoordinator(args.workdir)
        result = coordinator.run_research_and_plan(args.task)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "code-review":
        if not args.task:
            print("错误: --task required")
            return 1

        coordinator = MultiAgentCoordinator(args.workdir)
        result = coordinator.run_code_and_review(args.task)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "debug-fix":
        if not args.task:
            print("错误: --task required")
            return 1

        coordinator = MultiAgentCoordinator(args.workdir)
        result = coordinator.run_debug_and_fix(args.task)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
