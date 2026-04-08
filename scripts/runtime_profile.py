#!/usr/bin/env python3
"""
Shared runtime profile helpers.

This module centralizes the skill-context prompt snippets and token budget
heuristics so the authoritative runtime and middleware prototype do not drift.
"""

from __future__ import annotations

MINIMAL_CORE = """## 原则
- 回答简洁,不废话
- 有证据再声称完成
- 先验证再结论"""

SKILL_POLICY_RECOMMENDATIONS = {
    "EXECUTING": "default_enable",
    "REVIEWING": "conditional_enable",
    "DEBUGGING": "conditional_enable_after_optimization",
    "RESEARCH": "defer_or_lighten",
    "PLANNING": "defer",
    "THINKING": "disable",
    "FULL_WORKFLOW": "disable",
}

PHASE_PROMPTS = {
    "EXECUTING": """## EXECUTING 执行

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
    "DEBUGGING": """## DEBUGGING 调试

**铁律**: 不定位根因不修复

步骤:
1. 收集症状(错误信息/堆栈)
2. 追踪代码找可能原因
3. 验证假设,不对就回退
4. 3次失败→考虑架构问题

输出: 根因/修复/回归测试""",
    "REVIEWING": """## REVIEWING 代码审查

**优先级**: P0安全 > P1逻辑/性能 > P2风格

直接输出问题:
- [文件:行号] 问题 (P0/P1/P2)
- 修复: [简洁建议]""",
    "THINKING": """## THINKING 专家推理

**核心**: 谁最懂这个?TA会怎么说?

**Mandatory Think**: 重大决策(git操作,阶段转换)前必须思考

回答:
- 本质: [一句话]
- 权衡: [最多3观点,各20字]
- 建议: [1个明确建议]""",
    "RESEARCH": """## RESEARCH 搜索研究

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
    "PLANNING": """## PLANNING 任务规划

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
    "REFINING": """## 迭代优化框架

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

COMPLEXITY_TOKENS = {
    "XS": 500,
    "S": 500,
    "M": 1000,
    "L": 1500,
    "XL": 2500,
}


def build_skill_context(phase: str, complexity: str) -> tuple[str, int]:
    """Build skill context and expected tokens from phase and complexity."""
    phase_prompt = PHASE_PROMPTS.get(phase, "")
    prompt = (MINIMAL_CORE + "\n\n" + phase_prompt).strip()
    tokens = COMPLEXITY_TOKENS.get(complexity, 1500)
    return prompt, tokens


def token_budget_for_complexity(complexity: str) -> int:
    """Return the shared token budget heuristic for a complexity level."""
    return COMPLEXITY_TOKENS.get(complexity, 1500)


def skill_policy_for_phase(phase: str, complexity: str, intent: str | None = None) -> str:
    """Return the recommended skill policy for a phase/complexity pair."""
    phase = (phase or "").upper()
    complexity = (complexity or "").upper()
    intent = (intent or "").upper()

    if phase == "CHAT" or intent == "FULL_WORKFLOW":
        return "disable"
    if phase == "DEBUGGING":
        if complexity in {"XS", "S"}:
            return "conditional_enable_after_optimization"
        return SKILL_POLICY_RECOMMENDATIONS["DEBUGGING"]
    if phase == "REVIEWING":
        if complexity in {"XS", "S"}:
            return "conditional_enable"
        return SKILL_POLICY_RECOMMENDATIONS["REVIEWING"]
    return SKILL_POLICY_RECOMMENDATIONS.get(phase, "default_enable")


def skill_activation_level_for_phase(phase: str, complexity: str, intent: str | None = None) -> int:
    """Return the default skill activation level for a phase/complexity pair."""
    phase = (phase or "").upper()
    complexity = (complexity or "").upper()
    intent = (intent or "").upper()

    if not should_use_skill_for_phase(phase, complexity, intent):
        return 0
    if phase == "EXECUTING":
        return 75 if complexity not in {"XS", "S"} else 50
    if phase == "REVIEWING":
        return 50
    if phase == "DEBUGGING":
        return 25 if complexity not in {"XS", "S"} else 0
    return 50


def escalate_skill_activation_level(current_level: int) -> int:
    """Increase skill activation after a failure, capped at 100."""
    if current_level <= 0:
        return 0
    if current_level < 50:
        return 50
    if current_level < 75:
        return 75
    return 100


def should_use_skill_for_phase(phase: str, complexity: str, intent: str | None = None) -> bool:
    """Return the default skill on/off decision for a phase/complexity pair."""
    phase = (phase or "").upper()
    complexity = (complexity or "").upper()
    intent = (intent or "").upper()

    if phase in {"CHAT", "THINKING", "RESEARCH", "PLANNING"} or intent == "FULL_WORKFLOW":
        return False
    if phase == "DEBUGGING":
        return complexity not in {"XS", "S"}
    if phase == "REVIEWING":
        return complexity not in {"XS", "S"}
    return True
