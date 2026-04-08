#!/usr/bin/env python3
"""
Workflow Engine v2 - 基于Middleware的灵活工作流引擎

借鉴deer-flow的Middleware Chain设计,实现:
1. 意图分析 -> 2. 复杂度评估 -> 3. Skill加载 -> 4. 执行

相对于v1的优势:
- 中间件可组合、可禁用
- 渐进式Skill加载,减少token消耗
- 基于实验数据优化: THINKING/RESEARCH默认禁用skill

Usage:
    python3 workflow_engine_v2.py "用户输入"
    python3 workflow_engine_v2.py --status
"""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# 导入中间件系统
from middleware import (
    Complexity,
    Phase,
    Request,
    Response,
    create_default_chain,
)

# ============================================================================
# 配置
# ============================================================================

DEFAULT_STATE_FILE = ".workflow_state.json"


# ============================================================================
# 工作流状态
# ============================================================================

@dataclass
class WorkflowState:
    """工作流状态"""
    session_id: str = ""
    current_phase: Phase = Phase.IDLE
    phase_sequence: list[Phase] = field(default_factory=list)
    current_step: int = 0
    request: Request | None = None
    response: Response | None = None
    started_at: str | None = None
    updated_at: str | None = None


# ============================================================================
# 工作流引擎
# ============================================================================

class WorkflowEngine:
    """
    基于Middleware的工作流引擎

    设计原则:
    1. Middleware决定意图和技能加载
    2. 阶段序列由复杂度决定
    3. 执行器负责具体任务执行
    """

    def __init__(self, workdir: str = "."):
        self.workdir = Path(workdir)
        self.state_file = self.workdir / DEFAULT_STATE_FILE
        self.chain = create_default_chain()
        self.state: WorkflowState | None = None

    # ==================== 核心方法 ====================

    def process(self, text: str, **kwargs) -> Response:
        """
        处理用户输入,执行完整工作流

        Args:
            text: 用户输入
            **kwargs: 额外参数 (session_id, user_id等)

        Returns:
            Response: 处理结果
        """
        # 1. 构建请求
        request = Request(
            text=text,
            session_id=kwargs.get("session_id", ""),
            user_id=kwargs.get("user_id", ""),
            metadata=kwargs
        )

        # 2. 中间件链处理
        response = self.chain.execute(request)

        # 3. 更新状态
        self._update_state(request, response)

        return response

    def advance(self) -> Response:
        """
        推进到下一个阶段

        Returns:
            Response: 处理结果
        """
        if not self.state or not self.state.request:
            raise ValueError("No active workflow state")

        state = self.state
        state.current_step += 1

        if state.current_step >= len(state.phase_sequence):
            # 工作流完成
            state.current_phase = Phase.COMPLETE
            return self._create_complete_response(state)

        # 执行下一个阶段
        next_phase = state.phase_sequence[state.current_step]
        state.current_phase = next_phase

        return self._execute_phase(state, next_phase)

    def status(self) -> dict:
        """
        获取当前状态

        Returns:
            dict: 状态信息
        """
        if not self.state:
            return {"status": "idle", "message": "No active workflow"}

        return {
            "status": "active",
            "current_phase": self.state.current_phase.value,
            "phase_sequence": [p.value for p in self.state.phase_sequence],
            "current_step": self.state.current_step,
            "total_steps": len(self.state.phase_sequence),
            "started_at": self.state.started_at,
            "request": {
                "text": self.state.request.text if self.state.request else "",
                "intent": self.state.request.intent if self.state.request else "",
                "complexity": self.state.request.complexity.value if self.state.request else "",
                "use_skill": self.state.request.use_skill if self.state.request else True,
            } if self.state.request else None
        }

    def save_state(self) -> None:
        """保存状态到文件"""
        if not self.state:
            return

        state_dict = {
            "session_id": self.state.session_id,
            "current_phase": self.state.current_phase.value,
            "phase_sequence": [p.value for p in self.state.phase_sequence],
            "current_step": self.state.current_step,
            "started_at": self.state.started_at,
            "updated_at": datetime.now().isoformat(),
            "request": {
                "text": self.state.request.text if self.state.request else "",
                "intent": self.state.request.intent if self.state.request else "",
                "complexity": self.state.request.complexity.value if self.state.request else "M",
                "use_skill": self.state.request.use_skill if self.state.request else True,
                "skill_context": self.state.request.skill_context if self.state.request else "",
            } if self.state.request else None
        }

        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, indent=2, ensure_ascii=False)

    def load_state(self) -> bool:
        """
        从文件加载状态

        Returns:
            bool: 是否成功加载
        """
        if not self.state_file.exists():
            return False

        try:
            with open(self.state_file, encoding="utf-8") as f:
                state_dict = json.load(f)

            self.state = WorkflowState(
                session_id=state_dict.get("session_id", ""),
                current_phase=Phase(state_dict.get("current_phase", "IDLE")),
                phase_sequence=[Phase(p) for p in state_dict.get("phase_sequence", [])],
                current_step=state_dict.get("current_step", 0),
                started_at=state_dict.get("started_at")
            )

            if state_dict.get("request"):
                req_data = state_dict["request"]
                self.state.request = Request(
                    text=req_data.get("text", ""),
                    intent=req_data.get("intent"),
                    complexity=Complexity(req_data.get("complexity", "M")),
                    use_skill=req_data.get("use_skill", True),
                    skill_context=req_data.get("skill_context", ""),
                )

            return True

        except Exception as e:
            print(f"Failed to load state: {e}")
            return False

    # ==================== 私有方法 ====================

    def _update_state(self, request: Request, response: Response) -> None:
        """更新工作流状态"""
        self.state = WorkflowState(
            session_id=request.session_id or datetime.now().strftime("%Y%m%d%H%M%S"),
            current_phase=request.phase,
            phase_sequence=request.metadata.get("phase_sequence", []),
            current_step=0,
            request=request,
            response=response,
            started_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

    def _execute_phase(self, state: WorkflowState, phase: Phase) -> Response:
        """执行单个阶段"""
        response = Response(
            request=state.request,
            phases_used=[phase]
        )

        # 根据阶段类型生成输出
        if phase == Phase.COMPLETE:
            return self._create_complete_response(state)

        # 这里可以调用实际的执行器
        response.output = f"[{phase.value}] Phase execution placeholder"
        return response

    def _create_complete_response(self, state: WorkflowState) -> Response:
        """创建完成响应"""
        return Response(
            request=state.request,
            output="Workflow complete",
            success=True,
            phases_used=state.phase_sequence
        )


# ============================================================================
# CLI 入口
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Workflow Engine v2 - Middleware-based workflow")
    parser.add_argument("text", nargs="?", help="用户输入")
    parser.add_argument("--status", action="store_true", help="查看当前状态")
    parser.add_argument("--advance", action="store_true", help="推进到下一阶段")
    parser.add_argument("--workdir", default=".", help="工作目录")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    args = parser.parse_args()

    engine = WorkflowEngine(workdir=args.workdir)

    # 加载已有状态
    engine.load_state()

    if args.status:
        # 查看状态
        status = engine.status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return 0

    if args.advance:
        # 推进阶段
        try:
            response = engine.advance()
            engine.save_state()
            print(f"Advanced to: {engine.state.current_phase.value}")
            print(f"Response: {response.output}")
        except Exception as e:
            print(f"Error: {e}")
        return 0

    if args.text:
        # 处理输入
        response = engine.process(args.text)
        engine.save_state()

        print("\n" + "=" * 60)
        print("Middleware Chain Result")
        print("=" * 60)

        if args.verbose:
            print(f"\n意图: {response.request.intent}")
            print(f"阶段: {response.request.phase.value}")
            print(f"复杂度: {response.request.complexity.value}")
            print(f"使用Skill: {response.request.use_skill}")
            print(f"Token预估: {response.request.tokens_expected}")
            print(f"阶段序列: {[p.value for p in response.request.metadata.get('phase_sequence', [])]}")

        print(f"\n阶段序列: {' -> '.join([p.value for p in response.request.metadata.get('phase_sequence', [])])}")
        print(f"耗时: {response.duration_ms}ms")

        return 0

    # 交互模式
    print("Workflow Engine v2 - Middleware-based workflow")
    print("输入消息进行工作流处理 (Ctrl+C 退出)")
    print("-" * 60)

    while True:
        try:
            text = input("\n> ")
            if not text.strip():
                continue

            response = engine.process(text)
            engine.save_state()

            print(f"  意图: {response.request.intent}")
            print(f"  阶段: {response.request.phase.value}")
            print(f"  复杂度: {response.request.complexity.value}")
            print(f"  使用Skill: {response.request.use_skill}")
            print(f"  序列: {' -> '.join([p.value for p in response.request.metadata.get('phase_sequence', [])])}")

        except KeyboardInterrupt:
            print("\n退出")
            break

    return 0


if __name__ == "__main__":
    sys.exit(main())
