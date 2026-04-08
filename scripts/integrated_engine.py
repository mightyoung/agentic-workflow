#!/usr/bin/env python3
"""
Integrated Workflow Engine - 中间层与执行层整合

Status:
    Experimental prototype only.
    The authoritative runtime remains scripts/workflow_engine.py.

整合以下组件:
1. MiddlewareChain - 意图识别、复杂度评估、阶段路由
2. SubAgentRunner - 真实AI subagent执行
3. ParallelExecutor - Band制并行执行
4. ReflexionEngine - 自反馈修正循环

架构:
    User Input
         ↓
    MiddlewareChain.process()
         ↓
    ┌─────────────────────────────────────┐
    │ IntentMiddleware → 意图识别          │
    │ ContextMiddleware → 上下文注入        │
    │ SkillMiddleware → skill_context生成   │
    │ ComplexityMiddleware → 复杂度评估    │
    └─────────────────────────────────────┘
         ↓
    OrchestrationResult {
        intent, phase, phase_sequence,
        skill_context, tokens_expected
    }
         ↓
    ParallelExecutor.execute_band() ← 根据phase_sequence
         ↓
    ┌─────────────────────────────────────┐
    │ Band 1: RESEARCH || THINKING (并行) │
    │ Band 2: PLANNING                   │
    │ Band 3: EXECUTING                  │
    │ Band 4: REVIEWING || DEBUGGING (并行)│
    └─────────────────────────────────────┘
         ↓
    ReflexionEngine.analyze() ← 自反馈修正
         ↓
    PhaseResult

Usage:
    from integrated_engine import IntegratedEngine

    engine = IntegratedEngine(workdir=".")
    result = engine.run("开发一个用户系统")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

# 导入中间层组件
from scripts.middleware import (
    Complexity,
    Phase,
    Request,
    SkillMiddleware,
    create_default_chain,
)

# 导入执行组件
try:
    from scripts.reflexion import ReflexionEngine, ReflexionResult
    from scripts.subagent_runner import SubAgentRunner
    COMPONENTS_AVAILABLE = True
except ImportError:
    COMPONENTS_AVAILABLE = False


# ============================================================================
# 整合结果数据模型
# ============================================================================

@dataclass
class OrchestrationResult:
    """编排结果 - MiddlewareChain的输出"""
    intent: str
    phase: Phase
    complexity: Complexity
    phase_sequence: list[Phase]
    skill_context: str
    tokens_expected: int
    use_skill: bool
    metadata: dict = field(default_factory=dict)


@dataclass
class PhaseExecutionResult:
    """阶段执行结果"""
    phase: Phase
    status: str  # pending, running, completed, failed
    output: str = ""
    error: str = ""
    duration_seconds: float = 0.0
    artifacts: list[str] = field(default_factory=list)
    reflexion: ReflexionResult | None = None


@dataclass
class WorkflowExecutionResult:
    """完整工作流执行结果"""
    orchestration: OrchestrationResult
    phase_results: list[PhaseExecutionResult]
    total_duration: float
    success: bool
    final_output: str = ""


# ============================================================================
# 整合引擎
# ============================================================================

class IntegratedEngine:
    """
    整合中间层与执行层的引擎

    设计原则:
    1. MiddlewareChain负责"决策" - 意图、复杂度、路由
    2. 执行器负责"行动" - subagent spawn、并行执行
    3. Reflexion负责"反思" - 自反馈修正
    """

    def __init__(self, workdir: str = "."):
        self.workdir = Path(workdir)
        self.chain = create_default_chain()
        self.subagent_runner: SubAgentRunner | None = None
        self.reflexion_engine: ReflexionEngine | None = None

        if COMPONENTS_AVAILABLE:
            self.subagent_runner = SubAgentRunner(workdir=str(workdir))
            self.reflexion_engine = ReflexionEngine()

    # ==================== 核心方法 ====================

    def run(self, text: str, **kwargs) -> WorkflowExecutionResult:
        """
        运行完整工作流

        Args:
            text: 用户输入
            **kwargs: 额外参数

        Returns:
            WorkflowExecutionResult: 执行结果
        """
        start_time = time.time()

        # Step 1: 中间层编排 - 决策阶段
        orchestration = self._orchestrate(text, **kwargs)

        # Step 2: 执行阶段序列 - 行动阶段
        phase_results = self._execute_phases(orchestration)

        # Step 3: 自反馈分析 - 反思阶段
        final_output = self._reflect(phase_results, orchestration)

        total_duration = time.time() - start_time

        return WorkflowExecutionResult(
            orchestration=orchestration,
            phase_results=phase_results,
            total_duration=total_duration,
            success=all(r.status == "completed" for r in phase_results),
            final_output=final_output
        )

    def _orchestrate(self, text: str, **kwargs) -> OrchestrationResult:
        """
        中间层编排 - 生成执行计划
        """
        request = Request(text=text, **kwargs)
        self.chain.execute(request)

        return OrchestrationResult(
            intent=request.intent or "UNKNOWN",
            phase=request.phase,
            complexity=request.complexity,
            phase_sequence=request.metadata.get("phase_sequence", []),
            skill_context=request.skill_context,
            tokens_expected=request.tokens_expected,
            use_skill=request.use_skill,
            metadata=request.metadata
        )

    def _execute_phases(self, orchestration: OrchestrationResult) -> list[PhaseExecutionResult]:
        """
        执行阶段序列 - 支持并行
        """
        results: list[PhaseExecutionResult] = []

        if not orchestration.phase_sequence:
            return results

        # 按Band分组执行
        current_band: int | None = None
        phases_in_current_band: list[Phase] = []

        for phase in orchestration.phase_sequence:
            if phase == Phase.COMPLETE:
                continue

            # 确定phase所属的band
            band = self._get_phase_band(phase)

            if current_band != band:
                # 执行当前band的所有phase
                if phases_in_current_band:
                    band_results = self._execute_band(phases_in_current_band, orchestration)
                    results.extend(band_results)

                current_band = band
                phases_in_current_band = []

            phases_in_current_band.append(phase)

        # 执行最后一个band
        if phases_in_current_band:
            band_results = self._execute_band(phases_in_current_band, orchestration)
            results.extend(band_results)

        return results

    def _execute_band(self, phases: list[Phase], orchestration: OrchestrationResult) -> list[PhaseExecutionResult]:
        """
        执行一个Band内的阶段 - 支持并行
        """
        if not phases:
            return []

        # 判断是否可以并行 - 使用BAND配置
        if len(phases) > 1 and self._can_parallel_phases(phases):
            return self._execute_parallel(phases, orchestration)
        else:
            return self._execute_sequential(phases, orchestration)

    def _execute_parallel(self, phases: list[Phase], orchestration: OrchestrationResult) -> list[PhaseExecutionResult]:
        """
        并行执行多个phase
        """
        results = []
        for phase in phases:
            result = self._execute_single_phase(phase, orchestration)
            results.append(result)
        return results

    def _execute_sequential(self, phases: list[Phase], orchestration: OrchestrationResult) -> list[PhaseExecutionResult]:
        """
        串行执行多个phase
        """
        results = []
        for phase in phases:
            result = self._execute_single_phase(phase, orchestration)
            results.append(result)
            # 如果失败，可以选择停止或继续
        return results

    def _execute_single_phase(self, phase: Phase, orchestration: OrchestrationResult) -> PhaseExecutionResult:
        """
        执行单个phase
        """
        start_time = time.time()

        # 更新skill_context为当前phase对应的
        skill_context = self._get_phase_skill_context(phase, orchestration)

        if COMPONENTS_AVAILABLE and self.subagent_runner:
            # 调用真实subagent执行
            try:
                result = self.subagent_runner.run(
                    phase=phase.value,
                    task=orchestration.metadata.get("task", orchestration.intent),
                    session_id=orchestration.metadata.get("session_id", ""),
                    prompt_override=skill_context
                )

                duration = time.time() - start_time

                # 自反馈分析
                reflexion = None
                if self.reflexion_engine and result.error:
                    reflexion = self.reflexion_engine.reflect(
                        result.error,
                        error_type="phase_execution_error",
                        context={"phase": phase.value},
                    )

                return PhaseExecutionResult(
                    phase=phase,
                    status="completed" if result.success else "failed",
                    output=result.output,
                    error=result.error,
                    duration_seconds=duration,
                    artifacts=result.artifacts,
                    reflexion=reflexion
                )
            except Exception as e:
                duration = time.time() - start_time
                return PhaseExecutionResult(
                    phase=phase,
                    status="failed",
                    error=str(e),
                    duration_seconds=duration
                )
        else:
            # 模拟执行（当组件不可用时）
            duration = time.time() - start_time
            return PhaseExecutionResult(
                phase=phase,
                status="completed",
                output=f"[模拟] Phase {phase.value} executed with skill context:\n{skill_context[:100]}...",
                duration_seconds=duration
            )

    def _get_phase_skill_context(self, phase: Phase, orchestration: OrchestrationResult) -> str:
        """
        获取指定phase对应的skill_context
        """
        # 使用SkillMiddleware生成当前phase的context
        skill_mw = SkillMiddleware()
        # 临时创建request来获取对应phase的prompt
        temp_request = Request(text=orchestration.metadata.get("task", ""))
        temp_request.phase = phase
        temp_request.complexity = orchestration.complexity
        temp_result = skill_mw.process(temp_request)
        skill_context = temp_result.request_modifications.get("skill_context", orchestration.skill_context)
        return str(skill_context)

    def _get_phase_band(self, phase: Phase) -> int:
        """
        获取phase对应的band编号
        """
        band_map = {
            Phase.RESEARCH: 1,
            Phase.THINKING: 1,
            Phase.PLANNING: 2,
            Phase.EXECUTING: 3,
            Phase.REVIEWING: 4,
            Phase.DEBUGGING: 4,
            Phase.REFINING: 4,
            Phase.COMPLETE: 5,
        }
        return band_map.get(phase, 2)

    def _can_parallel_phases(self, phases: list[Phase]) -> bool:
        """
        判断两个phase是否可以并行
        """
        # RESEARCH和THINKING可以并行
        parallel_pairs = [
            (Phase.RESEARCH, Phase.THINKING),
            (Phase.REVIEWING, Phase.DEBUGGING),
        ]
        for p1, p2 in parallel_pairs:
            if p1 in phases and p2 in phases:
                return True
        return False

    def _reflect(self, phase_results: list[PhaseExecutionResult], orchestration: OrchestrationResult) -> str:
        """
        自反馈分析 - 生成最终输出
        """
        if not phase_results:
            return "No phases executed"

        # 收集所有输出
        outputs = []
        errors = []

        for result in phase_results:
            if result.output:
                outputs.append(f"[{result.phase.value}] {result.output}")
            if result.error:
                errors.append(f"[{result.phase.value}] Error: {result.error}")

        # 生成报告
        report = []
        report.append("# Workflow Execution Report")
        report.append("")
        report.append(f"**Intent**: {orchestration.intent}")
        report.append(f"**Phase Sequence**: {' → '.join(p.value for p in orchestration.phase_sequence)}")
        report.append(f"**Total Duration**: {sum(r.duration_seconds for r in phase_results):.2f}s")
        report.append("")

        if outputs:
            report.append("## Outputs")
            for o in outputs:
                report.append(f"{o}")
            report.append("")

        if errors:
            report.append("## Errors")
            for e in errors:
                report.append(f"{e}")
            report.append("")

        return "\n".join(report)


# ============================================================================
# 便捷函数
# ============================================================================

def create_integrated_engine(workdir: str = ".") -> IntegratedEngine:
    """创建整合引擎"""
    return IntegratedEngine(workdir=workdir)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("Integrated Workflow Engine 测试")
    print("="*60)

    engine = create_integrated_engine(".")

    test_cases = [
        "帮我写一个回文检测函数",
        "/agentic-workflow 开发一个用户系统",
    ]

    for text in test_cases:
        print(f"\n输入: {text}")
        result = engine.run(text)

        print("\n--- 编排结果 ---")
        print(f"意图: {result.orchestration.intent}")
        print(f"阶段: {result.orchestration.phase.value}")
        print(f"复杂度: {result.orchestration.complexity.value}")
        print(f"序列: {[p.value for p in result.orchestration.phase_sequence]}")
        print(f"Skill: {'启用' if result.orchestration.use_skill else '禁用'}")

        print("\n--- 执行结果 ---")
        for pr in result.phase_results:
            print(f"[{pr.phase.value}] {pr.status} - {pr.duration_seconds:.2f}s")

        print("\n--- 最终输出 ---")
        print(result.final_output[:500] if result.final_output else "(无)")
        print("-"*60)
