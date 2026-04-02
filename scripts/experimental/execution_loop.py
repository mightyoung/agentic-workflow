#!/usr/bin/env python3
"""
Execution Loop - 执行循环机制

借鉴最佳实践设计:

1. ReAct Pattern (Reason + Act)
   - Thought -> Action -> Observation -> Thought -> ...
   - 论文: Yao et al., 2022

2. Plan-and-Execute Pattern
   - Planner先生成完整计划
   - Executor执行任务
   - 必要时Replanner调整剩余计划
   - 支持重规划和并行执行

3. Reflexion Pattern (verbal reinforcement)
   - Actor: 生成初始响应
   - Reflector: 评估轨迹质量
   - Self-Reflection: 生成改进反馈
   - 记忆增强

4. Loop Prevention
   - max_iterations: 最大迭代次数
   - max_steps_per_phase: 每个phase最大步数
   - budget_seconds: 时间预算
   - stop_signals: 停止信号检测

用法:
    from execution_loop import ExecutionLoop, LoopMode

    loop = ExecutionLoop(workdir)
    result = loop.run("实现一个REST API")

    # 或使用Plan-and-Execute模式
    loop = ExecutionLoop(workdir, mode=LoopMode.PLAN_AND_EXECUTE)
    result = loop.run("实现一个REST API")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple



# ============================================================================
# Loop Mode Definition
# ============================================================================

class LoopMode(Enum):
    """执行循环模式"""
    # 迭代模式: 边做边想 (ReAct)
    ITERATIVE = "iterative"

    # 计划执行模式: 先计划后执行 (Plan-and-Execute)
    PLAN_AND_EXECUTE = "plan_and_execute"

    # 反射模式: 自我反思改进 (Reflexion)
    REFLEXION = "reflexion"

    # 混合模式: 根据任务复杂度自动选择
    ADAPTIVE = "adaptive"


# ============================================================================
# Loop State and Step Records
# ============================================================================

class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class LoopStep:
    """循环步骤"""
    step_id: str
    phase: str
    thought: str = ""           # Thought: 当前想法
    action: str = ""            # Action: 要执行的动作
    observation: str = ""       # Observation: 执行结果
    reflection: str = ""        # Reflection: 反思反馈
    status: StepStatus = StepStatus.PENDING
    error: Optional[str] = None
    duration: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


@dataclass
class LoopConfig:
    """循环配置"""
    mode: LoopMode = LoopMode.ITERATIVE
    max_iterations: int = 50          # 最大迭代次数
    max_steps_per_phase: int = 20     # 每个phase最大步数
    budget_seconds: float = 600       # 时间预算 (10分钟)
    confidence_threshold: float = 0.8  # 置信度阈值
    enable_reflection: bool = True    # 是否启用反思
    enable_replan: bool = True        # 是否启用重规划
    early_stop_on_success: bool = True # 成功后提前停止


@dataclass
class LoopResult:
    """循环执行结果"""
    status: str  # completed, failed, timeout, max_iterations
    final_phase: str
    steps: List[LoopStep]
    total_iterations: int
    total_duration: float
    error: Optional[str] = None
    trajectory: Optional[Dict[str, Any]] = None


# ============================================================================
# Reflection Engine
# ============================================================================

class ReflectionEngine:
    """
    反思引擎 (Reflexion Pattern)

    基于已有经验生成改进反馈
    """

    def __init__(self):
        self.experience_store: List[Dict[str, Any]] = []

    def reflect(
        self,
        step: LoopStep,
        context: Dict[str, Any],
    ) -> str:
        """
        生成反思反馈

        Args:
            step: 当前步骤
            context: 执行上下文

        Returns:
            反思反馈字符串
        """
        reflections = []

        # 基于状态生成反馈
        if step.status == StepStatus.FAILED:
            reflections.append(f"步骤 {step.step_id} 失败: {step.error}")

            # 检查是否重复失败
            recent_failures = [
                s for s in context.get("recent_steps", [])
                if s.status == StepStatus.FAILED
            ]
            if len(recent_failures) >= 2:
                reflections.append("检测到连续失败，考虑换一种方法")

        elif step.status == StepStatus.COMPLETED:
            reflections.append(f"步骤 {step.step_id} 完成")

            # 检查是否有改进空间
            if step.duration > 30:
                reflections.append("执行时间较长，可考虑优化")

        # 基于观察生成反馈
        if step.observation:
            obs_lower = step.observation.lower()
            if "error" in obs_lower or "failed" in obs_lower:
                reflections.append("观察到错误，需要调整策略")
            elif "success" in obs_lower or "completed" in obs_lower:
                reflections.append("执行成功，可继续推进")

        return " | ".join(reflections) if reflections else "继续执行"

    def add_experience(self, experience: Dict[str, Any]):
        """添加经验到存储"""
        self.experience_store.append({
            **experience,
            "timestamp": datetime.now().isoformat(),
        })

    def get_relevant_experience(self, task: str, limit: int = 3) -> List[Dict[str, Any]]:
        """获取相关经验"""
        # 简单关键词匹配
        task_lower = task.lower()
        relevant = []

        for exp in reversed(self.experience_store):
            exp_task = exp.get("task", "").lower()
            if any(k in exp_task for k in task_lower.split() if len(k) > 3):
                relevant.append(exp)
                if len(relevant) >= limit:
                    break

        return relevant


# ============================================================================
# Plan and Execute Engine
# ============================================================================

class PlanExecuteEngine:
    """
    计划执行引擎 (Plan-and-Execute Pattern)

    1. Planner 生成完整任务计划
    2. Executor 按序执行任务
    3. Replanner 必要时调整计划
    """

    def __init__(self, executor: Callable):
        self.executor = executor
        self.plan: List[Dict[str, Any]] = []
        self.executed_count = 0

    def create_plan(self, task: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成任务计划

        Args:
            task: 任务描述
            context: 执行上下文

        Returns:
            计划列表 [{step_id, action, depends_on, estimated_duration}]
        """
        # 简单的基于关键词的计划生成
        plan = []

        task_lower = task.lower()

        # 基础步骤
        if any(k in task_lower for k in ["搜索", "研究", "调研"]):
            plan.append({"step_id": "P1", "action": "RESEARCH", "depends_on": [], "estimated_duration": 60})

        if any(k in task_lower for k in ["分析", "思考", "理解"]):
            plan.append({"step_id": "P2", "action": "THINKING", "depends_on": ["P1"] if plan else [], "estimated_duration": 60})

        if any(k in task_lower for k in ["计划", "规划", "设计"]):
            plan.append({"step_id": "P3", "action": "PLANNING", "depends_on": ["P2"] if "P2" in [p["step_id"] for p in plan] else [], "estimated_duration": 90})

        if any(k in task_lower for k in ["实现", "开发", "写", "创建"]):
            plan.append({"step_id": "P4", "action": "EXECUTING", "depends_on": ["P3"] if "P3" in [p["step_id"] for p in plan] else [], "estimated_duration": 300})

        if any(k in task_lower for k in ["审查", "检查", "review"]):
            plan.append({"step_id": "P5", "action": "REVIEWING", "depends_on": ["P4"] if "P4" in [p["step_id"] for p in plan] else [], "estimated_duration": 120})

        if any(k in task_lower for k in ["优化", "完善", "精炼"]):
            plan.append({"step_id": "P6", "action": "REFINING", "depends_on": ["P5"] if "P5" in [p["step_id"] for p in plan] else [], "estimated_duration": 60})

        # 如果没有匹配，使用默认步骤
        if not plan:
            plan = [
                {"step_id": "P1", "action": "THINKING", "depends_on": [], "estimated_duration": 60},
                {"step_id": "P2", "action": "PLANNING", "depends_on": ["P1"], "estimated_duration": 90},
                {"step_id": "P3", "action": "EXECUTING", "depends_on": ["P2"], "estimated_duration": 300},
                {"step_id": "P4", "action": "REVIEWING", "depends_on": ["P3"], "estimated_duration": 120},
            ]

        self.plan = plan
        return plan

    def replan(self, completed_step: LoopStep, remaining_plan: List[Dict]) -> List[Dict[str, Any]]:
        """
        重新规划 (仅在需要时调用)

        Args:
            completed_step:刚完成的步骤
            remaining_plan: 剩余计划

        Returns:
            调整后的计划
        """
        # 如果失败，添加调试步骤
        if completed_step.status == StepStatus.FAILED:
            debug_step = {
                "step_id": f"DEBUG_{completed_step.step_id}",
                "action": "DEBUGGING",
                "depends_on": [completed_step.step_id],
                "estimated_duration": 120,
            }
            return [debug_step] + remaining_plan

        # 如果成功，继续原计划
        return remaining_plan

    def get_next_executable(self) -> Optional[Dict[str, Any]]:
        """获取下一个可执行的任务"""
        executed_ids = set()
        for i in range(self.executed_count):
            if i < len(self.plan):
                executed_ids.add(self.plan[i]["step_id"])

        for step in self.plan:
            if step["step_id"] not in executed_ids:
                deps_met = all(dep in executed_ids for dep in step["depends_on"])
                if deps_met:
                    return step

        return None


# ============================================================================
# Main Execution Loop
# ============================================================================

class ExecutionLoop:
    """
    执行循环 (Execution Loop)

    支持三种模式:
    1. ITERATIVE: 边做边想 (ReAct)
    2. PLAN_AND_EXECUTE: 先计划后执行
    3. REFLEXION: 自我反思改进

    核心功能:
    - 步骤追踪
    - 循环保护 (max_iterations, budget)
    - 反思机制
    - 计划重规划
    - 轨迹记录
    """

    def __init__(
        self,
        workdir: str = ".",
        config: Optional[LoopConfig] = None,
        use_real_agent: bool = False,
    ):
        self.workdir = Path(workdir)
        self.config = config or LoopConfig()
        self.reflection_engine = ReflectionEngine()
        self._steps: List[LoopStep] = []
        self._phase_steps: Dict[str, int] = {}  # phase -> step count
        self._start_time: Optional[float] = None
        self._current_phase: str = "IDLE"
        self.use_real_agent = use_real_agent
        self._subagent_runner = None

    def _should_stop(self) -> Tuple[bool, str]:
        """
        检查是否应该停止循环

        Returns:
            (should_stop, reason)
        """
        # 检查迭代次数
        if len(self._steps) >= self.config.max_iterations:
            return True, f"达到最大迭代次数 ({self.config.max_iterations})"

        # 检查时间预算
        if self._start_time:
            elapsed = time.time() - self._start_time
            if elapsed >= self.config.budget_seconds:
                return True, f"达到时间预算 ({self.config.budget_seconds}s)"

        # 检查每个phase的步数
        if self._phase_steps.get(self._current_phase, 0) >= self.config.max_steps_per_phase:
            return True, f"Phase {self._current_phase} 达到最大步数 ({self.config.max_steps_per_phase})"

        return False, ""

    def _create_step(self, phase: str, thought: str = "", action: str = "") -> LoopStep:
        """创建新步骤"""
        step_id = f"S{len(self._steps) + 1}_{phase}"
        return LoopStep(
            step_id=step_id,
            phase=phase,
            thought=thought,
            action=action,
        )

    def _update_phase_tracking(self, phase: str):
        """更新phase追踪"""
        self._current_phase = phase
        self._phase_steps[phase] = self._phase_steps.get(phase, 0) + 1

    def _build_context(self) -> Dict[str, Any]:
        """构建执行上下文"""
        return {
            "steps": self._steps[-10:],  # 最近10步
            "recent_steps": [s for s in self._steps[-5:] if s.status == StepStatus.FAILED],
            "phase_steps": dict(self._phase_steps),
            "total_iterations": len(self._steps),
            "config": {
                "mode": self.config.mode.value,
                "max_iterations": self.config.max_iterations,
                "budget_seconds": self.config.budget_seconds,
            }
        }

    def _execute_iterative(
        self,
        task: str,
        initial_phase: str,
        executor: Callable[[str, LoopStep], LoopStep],
    ) -> LoopResult:
        """
        迭代模式 (ReAct)

        Thought -> Action -> Observation -> Thought -> ...
        """
        self._start_time = time.time()
        phase = initial_phase
        iteration = 0

        while iteration < self.config.max_iterations:
            # 检查停止条件
            should_stop, reason = self._should_stop()
            if should_stop:
                return LoopResult(
                    status="max_iterations" if "迭代" in reason else "timeout",
                    final_phase=phase,
                    steps=self._steps,
                    total_iterations=iteration,
                    total_duration=time.time() - self._start_time,
                    error=reason,
                )

            # 创建步骤
            step = self._create_step(phase, thought=f"思考: {task}")
            step.action = f"execute_{phase}"
            step.status = StepStatus.RUNNING

            self._update_phase_tracking(phase)
            self._steps.append(step)

            # 执行
            start_time = time.time()
            try:
                step = executor(phase, step)
                step.status = StepStatus.COMPLETED
            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = str(e)

            step.duration = time.time() - start_time
            step.completed_at = datetime.now().isoformat()

            # 反思 (Reflexion)
            if self.config.enable_reflection:
                context = self._build_context()
                step.reflection = self.reflection_engine.reflect(step, context)

            # 判断下一步
            if step.status == StepStatus.FAILED:
                # 失败: 尝试调试或继续
                phase = "DEBUGGING"
            elif phase == "COMPLETE":
                # 显式完成
                break
            elif step.observation and ("任务完成" in step.observation or "全部完成" in step.observation):
                # 显式标记完成
                phase = "COMPLETE"
                break
            else:
                # 继续下一个phase
                phase = self._get_next_phase(phase)

            iteration += 1

        return LoopResult(
            status="completed" if phase == "COMPLETE" else "incomplete",
            final_phase=phase,
            steps=self._steps,
            total_iterations=iteration,
            total_duration=time.time() - self._start_time,
        )

    def _execute_plan_and_execute(
        self,
        task: str,
        executor: Callable[[str, LoopStep], LoopStep],
    ) -> LoopResult:
        """
        计划执行模式 (Plan-and-Execute)

        1. Planner 生成计划
        2. Executor 执行任务
        3. Replanner 必要时调整
        """
        self._start_time = time.time()

        # 创建计划引擎
        plan_engine = PlanExecuteEngine(executor)

        # 生成计划
        plan = plan_engine.create_plan(task, self._build_context())

        # 执行计划
        current_idx = 0
        total_executed = 0

        while current_idx < len(plan):
            # 检查停止条件
            should_stop, reason = self._should_stop()
            if should_stop:
                return LoopResult(
                    status="max_iterations" if "迭代" in reason else "timeout",
                    final_phase=plan[current_idx]["action"],
                    steps=self._steps,
                    total_iterations=total_executed,
                    total_duration=time.time() - self._start_time,
                    error=reason,
                )

            # 获取当前任务
            current_task = plan[current_idx]
            phase = current_task["action"]

            # 创建并执行步骤
            step = self._create_step(phase, thought=f"计划: {current_task['step_id']}")
            step.action = current_task["step_id"]
            step.status = StepStatus.RUNNING

            self._update_phase_tracking(phase)
            self._steps.append(step)

            start_time = time.time()
            try:
                step = executor(phase, step)
                step.status = StepStatus.COMPLETED
            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = str(e)

            step.duration = time.time() - start_time
            step.completed_at = datetime.now().isoformat()

            # 如果失败且启用重规划
            if step.status == StepStatus.FAILED and self.config.enable_replan:
                remaining = plan[current_idx:]
                plan = plan_engine.replan(step, remaining)

            total_executed += 1
            current_idx += 1

        return LoopResult(
            status="completed",
            final_phase=plan[-1]["action"] if plan else "COMPLETE",
            steps=self._steps,
            total_iterations=total_executed,
            total_duration=time.time() - self._start_time,
        )

    def _execute_reflexion(
        self,
        task: str,
        executor: Callable[[str, LoopStep], LoopStep],
    ) -> LoopResult:
        """
        反思模式 (Reflexion)

        基于自我反思进行迭代改进
        """
        self._start_time = time.time()
        best_result: Optional[LoopStep] = None
        best_score = 0.0
        no_improvement_count = 0
        max_no_improvement = 3

        phase = "THINKING"
        iteration = 0

        while iteration < self.config.max_iterations:
            # 检查停止条件
            should_stop, reason = self._should_stop()
            if should_stop:
                return LoopResult(
                    status="max_iterations",
                    final_phase=phase,
                    steps=self._steps,
                    total_iterations=iteration,
                    total_duration=time.time() - self._start_time,
                    error=reason,
                )

            # 创建步骤
            step = self._create_step(phase, thought=f"反思: {task}")
            step.action = f"reflexion_{phase}"
            step.status = StepStatus.RUNNING

            self._update_phase_tracking(phase)
            self._steps.append(step)

            start_time = time.time()
            try:
                step = executor(phase, step)
                step.status = StepStatus.COMPLETED

                # 评估结果
                score = self._evaluate_result(step)
                if score > best_score:
                    best_score = score
                    best_result = step
                    no_improvement_count = 0
                else:
                    no_improvement_count += 1

            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = str(e)
                no_improvement_count += 1

            step.duration = time.time() - start_time
            step.completed_at = datetime.now().isoformat()

            # 反思
            context = self._build_context()
            step.reflection = self.reflection_engine.reflect(step, context)

            # 如果多次无改进，尝试换方法
            if no_improvement_count >= max_no_improvement:
                if phase == "THINKING":
                    phase = "PLANNING"
                elif phase == "PLANNING":
                    phase = "EXECUTING"
                no_improvement_count = 0

            iteration += 1

        return LoopResult(
            status="completed",
            final_phase=phase,
            steps=self._steps,
            total_iterations=iteration,
            total_duration=time.time() - self._start_time,
            trajectory={"best_score": best_score, "best_result": self._step_to_dict(best_result) if best_result else None} if best_result else None,
        )

    def _get_next_phase(self, current: str) -> str:
        """获取下一个phase"""
        transitions = {
            "THINKING": "PLANNING",
            "PLANNING": "EXECUTING",
            "EXECUTING": "REVIEWING",
            "REVIEWING": "REFINING",
            "REFINING": "COMPLETE",
            "DEBUGGING": "EXECUTING",
        }
        return transitions.get(current, "COMPLETE")

    def _evaluate_result(self, step: LoopStep) -> float:
        """评估结果质量 (0-1)"""
        score = 0.5

        if step.status == StepStatus.COMPLETED:
            score += 0.3

        if step.observation:
            if "成功" in step.observation or "完成" in step.observation:
                score += 0.2

        return min(score, 1.0)

    def _step_to_dict(self, step: LoopStep) -> Dict[str, Any]:
        """将步骤转换为字典"""
        return {
            "step_id": step.step_id,
            "phase": step.phase,
            "thought": step.thought,
            "action": step.action,
            "observation": step.observation,
            "reflection": step.reflection,
            "status": step.status.value,
            "error": step.error,
            "duration": step.duration,
        }

    def run(
        self,
        task: str,
        initial_phase: str = "THINKING",
        executor: Optional[Callable[[str, LoopStep], LoopStep]] = None,
    ) -> LoopResult:
        """
        运行执行循环

        Args:
            task: 任务描述
            initial_phase: 初始phase
            executor: 执行器函数 (phase, step) -> step

        Returns:
            LoopResult
        """
        # 选择执行器：用户提供的 > 真实AI > 模拟
        if executor is None:
            if self.use_real_agent:
                executor = self._real_executor
            else:
                executor = self._default_executor

        # 根据模式执行
        if self.config.mode == LoopMode.ITERATIVE:
            return self._execute_iterative(task, initial_phase, executor)
        elif self.config.mode == LoopMode.PLAN_AND_EXECUTE:
            return self._execute_plan_and_execute(task, executor)
        elif self.config.mode == LoopMode.REFLEXION:
            return self._execute_reflexion(task, executor)
        else:  # ADAPTIVE
            # 根据任务复杂度自动选择
            task_words = len(task.split())
            if task_words > 50:
                # 复杂任务用计划执行
                return self._execute_plan_and_execute(task, executor)
            else:
                # 简单任务用迭代
                return self._execute_iterative(task, initial_phase, executor)

    def _default_executor(self, phase: str, step: LoopStep) -> LoopStep:
        """默认执行器 (模拟)"""
        time.sleep(0.1)  # 模拟执行

        step.observation = f"{phase} 执行完成"
        return step

    def _get_real_executor(self):
        """Get or create a real executor using SubAgentRunner."""
        if self._subagent_runner is not None:
            return self._subagent_runner

        try:
            from subagent_runner import SubAgentRunner
            self._subagent_runner = SubAgentRunner(workdir=str(self.workdir))
        except ImportError:
            self._subagent_runner = None
        return self._subagent_runner

    def _real_executor(self, phase: str, step: LoopStep) -> LoopStep:
        """Real executor using SubAgentRunner for actual AI execution."""
        runner = self._get_real_executor()
        if runner is None:
            step.observation = "SubAgentRunner not available - falling back to mock"
            return self._default_executor(phase, step)

        # Use step.action as the task
        task = step.action or step.thought or f"Execute {phase}"

        try:
            result = runner.run(
                phase=phase,
                task=task,
                session_id=step.step_id,
            )
            if result.success:
                step.observation = result.output
                step.status = StepStatus.COMPLETED
            else:
                step.observation = f"Error: {result.error}"
                step.status = StepStatus.FAILED
                step.error = result.error
        except Exception as e:
            step.observation = f"Exception: {str(e)}"
            step.status = StepStatus.FAILED
            step.error = str(e)

        return step

    def get_trajectory(self) -> Dict[str, Any]:
        """获取执行轨迹"""
        return {
            "task": getattr(self, "_task", ""),
            "mode": self.config.mode.value,
            "steps": [
                {
                    "step_id": s.step_id,
                    "phase": s.phase,
                    "thought": s.thought,
                    "action": s.action,
                    "observation": s.observation,
                    "reflection": s.reflection,
                    "status": s.status.value,
                    "duration": s.duration,
                    "error": s.error,
                }
                for s in self._steps
            ],
            "phase_steps": self._phase_steps,
            "total_iterations": len(self._steps),
        }


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Execution Loop - 执行循环")
    parser.add_argument("--task", help="任务描述")
    parser.add_argument("--mode", choices=["iterative", "plan_and_execute", "reflexion", "adaptive"], default="adaptive")
    parser.add_argument("--max-iterations", type=int, default=50)
    parser.add_argument("--budget-seconds", type=float, default=600)
    parser.add_argument("--workdir", default=".")
    args = parser.parse_args()

    config = LoopConfig(
        mode=LoopMode(args.mode),
        max_iterations=args.max_iterations,
        budget_seconds=args.budget_seconds,
    )

    loop = ExecutionLoop(args.workdir, config)

    task = args.task or "实现一个简单的计算器"
    print(f"Executing task: {task}")
    print(f"Mode: {config.mode.value}")
    print("-" * 50)

    result = loop.run(task)

    print("\n结果:")
    print(f"  Status: {result.status}")
    print(f"  Final Phase: {result.final_phase}")
    print(f"  Iterations: {result.total_iterations}")
    print(f"  Duration: {result.total_duration:.2f}s")
    print(f"  Steps: {len(result.steps)}")

    print("\n执行轨迹:")
    for step in result.steps:
        status_icon = {
            StepStatus.COMPLETED: "✅",
            StepStatus.FAILED: "❌",
            StepStatus.RUNNING: "🔄",
            StepStatus.PENDING: "⏳",
        }.get(step.status, "❓")
        print(f"  {status_icon} {step.step_id} [{step.phase}]: {step.observation or step.error or step.thought}")


if __name__ == "__main__":
    raise SystemExit(main())
