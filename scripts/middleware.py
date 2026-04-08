#!/usr/bin/env python3
"""
Middleware Chain System - 借鉴 deer-flow 的中间层设计

Status:
    Experimental prototype used for orchestration experiments.
    It is not the authoritative workflow state machine.

核心设计:
1. MiddlewareProtocol - 中间件协议接口
2. MiddlewareChain - 中间件链式调用
3. Request/Response - 请求响应对象
4. 各阶段中间件实现

中间件顺序 (参考deer-flow):
1. IntentMiddleware      - 意图分析
2. ContextMiddleware    - 上下文注入
3. SkillMiddleware      - 渐进式skill加载
4. ComplexityMiddleware  - 复杂度评估
5. SandboxMiddleware    - 执行隔离(预留)

Usage:
    chain = MiddlewareChain([
        IntentMiddleware(),
        ContextMiddleware(),
        SkillMiddleware(),
    ])
    response = chain.execute(request)
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from runtime_profile import build_skill_context, token_budget_for_complexity

# ============================================================================
# 数据模型
# ============================================================================

class Phase(Enum):
    """工作阶段"""
    IDLE = "IDLE"
    DEBUGGING = "DEBUGGING"
    RESEARCH = "RESEARCH"
    THINKING = "THINKING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    REVIEWING = "REVIEWING"
    REFINING = "REFINING"
    COMPLETE = "COMPLETE"


class Complexity(Enum):
    """任务复杂度"""
    XS = "XS"  # typo, import
    S = "S"    # fix known bug
    M = "M"    # new API
    L = "L"    # refactor module
    XL = "XL"  # design new system


@dataclass
class Request:
    """请求对象"""
    text: str
    user_id: str | None = None
    session_id: str | None = None
    metadata: dict = field(default_factory=dict)

    # 解析后填充的字段
    intent: str | None = None
    phase: Phase = Phase.IDLE
    complexity: Complexity = Complexity.M
    skill_context: str = ""
    tokens_expected: int = 0
    use_skill: bool = True


@dataclass
class Response:
    """响应对象"""
    request: Request
    output: str = ""
    success: bool = True
    error: str | None = None
    duration_ms: int = 0
    tokens_used: int = 0
    phases_used: list[Phase] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class MiddlewareResult:
    """中间件处理结果"""
    continue_chain: bool = True  # 是否继续执行后续中间件
    request_modifications: dict = field(default_factory=dict)  # 对request的修改
    response_modifications: dict = field(default_factory=dict)  # 对response的修改
    skip_reason: str | None = None


# ============================================================================
# 中间件协议
# ============================================================================

class MiddlewareProtocol(ABC):
    """中间件协议 - 所有中间件必须实现此接口"""

    @property
    @abstractmethod
    def name(self) -> str:
        """中间件名称"""
        pass

    @abstractmethod
    def process(self, request: Request, response: Response | None = None) -> MiddlewareResult:
        """
        处理请求

        Args:
            request: 请求对象
            response: 响应对象(如果已生成)

        Returns:
            MiddlewareResult: 处理结果
        """
        pass

    def on_error(self, error: Exception, request: Request) -> None:
        """错误处理回调"""
        _ = (error, request)


# ============================================================================
# 中间件实现
# ============================================================================

class IntentMiddleware(MiddlewareProtocol):
    """
    意图分析中间件

    分析用户输入的真实意图，决定:
    1. 是否触发工作流
    2. 应该使用哪个阶段
    3. 是否需要skill

    借鉴oh-my-openagent的IntentGate设计
    """

    # 意图关键词配置
    INTENT_KEYWORDS = {
        "DEBUGGING": [
            "bug", "错误", "调试", "修复", "崩溃", "异常", "失败",
            "跑不通", "不能用", "失效", "超时", "卡死", "无响应"
        ],
        "REVIEWING": [
            "审查", "review", "审计", "检查", "代码审查", "代码质量"
        ],
        "REFINING": [
            "优化", "迭代", "精炼", "改进", "完善", "调优"
        ],
        "RESEARCH": [
            "搜索", "调研", "最佳实践", "有什么", "如何实现", "参考"
        ],
        "THINKING": [
            "谁最懂", "专家", "分析", "理解", "思路", "建议", "怎么看"
        ],
        "PLANNING": [
            "计划", "规划", "拆分", "设计", "安排", "步骤"
        ],
        "EXECUTING": [
            "写", "实现", "开发", "创建", "编写", "implement", "build"
        ],
    }

    # 负面意图 (不触发工作流)
    NEGATIVE_INTENTS = [
        "天气", "笑话", "你好", "谢谢", "嗨", "hi", "hello", "bye"
    ]

    # 强制触发
    FORCE_TRIGGERS = [
        "/agentic-workflow", "继续", "下一步", "继续执行"
    ]

    @property
    def name(self) -> str:
        return "IntentMiddleware"

    def process(self, request: Request, response: Response | None = None) -> MiddlewareResult:
        text_lower = request.text.lower()

        # 1. 负面意图检测 - 直接回答
        if any(neg in text_lower for neg in self.NEGATIVE_INTENTS):
            request.intent = "CHAT"
            request.use_skill = False
            return MiddlewareResult(
                continue_chain=False,
                request_modifications={"intent": "CHAT", "use_skill": False},
                skip_reason="负面意图检测到"
            )

        # 2. 强制触发
        if any(force in request.text for force in self.FORCE_TRIGGERS):
            request.intent = "FULL_WORKFLOW"
            request.phase = Phase.RESEARCH  # 从 RESEARCH 开始完整流程
            request.complexity = Complexity.XL
            request.metadata["phase_sequence"] = [
                Phase.RESEARCH,
                Phase.THINKING,
                Phase.PLANNING,
                Phase.EXECUTING,
                Phase.REVIEWING,
                Phase.REFINING,
                Phase.COMPLETE,
            ]
            return MiddlewareResult(
                continue_chain=True,
                request_modifications={
                    "intent": "FULL_WORKFLOW",
                    "phase": Phase.RESEARCH,
                    "complexity": Complexity.XL,
                    "phase_sequence": request.metadata["phase_sequence"],
                },
            )

        # 3. 意图检测
        for intent_name, keywords in self.INTENT_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                phase_map = {
                    "DEBUGGING": Phase.DEBUGGING,
                    "REVIEWING": Phase.REVIEWING,
                    "REFINING": Phase.REFINING,
                    "RESEARCH": Phase.RESEARCH,
                    "THINKING": Phase.THINKING,
                    "PLANNING": Phase.PLANNING,
                    "EXECUTING": Phase.EXECUTING,
                }
                request.intent = intent_name
                request.phase = phase_map.get(intent_name, Phase.EXECUTING)

                # THINKING/RESEARCH 默认不需要skill (基于实验数据)
                if intent_name in ["THINKING", "RESEARCH"]:
                    request.use_skill = False

                return MiddlewareResult(
                    continue_chain=True,
                    request_modifications={
                        "intent": intent_name,
                        "phase": request.phase,
                        "use_skill": request.use_skill
                    }
                )

        # 默认意图
        request.intent = "EXECUTE"
        request.phase = Phase.EXECUTING
        return MiddlewareResult(
            continue_chain=True,
            request_modifications={"intent": "EXECUTE", "phase": Phase.EXECUTING}
        )


class ComplexityMiddleware(MiddlewareProtocol):
    """
    复杂度评估中间件

    评估任务复杂度，决定:
    1. 需要经历哪些阶段
    2. Token预算
    3. 是否启用skill
    """

    COMPLEXITY_KEYWORDS = {
        Complexity.XS: ["typo", "拼写", "import", "重命名", "删除", "一个函数", "写一个", "简单函数"],
        Complexity.S: ["修复", "修改", "bug", "错误", "调整", "这个", "下这个"],
        Complexity.M: ["新增", "功能", "接口", "组件", "实现", "开发"],
        Complexity.L: ["重构", "重写", "模块", "迁移", "大改", "整个"],
        Complexity.XL: ["系统设计", "架构", "从零开始", "微服务", "全新项目", "设计一个"],
    }

    @property
    def name(self) -> str:
        return "ComplexityMiddleware"

    def process(self, request: Request, response: Response | None = None) -> MiddlewareResult:
        text_lower = request.text.lower()

        if request.intent == "FULL_WORKFLOW":
            phase_sequence = self._get_phase_sequence(Complexity.XL)
            request.complexity = Complexity.XL
            request.metadata["phase_sequence"] = phase_sequence
            return MiddlewareResult(
                continue_chain=True,
                request_modifications={
                    "complexity": Complexity.XL,
                    "phase_sequence": phase_sequence,
                },
            )

        scores = {}

        for complexity, keywords in self.COMPLEXITY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[complexity] = score

        if scores:
            request.complexity = max(scores, key=lambda complexity: scores[complexity])
        else:
            request.complexity = Complexity.M  # 默认中等复杂度

        # 更新phase_sequence
        phase_sequence = self._get_phase_sequence(request.complexity)
        request.metadata["phase_sequence"] = phase_sequence

        # 简单任务决策:
        # - XS/S + EXECUTING: 仍可使用skill (TDD有效, 66.7%胜率)
        # - XS/S + DEBUGGING: 禁用skill (简单bug直接修复)
        # - THINKING/RESEARCH: 在IntentMiddleware已禁用
        if request.complexity in [Complexity.XS, Complexity.S] and request.phase == Phase.DEBUGGING:
            request.use_skill = False

        return MiddlewareResult(
            continue_chain=True,
            request_modifications={
                "complexity": request.complexity,
                "phase_sequence": phase_sequence
            }
        )

    def _get_phase_sequence(self, complexity: Complexity) -> list[Phase]:
        """根据复杂度获取阶段序列"""
        sequences = {
            Complexity.XS: [Phase.EXECUTING, Phase.COMPLETE],
            Complexity.S: [Phase.DEBUGGING, Phase.EXECUTING, Phase.COMPLETE],
            Complexity.M: [Phase.PLANNING, Phase.EXECUTING, Phase.REVIEWING, Phase.COMPLETE],
            Complexity.L: [Phase.RESEARCH, Phase.THINKING, Phase.PLANNING, Phase.EXECUTING, Phase.REVIEWING, Phase.COMPLETE],
            Complexity.XL: [Phase.RESEARCH, Phase.THINKING, Phase.PLANNING, Phase.EXECUTING, Phase.REVIEWING, Phase.REFINING, Phase.COMPLETE],
        }
        return sequences.get(complexity, sequences[Complexity.M])


class SkillMiddleware(MiddlewareProtocol):
    """
    渐进式Skill加载中间件

    基于实验数据优化:
    - EXECUTING/DEBUGGING: 启用skill (有效)
    - REVIEWING: 可选启用
    - THINKING/RESEARCH: 禁用skill (无效)
    - 简单任务: 禁用skill

    借鉴deer-flow的渐进式skill加载
    """

    @property
    def name(self) -> str:
        return "SkillMiddleware"

    def process(self, request: Request, response: Response | None = None) -> MiddlewareResult:
        # 如果不应该使用skill,返回空context
        if not request.use_skill:
            request.skill_context = ""
            request.tokens_expected = 500  # 简单任务预估500 tokens
            return MiddlewareResult(
                continue_chain=True,
                request_modifications={
                    "skill_context": "",
                    "tokens_expected": 500
                }
            )

        # 获取当前阶段的精简prompt,并添加核心原则
        prompt, tokens = build_skill_context(request.phase.value, request.complexity.value)

        # 根据复杂度调整
        if request.complexity == Complexity.XL:
            # 复杂任务可以稍微详细一点
            prompt = prompt + "\n\n这是一个复杂任务,请深入分析。"
        elif request.complexity == Complexity.L:
            pass

        request.tokens_expected = max(token_budget_for_complexity(request.complexity.value), tokens)

        request.skill_context = prompt

        return MiddlewareResult(
            continue_chain=True,
            request_modifications={
                "skill_context": prompt,
                "tokens_expected": request.tokens_expected
            }
        )


class ContextMiddleware(MiddlewareProtocol):
    """
    Context Injection Middleware

    Injects workspace and project context
    """

    @property
    def name(self) -> str:
        return "ContextMiddleware"

    def process(self, request: Request, response: Response | None = None) -> MiddlewareResult:
        # 可以在此注入项目特定的上下文
        # 例如: 项目结构、已有技能、约束等

        if "workspace" not in request.metadata:
            request.metadata["workspace"] = {
                "cwd": request.metadata.get("cwd", ""),
            }

        return MiddlewareResult(
            continue_chain=True,
            request_modifications=request.metadata
        )


# ============================================================================
# 中间件链
# ============================================================================

class MiddlewareChain:
    """
    中间件链

    按顺序执行所有中间件,支持:
    1. 中断链执行
    2. 请求/响应修改
    3. 错误处理
    """

    def __init__(self, middlewares: list[MiddlewareProtocol] | None = None):
        self.middlewares: list[MiddlewareProtocol] = middlewares or []

    def add(self, middleware: MiddlewareProtocol) -> MiddlewareChain:
        """添加中间件"""
        self.middlewares.append(middleware)
        return self

    def execute(self, request: Request, response: Response | None = None) -> Response:
        """执行中间件链"""
        if response is None:
            response = Response(request=request)

        start_time = time.time()

        for middleware in self.middlewares:
            try:
                result = middleware.process(request, response)

                # 应用请求修改
                if result.request_modifications:
                    for key, value in result.request_modifications.items():
                        setattr(request, key, value)

                # 如果中断链,停止执行
                if not result.continue_chain:
                    break

            except Exception as e:
                # 错误处理
                middleware.on_error(e, request)
                if response:
                    response.success = False
                    response.error = str(e)

        # 更新耗时
        response.duration_ms = int((time.time() - start_time) * 1000)

        return response

    def __len__(self) -> int:
        return len(self.middlewares)


# ============================================================================
# 便捷函数
# ============================================================================

def create_default_chain() -> MiddlewareChain:
    """创建默认中间件链"""
    return MiddlewareChain([
        IntentMiddleware(),
        ContextMiddleware(),
        ComplexityMiddleware(),
        SkillMiddleware(),
    ])


def process_request(text: str, **kwargs) -> Response:
    """快捷处理请求"""
    request = Request(text=text, **kwargs)
    chain = create_default_chain()
    return chain.execute(request)


# ============================================================================
# 测试
# ============================================================================

if __name__ == "__main__":
    # 测试用例
    test_cases = [
        "帮我写一个回文检测函数",
        "这个bug一直解决不了",
        "谁最懂Python异步编程",
        "帮我搜索RESTful API最佳实践",
        "今天天气怎么样",
        "/agentic-workflow 开发一个用户系统",
    ]

    chain = create_default_chain()

    print("=" * 60)
    print("Middleware Chain 测试")
    print("=" * 60)

    for text in test_cases:
        request = Request(text=text)
        response = chain.execute(request)

        print(f"\n输入: {text}")
        print(f"  意图: {request.intent}")
        print(f"  阶段: {request.phase.value}")
        print(f"  复杂度: {request.complexity.value}")
        print(f"  使用Skill: {request.use_skill}")
        print(f"  Token预估: {request.tokens_expected}")
        print(f"  阶段序列: {[p.value for p in request.metadata.get('phase_sequence', [])]}")
