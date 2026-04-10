#!/usr/bin/env python3
"""
Router - Routing Decision Assistant

Supports two routing modes:
1. Semantic Router - Uses embedding similarity
2. Keyword Router - Lightweight keyword matching

Behavior order:
1. Negative trigger filter -> DIRECT_ANSWER
2. Force trigger -> FULL_WORKFLOW
3. Semantic routing (if available and confidence sufficient)
4. Keyword routing as fallback
5. Default to EXECUTING if no match

Usage:
    python3 router.py "user message"
    python3 router.py --semantic "user message"  # Force semantic routing
"""

import re
import sys
from typing import Any, Optional

# 路由关键词配置
ROUTE_KEYWORDS = {
    "ANALYZING": [
        "分析需求", "需求分析", "分析一下", "分析这个",
        "需求梳理", "梳理需求", "理解需求", "需求理解",
        "analyze", "analysis", "需求"
    ],
    "RESEARCH": [
        "帮我搜索", "查找最佳实践", "调研一下", "调研", "搜索一下",
        "网络上搜索", "在网上搜索", "最佳实践", "有什么", "有哪些",
        "选型", "参考", "案例", "了解一下", "想知道", "查一下",
        "找一下", "有没有", "哪里有", "如何实现", "怎么做的",
        "怎么做", "如何做", "怎么实现", "方法",
        "部署", "数据库优化", "research", "best practice", "case study"
    ],
    "THINKING": [
        "谁最懂", "专家", "分析", "理解", "看看", "分析一下",
        "这个怎么实现", "那个行不行", "哪个好", "建议", "看法",
        "思路", "怎么选", "哪个更", "有什么区别", "帮我看看",
        "给点意见", "顶级", "怎么看", "优化", "怎么优化",
        "best minds", "会怎么做", "顶级安全专家",
        "是什么原理", "原理", "底层逻辑"
    ],
    "PLANNING": [
        "计划", "规划", "拆分", "设计", "安排", "整理一下",
        "要做什么", "步骤", "先后顺序", "先做哪个", "如何开始",
        "从哪里入手", "规划一下", "安排一下", "plan", "break down"
    ],
    "DEBUGGING": [
        "帮我调试", "修复这个bug", "报错如下", "报错信息", "错误如下",
        "bug", "错误", "调试", "修复", "崩溃", "异常", "不动",
        "失败", "回报", "卡住", "挂起", "响应很慢", "太慢了",
        "跑不通", "不能用", "失效", "超时", "卡死", "无响应",
        "不动了", "没有反应", "卡住了", "运行出错", "启动失败",
        "连接失败", "nameerror", "定位", "定位问题", "报错",
        "运行报错", "崩溃了", "程序崩溃了", "崩溃了帮我看看"
    ],
    "SUBAGENT": [
        "给我结果就行", "直接给我", "就要结果", "不用解释",
        "不要过程", "直接输出", "出结果", "只要结果",
        "just give me", "just result", "direct output", "no explanation"
    ],
    "REVIEWING": [
        "代码审查", "帮我review", "审查这段代码", "审计", "审查",
        "review", "检查", "审查一下", "代码审查建议"
    ],
    "EXECUTING": [
        "写一个", "帮我写", "实现", "开发", "创建", "编写",
        "implement", "build", "create", "develop", "write code"
    ],
    "REFINING": [
        "迭代", "优化", "精炼", "改进", "完善", "再优化",
        "调优", "打磨", "迭代优化", "refine", "improve", "iterate"
    ],
    "EXPLORING": [
        "实验", "想法", "深层", "本质", "探索", "挖掘",
        "思考", "研究", "investigate", "explore",
        "深入分析", "根本原因", "为什么会这样"
    ],
    "OFFICE_HOURS": [
        "产品想法", "需求不明确", "咨询", "讨论一下",
        "该怎么选", "纠结", "拿不定主意", "意见",
        "产品咨询", "建议", "帮我出主意",
        "product idea", "not sure", "advice", "consult"
    ]
}

# 强制触发关键词（优先级最高）
FORCE_TRIGGERS = {
    "/agentic-workflow": "FULL_WORKFLOW",
    "继续": "FULL_WORKFLOW",
    "继续下一步": "FULL_WORKFLOW",
    "继续任务": "FULL_WORKFLOW",
    "下一步": "FULL_WORKFLOW",
    "继续进行": "FULL_WORKFLOW",
    "继续执行": "FULL_WORKFLOW",
    "接着来": "FULL_WORKFLOW",
    "继续做": "FULL_WORKFLOW"
}

# 负面触发关键词（不触发工作流）
NEGATIVE_TRIGGERS = [
    "天气", "笑话", "你好", "谢谢", "嗨",
    "嘿", "干嘛呢", "最近怎样"
]

NEGATIVE_REGEX_TRIGGERS = [
    r"\bhi\b",
    r"\bhello\b",
    r"\bbye\b",
    r"\bok\b",
    r"\byes\b",
    r"\bno\b",
    r"\bmaybe\b",
]

# 负面触发上下文（如果有开发相关词则不算负面）
NEGATIVE_CONTEXTS = ["开发", "代码", "帮我", "问题", "需要"]


# Complexity estimation keywords
COMPLEXITY_KEYWORDS = {
    "XL": [
        "系统设计", "设计系统", "新系统", "架构设计", "从零开始",
        "全新项目", "微服务", "分布式", "system design", "new system",
        "from scratch", "architecture", "设计一个", "搭建一个"
    ],
    "L": [
        "重构", "重写", "模块", "迁移", "升级", "整个",
        "全面", "大改", "refactor", "rewrite", "module",
        "migration", "全部改", "重新设计", "多个文件"
    ],
    "M": [
        "新增", "功能", "feature", "endpoint", "api",
        "接口", "页面", "组件", "add", "implement",
        "开发一个", "写一个", "实现一个"
    ],
    "S": [
        "修复", "修改", "改一下", "fix", "bug", "错误",
        "调整", "更新", "update", "change", "小改"
    ],
    "XS": [
        "typo", "拼写", "格式", "注释", "import", "rename",
        "重命名", "删除", "移除", "简单", "一行"
    ],
}

# Phase sequences per complexity level
PHASE_SEQUENCES = {
    "XS": ["EXECUTING", "COMPLETE"],
    "S": ["EXECUTING", "REVIEWING", "COMPLETE"],
    "M": ["PLANNING", "EXECUTING", "REVIEWING", "COMPLETE"],
    "L": ["RESEARCH", "THINKING", "PLANNING", "EXECUTING", "REVIEWING", "COMPLETE"],
    "XL": ["RESEARCH", "THINKING", "PLANNING", "EXECUTING", "REVIEWING", "REFINING", "COMPLETE"],
}

SKILL_RERANK_TOP_K = 5


def _normalize_route_text(text: str) -> str:
    return text.lower().strip()


def _extract_route_terms(text: str) -> list[str]:
    """Extract lightweight terms for retrieval/rerank."""
    normalized = _normalize_route_text(text)
    raw_terms = re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z0-9_]+", normalized)
    terms: list[str] = []
    for term in raw_terms:
        cleaned = term.strip().lower()
        if cleaned and cleaned not in terms:
            terms.append(cleaned)
    return terms


def _collect_stage_candidates(text: str) -> list[dict[str, Any]]:
    """Collect all stage candidates before reranking."""
    text_lower = text.lower()
    stage_priority = {
        "DEBUGGING": 7,
        "REVIEWING": 6,
        "REFINING": 5,
        "EXPLORING": 5,
        "OFFICE_HOURS": 5,
        "ANALYZING": 4,
        "THINKING": 4,
        "PLANNING": 3,
        "RESEARCH": 2,
        "EXECUTING": 1,
        "SUBAGENT": 0,
    }
    candidates: list[dict[str, Any]] = []

    for stage, keywords in ROUTE_KEYWORDS.items():
        matched_keywords = [keyword for keyword in keywords if keyword in text_lower]
        if not matched_keywords:
            continue

        relevance = min(max(len(keyword) for keyword in matched_keywords) / max(len(text_lower), 1), 0.9)
        priority = stage_priority.get(stage, 0)
        confidence = min(relevance + (priority * 0.1), 0.95)
        candidates.append(
            {
                "stage": stage,
                "base_confidence": confidence,
                "priority": priority,
                "matched_keywords": matched_keywords,
                "match_count": len(matched_keywords),
            }
        )

    candidates.sort(key=lambda item: (item["base_confidence"], item["priority"], item["match_count"]), reverse=True)
    return candidates


def _skill_body_text(skill: Any) -> str:
    metadata = getattr(skill, "metadata", None)
    parts: list[str] = []
    if metadata:
        parts.extend(
            [
                str(getattr(metadata, "name", "")),
                str(getattr(metadata, "description", "")),
                " ".join(getattr(metadata, "tags", []) or []),
            ]
        )
    parts.extend(
        [
            str(getattr(skill, "overview", "")),
            str(getattr(skill, "entry_criteria", "")),
            str(getattr(skill, "core_process", "")),
            str(getattr(skill, "phase_prompt_template", "")),
            str(getattr(skill, "completion_template", "")),
            str(getattr(skill, "raw_content", "")),
        ]
    )
    return "\n".join(part for part in parts if part).lower()


def _score_skill_candidate(text: str, candidate: dict[str, Any], skill: Any | None) -> dict[str, Any]:
    """Score a stage candidate using the loaded skill body."""
    base_confidence = float(candidate.get("base_confidence", 0.0))
    if skill is None:
        return {
            **candidate,
            "skill_name": None,
            "skill_score": 0.0,
            "score": base_confidence,
            "score_reason": "no skill body available",
        }

    prompt_terms = _extract_route_terms(text)
    skill_text = _skill_body_text(skill)
    prompt_text = _normalize_route_text(text)
    matched_terms = [term for term in prompt_terms if term and term in skill_text]
    matched_keywords = [kw for kw in candidate.get("matched_keywords", []) if str(kw).lower() in skill_text]

    term_score = len(matched_terms) / max(len(prompt_terms), 1)
    keyword_score = len(matched_keywords) / max(len(candidate.get("matched_keywords", [])) or 1, 1)

    metadata_bonus = 0.0
    metadata = getattr(skill, "metadata", None)
    if metadata:
        skill_name = str(getattr(metadata, "name", "")).lower()
        description = str(getattr(metadata, "description", "")).lower()
        if candidate["stage"].lower() in skill_name:
            metadata_bonus += 0.1
        if candidate["stage"].lower() in description:
            metadata_bonus += 0.05

    exact_phrase_bonus = 0.0
    for phrase in matched_keywords[:3]:
        if phrase and phrase.lower() in prompt_text and phrase.lower() in skill_text:
            exact_phrase_bonus += 0.05

    skill_score = min(term_score * 0.55 + keyword_score * 0.25 + metadata_bonus + exact_phrase_bonus, 1.0)
    combined_score = min(base_confidence * 0.45 + skill_score * 0.55, 0.98)

    return {
        **candidate,
        "skill_name": getattr(getattr(skill, "metadata", None), "name", candidate["stage"].lower()),
        "skill_score": round(skill_score, 3),
        "score": round(combined_score, 3),
        "score_reason": f"terms={matched_terms[:5]} keywords={matched_keywords[:5]}",
    }


def rerank_stage_candidates(
    text: str,
    candidates: list[dict[str, Any]],
    skills_dir: str = "skills",
    top_k: int = SKILL_RERANK_TOP_K,
) -> list[dict[str, Any]]:
    """Retrieve and rerank stage candidates using full skill bodies."""
    if not candidates:
        return []

    try:
        from skill_loader import SkillLoader
    except Exception:
        return [
            _score_skill_candidate(text, candidate, None)
            for candidate in candidates[:top_k]
        ]

    loader = SkillLoader(skills_dir)
    reranked: list[dict[str, Any]] = []
    for candidate in candidates[:top_k]:
        skill = loader.load_skill(candidate["stage"])
        reranked.append(_score_skill_candidate(text, candidate, skill))

    reranked.sort(key=lambda item: (item["score"], item["base_confidence"], item["priority"], item["match_count"]), reverse=True)
    return reranked


def estimate_complexity(text: str) -> tuple[str, float]:
    """
    Estimate task complexity from user input.

    Returns:
        (complexity, confidence) where complexity is XS/S/M/L/XL
        and confidence is 0.0-1.0
    """
    text_lower = text.lower()
    scores: dict[str, float] = {}

    for level, keywords in COMPLEXITY_KEYWORDS.items():
        score = 0.0
        for kw in keywords:
            if kw in text_lower:
                score += len(kw) / max(len(text_lower), 1)
        scores[level] = score

    if not any(scores.values()):
        return ("M", 0.3)  # Default: medium complexity, low confidence

    best = max(scores, key=lambda k: scores[k])
    confidence = min(scores[best] * 5, 0.95)  # Scale up, cap at 0.95
    return (best, confidence)


def get_phase_sequence(complexity: str) -> list[str]:
    """Get the required phase sequence for a given complexity level."""
    return PHASE_SEQUENCES.get(complexity, PHASE_SEQUENCES["M"])


def check_negative_trigger(text: str) -> bool:
    """检查是否应该直接回答（不触发工作流）"""
    text_lower = text.lower()

    # 检查是否包含负面关键词
    has_negative = any(neg in text_lower for neg in NEGATIVE_TRIGGERS)
    if not has_negative:
        has_negative = any(re.search(pattern, text_lower) for pattern in NEGATIVE_REGEX_TRIGGERS)
    if not has_negative:
        return False

    # 如果包含负面关键词，同时包含开发相关词，则不视为负面
    has_context = any(ctx in text_lower for ctx in NEGATIVE_CONTEXTS)
    if has_negative and has_context:
        return False

    return True


def check_force_trigger(text: str) -> Optional[str]:
    """检查强制触发关键词"""
    text_lower = text.lower()

    # 检查 /agentic-workflow 命令
    if "/agentic-workflow" in text:
        return "FULL_WORKFLOW"

    # 检查继续任务
    for keyword, trigger in FORCE_TRIGGERS.items():
        if keyword in text_lower:
            return trigger

    return None


def detect_stage(text: str) -> tuple[str, float]:
    """
    Detect which phase to trigger.

    Returns:
        (stage, confidence) where confidence is 0.0-1.0
    """
    candidates = _collect_stage_candidates(text)
    if candidates:
        best = candidates[0]
        return best["stage"], float(best["base_confidence"])

    return "EXECUTING", 0.1  # Default: low confidence


def route(
    text: str,
    use_semantic: bool = False,
    use_skill_rerank: bool = True,
    skills_dir: str = "skills",
) -> tuple[str, str, float]:
    """
    Execute routing decision.

    Args:
        text: User message
        use_semantic: Whether to prefer semantic routing

    Returns:
        (trigger_type, phase, confidence)
        trigger_type: FULL_WORKFLOW / STAGE / DIRECT_ANSWER / NONE
        phase: Phase name
        confidence: 0.0-1.0 confidence score
    """
    # Step 1: Check negative trigger
    if check_negative_trigger(text):
        return ("DIRECT_ANSWER", "闲聊", 1.0)

    # Step 2: Check force trigger
    force = check_force_trigger(text)
    if force:
        return ("FULL_WORKFLOW", "完整流程", 1.0)

    # Step 3: Try semantic routing if enabled
    if use_semantic:
        try:
            import os
            experimental_path = os.path.join(os.path.dirname(__file__), "experimental")
            if experimental_path not in sys.path:
                sys.path.insert(0, experimental_path)
            from semantic_router import route_semantic as semantic_route
            trigger_type, phase = semantic_route(text)
            if trigger_type == "STAGE":
                return (trigger_type, phase, 0.8)  # Semantic gives high confidence
        except ImportError:
            pass  # Fallback to keyword
        except Exception:
            pass  # Fallback to keyword

    # Step 4: Detect stage (keyword-based)
    candidates = _collect_stage_candidates(text)
    if not candidates:
        return ("STAGE", "EXECUTING", 0.1)

    if use_skill_rerank and len(candidates) > 1:
        reranked = rerank_stage_candidates(text, candidates, skills_dir=skills_dir)
        if reranked:
            best = reranked[0]
            return ("STAGE", best["stage"], float(best["score"]))

    best = candidates[0]
    return ("STAGE", best["stage"], float(best["base_confidence"]))


def route_with_complexity(
    text: str,
    use_semantic: bool = False,
    use_skill_rerank: bool = True,
    skills_dir: str = "skills",
) -> dict:
    """
    Extended routing that includes complexity estimation and phase sequence.

    Returns dict with:
        trigger_type, phase, confidence, complexity, complexity_confidence, phase_sequence
    """
    trigger_type, phase, confidence = route(
        text,
        use_semantic=use_semantic,
        use_skill_rerank=use_skill_rerank,
        skills_dir=skills_dir,
    )
    complexity, complexity_conf = estimate_complexity(text)
    phase_sequence = get_phase_sequence(complexity)

    return {
        "trigger_type": trigger_type,
        "phase": phase,
        "confidence": confidence,
        "complexity": complexity,
        "complexity_confidence": complexity_conf,
        "phase_sequence": phase_sequence,
        "total_phases": len(phase_sequence),
    }


def format_output(result: tuple[str, str, float], text: str, format: str = 'simple') -> str:
    """Format routing output"""
    trigger_type, stage, confidence = result

    if format == 'json':
        import json
        return json.dumps({
            "input": text,
            "trigger_type": trigger_type,
            "stage": stage,
            "confidence": round(confidence, 3),
            "should_trigger_workflow": trigger_type in ("FULL_WORKFLOW", "STAGE")
        }, ensure_ascii=False, indent=2)

    elif format == 'simple':
        if trigger_type == "DIRECT_ANSWER":
            return f"DIRECT_ANSWER | 闲聊 | NO_WORKFLOW | conf={confidence:.2f}"
        elif trigger_type == "FULL_WORKFLOW":
            return f"FULL_WORKFLOW | 完整流程 | WORKFLOW | conf={confidence:.2f}"
        else:
            return f"STAGE | {stage} | WORKFLOW | conf={confidence:.2f}"

    else:  # verbose
        lines = [
            "=" * 50,
            f"输入: {text}",
            "-" * 50,
            f"触发类型: {trigger_type}",
            f"阶段: {stage}",
            f"置信度: {confidence:.3f}",
            f"是否触发工作流: {'是' if trigger_type in ('FULL_WORKFLOW', 'STAGE') else '否'}",
            "=" * 50
        ]
        return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Router - 路由决策辅助工具")
    parser.add_argument("text", nargs="?", help="要路由的文本")
    parser.add_argument("--semantic", action="store_true", help="使用语义路由")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.text:
        text = args.text
    elif not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    else:
        print("Router - 路由决策辅助工具")
        print("输入消息进行路由判断 (Ctrl+C 退出)")
        print("-" * 50)

        while True:
            try:
                text = input("\n> ")
                if not text.strip():
                    continue

                result = route(text)
                print(format_output(result, text, 'verbose'))
            except KeyboardInterrupt:
                print("\n退出")
                break
        return 0

    result = route(text)
    print(format_output(result, text, 'simple'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
