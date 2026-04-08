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

    # 核心工作流 - 极简版,只包含绝对必要原则
    # 实验发现: 3行核心原则最优,不会对任何阶段造成干扰
    MINIMAL_CORE = """## 原则
- 回答简洁,不废话
- 有证据再声称完成
- 先验证再结论"""

    # 各阶段对应的精简prompt - 基于实验优化的版本
    # 实验发现: 阶段隔离注入 + 极简核心原则 最优
    PHASE_PROMPTS = {
        # EXECUTING: 借鉴gstack "Boil the Lake" + Fix-First
        Phase.EXECUTING: """## EXECUTING 执行

**铁律**: 先写测试再实现,先验证再声称完成

**Boil the Lake原则**: 完整性与AI能力成正比,不要省步骤

**Fix-First决策**:
- AUTO-FIX: 机械性问题(typo, import, 格式化)→直接修复
- ASK: 判断性问题(架构, 设计)→先问用户

**Voice规则**:
- 禁止: em dashes, "delve/crucial/robust"等AI词汇
- 使用: 具体file:line引用,简洁动词

步骤:
1. 写失败的测试
2. 写最小代码通过
3. 重构优化

**验证**: 运行测试确认,不要只说"完成了".""",

        # DEBUGGING: 4步调试 + 3次失败规则 (66.7%获胜率)
        Phase.DEBUGGING: """## DEBUGGING 调试

**铁律**: 不定位根因不修复

步骤:
1. 收集症状(错误信息/堆栈)
2. 追踪代码找可能原因
3. 验证假设,不对就回退
4. 3次失败→考虑架构问题

输出: 根因/修复/回归测试""",

        # REVIEWING: P0/P1/P2优先级 (66.7%-100%获胜率)
        Phase.REVIEWING: """## REVIEWING 代码审查

**优先级**: P0安全 > P1逻辑/性能 > P2风格

直接输出问题:
- [文件:行号] 问题 (P0/P1/P2)
- 修复: [简洁建议]""",

        # THINKING: "谁最懂"框架 + Mandatory Think
        Phase.THINKING: """## THINKING 专家推理

**核心**: 谁最懂这个?TA会怎么说?

**Mandatory Think**: 重大决策(git操作,阶段转换)前必须思考

回答:
- 本质: [一句话]
- 权衡: [最多3观点,各20字]
- 建议: [1个明确建议]""",

        # RESEARCH: 借鉴deer-flow Phase Methodology + Quality Gate
        Phase.RESEARCH: """## RESEARCH 搜索研究

**阶段方法论**:
1. 广泛探索 - 快速扫描多个来源
2. 深度挖掘 - 聚焦权威来源
3. 综合验证 - 检查一致性

**Quality Gate**: 自问"能自信回答吗?"
- 如果NO→继续研究
- 如果YES→输出结论

**执行**:
1. 搜索: 具体技术名词+"best practices"
2. 深度获取: 不只看摘要,要fetch完整内容
3. 来源优先级: 官方文档>开源>博客>AI生成
4. 输出: 关键发现+3条内可操作建议+来源

**铁律**: 搜索不可用时直接说明,禁止静默降级

**时间感知**: 检查当前日期,趋势用年月""",

        # PLANNING: 简化版 - 保留核心路由
        Phase.PLANNING: """## PLANNING 任务规划

**复杂度路由**:
- XS/S: TodoWrite拆分,不用spec文件
- M: spec.md + tasks.md
- L/XL: spec.md + plan.md + tasks.md + .contract.json

**核心**: 不只拆分,要生成多种方案

步骤:
1. 明确目标(一话说清)
2. 生成2-3方案(最小/折中/理想)
3. 推荐明确方案和理由

**反模式**: XS/S禁止完整spec-kit""",

        Phase.REFINING: """## 迭代优化框架

**优化优先级**:
1. 正确性 - 修复bug/边缘case
2. 性能 - 降低复杂度/减少资源
3. 可维护性 - 清理代码/添加文档

**迭代原则**:
- 每次只做一件事
- 小步提交,随时可回退
- 重构不改变外部行为

**输出格式**:
## 当前问题
[具体问题描述]

## 优化方案
[具体改进措施]

## 验证
[如何验证优化效果]""",
    }

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
        phase_prompt = self.PHASE_PROMPTS.get(request.phase, "")
        prompt = self.MINIMAL_CORE + "\n\n" + phase_prompt

        # 根据复杂度调整
        if request.complexity == Complexity.XL:
            # 复杂任务可以稍微详细一点
            prompt = prompt + "\n\n这是一个复杂任务,请深入分析。"
            request.tokens_expected = 4000
        elif request.complexity == Complexity.L:
            request.tokens_expected = 2500
        elif request.complexity == Complexity.M:
            request.tokens_expected = 1500
        else:
            request.tokens_expected = 1000

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
