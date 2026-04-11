#!/usr/bin/env python3
"""
Shared runtime profile helpers.

This module centralizes the skill-context prompt snippets and token budget
heuristics so the authoritative runtime and middleware prototype do not drift.
"""

from __future__ import annotations

import hashlib
from typing import Any

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

**默认形态**: 轻量排障,先把问题缩小到单点根因

步骤:
1. 收集症状(错误信息/堆栈)
2. 追踪代码找可能原因
3. 验证假设,不对就回退
4. 仅在重复失败时升级到深度调试

输出: 根因/最小修复/回归测试""",
    "REVIEWING": """## REVIEWING 代码审查

**优先级**: P0安全 > P1逻辑/性能 > P2风格

**默认形态**: 先看 contract / owned_files / files_reviewed,再看代码细节

直接输出问题:
- [文件:行号] 问题 (P0/P1/P2)
- 修复: [简洁建议]

**必须项**:
- 先确认审查范围
- 明确列出已审文件
- 区分契约偏差和实现缺陷""",
    "THINKING": """## THINKING 专家推理

**核心**: 谁最懂这个?TA会怎么说?

**Mandatory Think**: 重大决策(git操作,阶段转换)前必须思考

**求是式四步法**:
1. 调查研究: 先收集代码、测试、日志、git history、用户反馈等第一手事实
2. 矛盾分析: 找出主要矛盾、次要矛盾和矛盾的主要方面
3. 群众路线: 把多源事实集中、归纳、再返回验证
4. 持久战略: 判断当前阶段(防御/相持/反攻)与局部攻坚点

回答:
- 调查结论: [一句话]
- 主要矛盾: [A vs B]
- 阶段判断: [战略防御/相持/反攻]
- 局部攻坚点: [具体可做的小切口]
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
- XS/S: TodoWrite + progress.md,不展开完整 spec
- M: spec.md + tasks.md,优先文件化
- L/XL: spec.md + plan.md + tasks.md + .contract.json

**核心**: 先把目标写成文件,再展开方案

步骤:
1. 明确目标(一话说清)
2. 给出 2-3 个方案但保持精简
3. 写出依赖、风险和验收

**默认要求**:
- 先写文件,后写解释
- 优先 plan digest 而不是长 prompt
- XS/S 避免厚重 spec-kit""",
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

DEBUGGING_LOCAL_HINTS = (
    "单文件",
    "单个文件",
    "单点",
    "局部",
    "小修复",
    "小改动",
    "微调",
    "这个 bug",
    "这个bug",
    "这个错误",
    "one file",
    "single file",
    "minor fix",
    "small fix",
)

DEBUGGING_GLOBAL_HINTS = (
    "系统",
    "架构",
    "重构",
    "全局",
    "多文件",
    "多处",
    "全链路",
    "大改",
    "migration",
    "refactor",
    "architecture",
)

THINKING_NEW_PROJECT_HINTS = (
    "从零开始",
    "新项目",
    "新系统",
    "系统设计",
    "架构设计",
    "启动",
    "landing",
    "new project",
    "from scratch",
)

THINKING_COMPLEX_PROBLEM_HINTS = (
    "bug",
    "错误",
    "报错",
    "失败",
    "根因",
    "调试",
    "定位",
    "卡住",
    "复杂问题",
    "疑难",
    "复杂",
)

THINKING_ITERATION_HINTS = (
    "优化",
    "迭代",
    "refine",
    "improve",
    "review",
    "反馈",
    "复盘",
    "改进",
    "再优化",
)


def _is_local_debugging_task(task_text: str | None) -> bool:
    """Heuristic for debugging tasks that are likely local/simple repairs."""
    text = (task_text or "").strip().lower()
    if not text:
        return False
    if any(hint in text for hint in DEBUGGING_GLOBAL_HINTS):
        return False
    return any(hint in text for hint in DEBUGGING_LOCAL_HINTS)


def _contains_any(text: str, hints: tuple[str, ...]) -> bool:
    return any(hint.lower() in text for hint in hints)


def debugging_activation_level_for_context(
    complexity: str,
    task_text: str | None = None,
    owned_files_count: int = 0,
    diff_size: int = 0,
    failure_count: int = 0,
) -> int:
    """Return a context-sensitive debugging activation level.

    The goal is to keep obvious local fixes light, while escalating only when
    the task spans multiple files, has a larger diff surface, or has repeated
    failure history.
    """
    complexity = (complexity or "").upper()

    owned_files_count = max(0, int(owned_files_count or 0))
    diff_size = max(0, int(diff_size or 0))
    failure_count = max(0, int(failure_count or 0))
    is_local = _is_local_debugging_task(task_text)

    if complexity in {"XS", "S"}:
        if failure_count >= 2 or owned_files_count > 1 or diff_size > 2:
            return 25
        if is_local and owned_files_count <= 1 and diff_size <= 2 and failure_count == 0:
            return 0
        return 0

    if is_local and owned_files_count <= 1 and diff_size <= 2 and failure_count == 0:
        return 0

    if owned_files_count <= 1 and diff_size <= 3 and failure_count <= 1:
        return 25

    if owned_files_count == 0 and diff_size == 0 and failure_count == 0:
        return 25

    return 50


def build_thinking_summary(
    task_text: str | None,
    complexity: str,
    memory_hints: list[str] | None = None,
    experience_check: dict[str, Any] | None = None,
    research_summary: dict[str, Any] | None = None,
    contract_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a qiushi-inspired THINKING summary for the next phase context."""
    text = (task_text or "").strip()
    text_lower = text.lower()
    memory_hints = memory_hints or []
    experience_check = experience_check or {}
    research_summary = research_summary or {}
    contract_summary = contract_summary or {}
    complexity = (complexity or "").upper()

    is_new_project = _contains_any(text_lower, THINKING_NEW_PROJECT_HINTS)
    is_complex_problem = _contains_any(text_lower, THINKING_COMPLEX_PROBLEM_HINTS)
    is_iteration = _contains_any(text_lower, THINKING_ITERATION_HINTS)
    is_long_horizon = complexity in {"L", "XL"} or is_new_project or "长期" in text_lower or "分阶段" in text_lower

    if is_new_project:
        workflow = "workflow_1_new_project"
        workflow_label = "新项目启动"
        workflow_steps = ["investigation-first", "contradiction-analysis", "spark-prairie-fire", "protracted-strategy"]
        thinking_methods = ["调查研究", "矛盾分析", "群众路线", "持久战略"]
        major_contradiction = "目标完整性 vs 资源/信息不足"
        stage_judgment = "战略防御期" if is_long_horizon else "战略相持期"
        local_attack_point = "先在最小可验证切片上建立根据地"
        recommendation = "先做调查研究，再抓主要矛盾，最后再决定是否进入规划"
    elif is_iteration:
        workflow = "workflow_3_iteration"
        workflow_label = "方案迭代优化"
        workflow_steps = ["mass-line", "contradiction-analysis", "practice-cognition", "criticism-self-criticism", "mass-line"]
        thinking_methods = ["群众路线", "矛盾分析", "实践认知", "批评自我批评"]
        major_contradiction = "现有方案收益 vs 新问题成本"
        stage_judgment = "战略相持期"
        local_attack_point = "先把反馈收束成一个可验证的改进点"
        recommendation = "先汇聚多源反馈，再聚焦最主要的改进矛盾"
    elif is_complex_problem:
        workflow = "workflow_2_complex_problem"
        workflow_label = "复杂问题攻坚"
        workflow_steps = ["investigation-first", "contradiction-analysis", "concentrate-forces", "practice-cognition", "criticism-self-criticism"]
        thinking_methods = ["调查研究", "矛盾分析", "集中力量", "实践认知", "批评自我批评"]
        major_contradiction = "现象 vs 根因"
        stage_judgment = "战术攻坚"
        local_attack_point = "先复现最小失败样本，围绕主要矛盾单点突破"
        recommendation = "先调查再判断，先验证假说，再决定是否升级到规划/执行"
    else:
        workflow = "workflow_2_complex_problem"
        workflow_label = "复杂问题攻坚"
        workflow_steps = ["investigation-first", "contradiction-analysis", "concentrate-forces", "practice-cognition", "criticism-self-criticism"]
        thinking_methods = ["调查研究", "矛盾分析", "集中力量", "实践认知", "批评自我批评"]
        major_contradiction = "事实 vs 假设"
        stage_judgment = "战术速决" if not is_long_horizon else "战略相持期"
        local_attack_point = "先找到一个最小可验证的切口"
        recommendation = "先把事实收齐，再围绕主要矛盾做最小可行判断"

    investigation_focus = [
        "代码库事实",
        "测试结果",
        "git history",
        "日志/报错",
        "用户反馈",
    ]
    if memory_hints:
        investigation_focus.append("长期记忆 / 经验摘要")
    if experience_check.get("has_relevant_experience"):
        investigation_focus.append("历史经验回流")

    if workflow == "workflow_1_new_project":
        thinking_mode = "investigation_first"
    elif workflow == "workflow_3_iteration":
        thinking_mode = "mass_line_iteration"
    elif workflow == "workflow_2_complex_problem":
        thinking_mode = "contradiction_analysis"
    else:
        thinking_mode = "lightweight"

    research_inputs: list[str] = []
    research_source = str(research_summary.get("research_source", "")).strip()
    if research_source and research_source not in {"(未设置)", "unset", "none"}:
        research_inputs.append(research_source)
    evidence_status = str(research_summary.get("evidence_status", "")).strip()
    if evidence_status:
        research_inputs.append(f"evidence:{evidence_status}")
    search_engine = str(research_summary.get("search_engine", "")).strip()
    if search_engine:
        research_inputs.append(f"engine:{search_engine}")
    sources_count = research_summary.get("sources_count", 0)
    research_inputs.append(f"sources:{int(sources_count or 0)}")

    memory_inputs = [str(hint).strip()[:120] for hint in memory_hints if str(hint).strip()][:3]

    contract_inputs: list[str] = []
    for key in ("goals", "acceptance_criteria", "impact_files", "dependencies", "verification_methods"):
        value = contract_summary.get(key, [])
        if isinstance(value, list):
            entries = [str(item).strip() for item in value if str(item).strip()]
            if entries:
                contract_inputs.append(f"{key}:{len(entries)}")
                contract_inputs.extend(entries[:2])
        elif isinstance(value, str) and value.strip():
            contract_inputs.append(f"{key}:{value.strip()}")

    if contract_summary.get("status"):
        contract_inputs.append(f"status:{str(contract_summary.get('status')).strip()}")

    confidence_level = "low"
    if evidence_status == "verified" and memory_inputs and contract_inputs:
        confidence_level = "high"
    elif evidence_status in {"verified", "degraded"} or memory_inputs or contract_inputs or experience_check.get("has_relevant_experience"):
        confidence_level = "medium"

    trace_basis = "|".join(
        [
            text,
            complexity,
            thinking_mode,
            evidence_status or "unset",
            str(len(memory_inputs)),
            str(len(contract_inputs)),
        ]
    )
    reasoning_trace_id = hashlib.sha1(trace_basis.encode("utf-8", errors="ignore")).hexdigest()[:12]

    return {
        "workflow": workflow,
        "workflow_label": workflow_label,
        "workflow_steps": workflow_steps,
        "thinking_methods": thinking_methods,
        "investigation_focus": investigation_focus,
        "thinking_mode": thinking_mode,
        "major_contradiction": major_contradiction,
        "stage_judgment": stage_judgment,
        "local_attack_point": local_attack_point,
        "recommendation": recommendation,
        "memory_hints_count": len(memory_hints),
        "research_inputs": research_inputs,
        "memory_inputs": memory_inputs,
        "contract_inputs": contract_inputs,
        "reasoning_trace_id": reasoning_trace_id,
        "confidence_level": confidence_level,
    }


def build_skill_context(
    phase: str,
    complexity: str,
    activation_level: int | None = None,
) -> tuple[str, int]:
    """Build skill context from tiered files, with PHASE_PROMPTS fallback.

    When tier files exist (skills/<phase>/tier_*.md), assembles them based on
    activation_level. Falls back to legacy PHASE_PROMPTS when tiers are absent.

    Args:
        phase: Phase name (e.g., "EXECUTING")
        complexity: Complexity level ("XS"/"S"/"M"/"L"/"XL")
        activation_level: 0-100 tier depth. If None, inferred from complexity.
    """
    phase = (phase or "").upper()
    complexity = (complexity or "").upper()

    # Infer activation_level from complexity if not provided
    if activation_level is None:
        activation_level = _infer_activation_from_complexity(phase, complexity)

    # Try tier-based assembly first
    try:
        from skill_assembler import assemble_skill_prompt
        prompt, tokens = assemble_skill_prompt(phase, activation_level)
        if prompt:
            return prompt, tokens
    except (ImportError, Exception):
        pass  # Fall through to legacy

    # Legacy fallback: PHASE_PROMPTS (kept for phases without tier files)
    phase_prompt = PHASE_PROMPTS.get(phase, "")
    prompt = (MINIMAL_CORE + "\n\n" + phase_prompt).strip() if phase_prompt else MINIMAL_CORE
    tokens = COMPLEXITY_TOKENS.get(complexity, 1500)
    return prompt, tokens


def _infer_activation_from_complexity(phase: str, complexity: str) -> int:
    """Map phase + complexity to a default activation level.

    This is the fallback when callers don't pass an explicit level.
    """
    if complexity in {"XS", "S"}:
        return 25
    if complexity == "M":
        return 50
    # L, XL
    return 75


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


def skill_activation_level_for_phase(
    phase: str,
    complexity: str,
    intent: str | None = None,
    task_text: str | None = None,
    owned_files_count: int | None = None,
    diff_size: int | None = None,
    failure_count: int = 0,
) -> int:
    """Return the default skill activation level for a phase/complexity pair."""
    phase = (phase or "").upper()
    complexity = (complexity or "").upper()
    intent = (intent or "").upper()

    if not should_use_skill_for_phase(
        phase,
        complexity,
        intent,
        task_text,
        owned_files_count=owned_files_count,
        diff_size=diff_size,
        failure_count=failure_count,
    ):
        return 0
    if phase == "EXECUTING":
        return 75 if complexity not in {"XS", "S"} else 50
    if phase == "REVIEWING":
        return 50
    if phase == "DEBUGGING":
        return debugging_activation_level_for_context(
            complexity,
            task_text=task_text,
            owned_files_count=owned_files_count or 0,
            diff_size=diff_size or 0,
            failure_count=failure_count,
        )
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


def should_use_skill_for_phase(
    phase: str,
    complexity: str,
    intent: str | None = None,
    task_text: str | None = None,
    owned_files_count: int | None = None,
    diff_size: int | None = None,
    failure_count: int = 0,
) -> bool:
    """Return the default skill on/off decision for a phase/complexity pair."""
    phase = (phase or "").upper()
    complexity = (complexity or "").upper()
    intent = (intent or "").upper()

    if phase in {"CHAT", "THINKING", "RESEARCH", "PLANNING"} or intent == "FULL_WORKFLOW":
        return False
    if phase == "DEBUGGING":
        return debugging_activation_level_for_context(
            complexity,
            task_text=task_text,
            owned_files_count=owned_files_count or 0,
            diff_size=diff_size or 0,
            failure_count=failure_count,
        ) > 0
    if phase == "REVIEWING":
        return complexity not in {"XS", "S"}
    return True
