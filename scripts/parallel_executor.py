#!/usr/bin/env python3
"""
Parallel Executor - 并行执行Band管理器

实现 phase 并行化策略:

Band 0: [ROUTER]                           - 串行入口
Band 1: [RESEARCH || THINKING]             - 并行
Band 2: [PLANNING]                         - 依赖 Band 1
Band 3: [EXECUTING]                        - 依赖 Band 2
Band 4: [REVIEWING || DEBUGGING]           - 部分并行
Band 5: [COMPLETE]                         - 串行收尾

用法:
    from parallel_executor import ParallelExecutor, BAND_CONFIG, PhaseBand

    executor = ParallelExecutor(workdir)
    result = executor.execute_band(1, ["RESEARCH", "THINKING"])
"""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

# ============================================================================
# Band Configuration (from parallel-execution.md)
# ============================================================================

class PhaseBand(Enum):
    """并行执行 Band 定义"""
    BAND_0_ROUTER = 0      # 串行入口
    BAND_1_EXPLORE = 1     # RESEARCH || THINKING 并行
    BAND_2_PLAN = 2        # PLANNING
    BAND_3_EXEC = 3        # EXECUTING
    BAND_4_REVIEW = 4      # REVIEWING || DEBUGGING
    BAND_5_COMPLETE = 5    # 串行收尾


# Band 配置
BAND_CONFIG = {
    PhaseBand.BAND_0_ROUTER: {
        "name": "ROUTER",
        "phases": ["ROUTER"],
        "parallel": False,
        "dependencies": [],
        "description": "串行入口点"
    },
    PhaseBand.BAND_1_EXPLORE: {
        "name": "EXPLORE",
        "phases": ["RESEARCH", "THINKING", "EXPLORING"],
        "parallel": True,
        "dependencies": [PhaseBand.BAND_0_ROUTER],
        "description": "研究与思考并行"
    },
    PhaseBand.BAND_2_PLAN: {
        "name": "PLAN",
        "phases": ["PLANNING", "OFFICE-HOURS"],
        "parallel": False,  # PLANNING 需要所有输入就绪
        "dependencies": [PhaseBand.BAND_1_EXPLORE],
        "description": "规划阶段"
    },
    PhaseBand.BAND_3_EXEC: {
        "name": "EXEC",
        "phases": ["EXECUTING"],
        "parallel": False,
        "dependencies": [PhaseBand.BAND_2_PLAN],
        "description": "执行阶段"
    },
    PhaseBand.BAND_4_REVIEW: {
        "name": "REVIEW",
        "phases": ["REVIEWING", "DEBUGGING", "REFINING"],
        "parallel": True,  # REVIEWING 和 DEBUGGING 可并行
        "dependencies": [PhaseBand.BAND_3_EXEC],
        "description": "审查与调试并行"
    },
    PhaseBand.BAND_5_COMPLETE: {
        "name": "COMPLETE",
        "phases": ["COMPLETE"],
        "parallel": False,
        "dependencies": [PhaseBand.BAND_4_REVIEW],
        "description": "完成阶段"
    },
}


@dataclass
class PhaseResult:
    """Phase 执行结果"""
    phase: str
    status: str  # pending, running, completed, failed, skipped
    result: Optional[Any] = None
    error: Optional[str] = None
    duration: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class BandResult:
    """Band 执行结果"""
    band: PhaseBand
    status: str  # pending, running, completed, failed, skipped
    phase_results: Dict[str, PhaseResult] = field(default_factory=dict)
    duration: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ============================================================================
# Phase Dependency Graph
# ============================================================================

PHASE_TO_BAND: Dict[str, PhaseBand] = {}
for band, config in BAND_CONFIG.items():
    for phase in config["phases"]:
        PHASE_TO_BAND[phase] = band

BAND_PHASES: Dict[PhaseBand, List[str]] = {}
for band, config in BAND_CONFIG.items():
    BAND_PHASES[band] = config["phases"]


def get_phase_band(phase: str) -> PhaseBand:
    """获取 phase 所在的 band"""
    return PHASE_TO_BAND.get(phase, PhaseBand.BAND_2_PLAN)


def get_band_phases(band: PhaseBand) -> List[str]:
    """获取 band 包含的所有 phases"""
    return BAND_PHASES.get(band, [])


def can_parallel(phase1: str, phase2: str) -> bool:
    """判断两个 phase 是否可以并行"""
    band1 = get_phase_band(phase1)
    band2 = get_phase_band(phase2)
    if band1 != band2:
        return False
    return BAND_CONFIG[band1]["parallel"]


def get_band_dependencies(band: PhaseBand) -> List[PhaseBand]:
    """获取 band 的依赖"""
    return BAND_CONFIG.get(band, {}).get("dependencies", [])


def are_dependencies_met(band: PhaseBand, completed_bands: Set[PhaseBand]) -> bool:
    """检查 band 的依赖是否都已完成"""
    deps = get_band_dependencies(band)
    return all(dep in completed_bands for dep in deps)


# ============================================================================
# Parallel Executor
# ============================================================================

class ParallelExecutor:
    """
    并行执行管理器

    功能:
    - Band 级别并行调度
    - Phase 级别并行执行
    - 依赖检查与等待
    - 超时控制
    - 进度追踪
    """

    def __init__(
        self,
        workdir: str = ".",
        max_workers: int = 3,
        default_timeout: int = 300,
    ):
        self.workdir = Path(workdir)
        self.max_workers = max_workers
        self.default_timeout = default_timeout
        self._lock = threading.RLock()
        self._band_results: Dict[PhaseBand, BandResult] = {}
        self._phase_callbacks: Dict[str, Callable] = {}
        self._completed_bands: Set[PhaseBand] = set()

    def set_phase_callback(self, phase: str, callback: Callable[[], Any]):
        """设置 phase 执行回调"""
        self._phase_callbacks[phase] = callback

    def execute_band(
        self,
        band: PhaseBand,
        phases: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> BandResult:
        """
        执行一个 band

        Args:
            band: 要执行的 band
            phases: 可选，指定要执行的 phases（默认使用 band 配置）
            context: 执行上下文

        Returns:
            BandResult
        """
        config = BAND_CONFIG.get(band, {})
        if not config:
            return BandResult(band=band, status="failed")

        phases_to_run = phases or config["phases"]

        # 检查是否并行
        is_parallel = config["parallel"] and len(phases_to_run) > 1

        result = BandResult(
            band=band,
            status="running",
            started_at=datetime.now().isoformat(),
        )

        with self._lock:
            self._band_results[band] = result

        start_time = time.time()

        if is_parallel:
            # 并行执行
            self._execute_parallel(band, phases_to_run, context, result)
        else:
            # 串行执行
            self._execute_sequential(band, phases_to_run, context, result)

        result.duration = time.time() - start_time
        result.completed_at = datetime.now().isoformat()
        result.status = "completed"

        with self._lock:
            self._completed_bands.add(band)

        return result

    def _execute_parallel(
        self,
        band: PhaseBand,
        phases: List[str],
        context: Optional[Dict[str, Any]],
        result: BandResult,
    ):
        """并行执行多个 phases"""
        with ThreadPoolExecutor(max_workers=min(len(phases), self.max_workers)) as executor:
            future_to_phase = {
                executor.submit(self._execute_phase, phase, context): phase
                for phase in phases
            }

            for future in as_completed(future_to_phase):
                phase = future_to_phase[future]
                try:
                    phase_result = future.result()
                    result.phase_results[phase] = phase_result
                except Exception as e:
                    result.phase_results[phase] = PhaseResult(
                        phase=phase,
                        status="failed",
                        error=str(e),
                    )

    def _execute_sequential(
        self,
        band: PhaseBand,
        phases: List[str],
        context: Optional[Dict[str, Any]],
        result: BandResult,
    ):
        """串行执行多个 phases"""
        for phase in phases:
            phase_result = self._execute_phase(phase, context)
            result.phase_results[phase] = phase_result

            # 如果失败，停止执行
            if phase_result.status == "failed":
                break

    def _execute_phase(self, phase: str, context: Optional[Dict[str, Any]]) -> PhaseResult:
        """执行单个 phase"""
        result = PhaseResult(
            phase=phase,
            status="running",
            started_at=datetime.now().isoformat(),
        )

        start_time = time.time()

        try:
            callback = self._phase_callbacks.get(phase)
            if callback:
                result.result = callback()
            else:
                # 默认实现：模拟执行
                time.sleep(0.1)
                result.result = {"phase": phase, "status": "completed"}

            result.status = "completed"

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.duration = time.time() - start_time
        result.completed_at = datetime.now().isoformat()

        return result

    def execute_workflow(
        self,
        phases: List[str],
        context: Optional[Dict[str, Any]] = None,
        stop_on_failure: bool = True,
    ) -> Dict[str, BandResult]:
        """
        执行完整工作流（自动处理 band 依赖）

        Args:
            phases: 要执行的 phases 列表
            context: 执行上下文
            stop_on_failure: 失败时是否停止

        Returns:
            {band: BandResult}
        """
        results = {}
        completed_bands: Set[PhaseBand] = set()

        # 按 band 分组
        band_phases: Dict[PhaseBand, List[str]] = {}
        for phase in phases:
            band = get_phase_band(phase)
            if band not in band_phases:
                band_phases[band] = []
            band_phases[band].append(phase)

        # 按 band 顺序执行
        for band in sorted(band_phases.keys(), key=lambda b: b.value):
            # 检查依赖
            if not are_dependencies_met(band, completed_bands):
                deps = get_band_dependencies(band)
                missing = [d for d in deps if d not in completed_bands]
                # 依赖未满足，跳过或失败
                results[band] = BandResult(
                    band=band,
                    status="skipped",
                    phase_results={
                        p: PhaseResult(phase=p, status="skipped", error=f"Dependencies not met: {missing}")
                        for p in band_phases[band]
                    },
                )
                if stop_on_failure:
                    break
                continue

            # 执行 band
            band_result = self.execute_band(band, band_phases[band], context)
            results[band] = band_result

            if band_result.status == "failed" and stop_on_failure:
                break

            completed_bands.add(band)

        return results

    def get_ready_bands(self, completed_bands: Set[PhaseBand]) -> List[PhaseBand]:
        """获取当前可以执行的 bands"""
        ready = []
        for band in PhaseBand:
            if band in completed_bands:
                continue
            if are_dependencies_met(band, completed_bands):
                ready.append(band)
        return ready

    def get_status(self) -> Dict[str, Any]:
        """获取执行状态"""
        return {
            "band_results": {
                band.value: {
                    "status": result.status,
                    "phase_results": {
                        p: {
                            "status": pr.status,
                            "duration": pr.duration,
                            "error": pr.error,
                        }
                        for p, pr in result.phase_results.items()
                    }
                }
                for band, result in self._band_results.items()
            },
            "completed_bands": [b.value for b in self._completed_bands],
        }


# ============================================================================
# Band-Aware Workflow Integration
# ============================================================================

class BandAwareWorkflow:
    """
    支持并行 Band 的工作流管理器

    集成到 workflow_engine 的状态机中
    """

    def __init__(self, workdir: str = "."):
        self.workdir = Path(workdir)
        self.executor = ParallelExecutor(workdir)
        self._completed_bands: Set[PhaseBand] = set()
        self._phase_states: Dict[str, str] = {}  # phase -> status

    def register_phase_handler(self, phase: str, handler: Callable):
        """注册 phase 处理函数"""
        self.executor.set_phase_callback(phase, handler)

    def execute_phase(self, phase: str) -> PhaseResult:
        """执行单个 phase"""
        callback = self.executor._phase_callbacks.get(phase)

        result = PhaseResult(
            phase=phase,
            status="running",
            started_at=datetime.now().isoformat(),
        )

        start_time = time.time()

        try:
            if callback:
                result.result = callback()
            else:
                time.sleep(0.1)
                result.result = {"phase": phase, "status": "completed"}

            result.status = "completed"

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.duration = time.time() - start_time
        result.completed_at = datetime.now().isoformat()
        self._phase_states[phase] = result.status

        return result

    def execute_band_phases(self, band: PhaseBand) -> BandResult:
        """执行 band 的所有 phases"""
        phases = get_band_phases(band)
        return self.executor.execute_band(band, phases)

    def can_execute_phase(self, phase: str) -> bool:
        """检查是否可以执行 phase"""
        band = get_phase_band(phase)
        return are_dependencies_met(band, self._completed_bands)

    def get_next_executable_phases(self) -> List[str]:
        """获取下一个可执行的 phases"""
        ready_bands = self.executor.get_ready_bands(self._completed_bands)
        phases = []
        for band in ready_bands:
            band_phases = get_band_phases(band)
            # 只返回尚未执行的 phases
            for p in band_phases:
                if p not in self._phase_states:
                    phases.append(p)
        return phases

    def mark_band_complete(self, band: PhaseBand):
        """标记 band 完成"""
        self._completed_bands.add(band)

    def get_workflow_status(self) -> Dict[str, Any]:
        """获取工作流状态"""
        return {
            "completed_bands": [b.value for b in self._completed_bands],
            "phase_states": self._phase_states,
            "next_phases": self.get_next_executable_phases(),
            "executor_status": self.executor.get_status(),
        }


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Parallel Executor - Band-based Parallel Execution")
    parser.add_argument("--workdir", default=".", help="workspace directory")
    parser.add_argument("--op", choices=["list-bands", "band-status", "execute-band", "execute-workflow"], required=True)
    parser.add_argument("--band", type=int, help="band number (0-5)")
    parser.add_argument("--phases", nargs="+", help="phases to execute")
    parser.add_argument("--parallel", action="store_true", help="enable parallel execution")
    args = parser.parse_args()

    executor = ParallelExecutor(args.workdir)

    if args.op == "list-bands":
        print("Parallel Execution Bands:")
        print("-" * 60)
        for band in PhaseBand:
            config = BAND_CONFIG[band]
            print(f"Band {band.value}: {config['name']}")
            print(f"  Phases: {config['phases']}")
            print(f"  Parallel: {config['parallel']}")
            print(f"  Dependencies: {[d.value for d in config['dependencies']]}")
            print(f"  Description: {config['description']}")
            print()
        return 0

    if args.op == "band-status":
        print(json.dumps(executor.get_status(), ensure_ascii=False, indent=2))
        return 0

    if args.op == "execute-band":
        if args.band is None:
            print("错误: --band required")
            return 1

        band = PhaseBand(args.band)
        phases = args.phases or get_band_phases(band)

        print(f"Executing Band {band.value} ({BAND_CONFIG[band]['name']})...")
        print(f"Phases: {phases}")

        result = executor.execute_band(band, phases)

        print(f"\nResult: {result.status}")
        print(f"Duration: {result.duration:.2f}s")
        for phase, phase_result in result.phase_results.items():
            print(f"  {phase}: {phase_result.status} ({phase_result.duration:.2f}s)")
            if phase_result.error:
                print(f"    Error: {phase_result.error}")

        return 0

    if args.op == "execute-workflow":
        if not args.phases:
            # 默认执行完整工作流
            phases = ["ROUTER", "RESEARCH", "THINKING", "PLANNING", "EXECUTING", "REVIEWING", "COMPLETE"]
        else:
            phases = args.phases

        print(f"Executing workflow: {phases}")

        results = executor.execute_workflow(phases)

        print("\nWorkflow Results:")
        for band, result in results.items():
            print(f"Band {band.value}: {result.status}")
            for phase, phase_result in result.phase_results.items():
                print(f"  {phase}: {phase_result.status}")

        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
