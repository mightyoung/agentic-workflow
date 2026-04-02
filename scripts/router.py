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
from typing import Optional, Tuple

# 路由关键词配置
ROUTE_KEYWORDS = {
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


def detect_stage(text: str) -> str:
    """检测应该触发的阶段"""
    text_lower = text.lower()
    stage_priority = {
        "DEBUGGING": 7,
        "REVIEWING": 6,
        "REFINING": 5,
        "EXPLORING": 5,
        "OFFICE_HOURS": 5,
        "THINKING": 4,
        "PLANNING": 3,
        "RESEARCH": 2,
        "EXECUTING": 1,
        "SUBAGENT": 0,
    }
    matches = []

    for stage, keywords in ROUTE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                matches.append((len(keyword), stage_priority.get(stage, 0), stage))

    if matches:
        matches.sort(reverse=True)
        return matches[0][2]

    return "EXECUTING"  # 默认


def route(text: str, use_semantic: bool = False) -> Tuple[str, str]:
    """
    执行路由决策

    Args:
        text: 用户消息
        use_semantic: 是否优先使用语义路由

    Returns:
        (触发类型, 阶段)
        触发类型: FULL_WORKFLOW / STAGE / DIRECT_ANSWER / NONE
    """
    # Step 1: 检查负面触发
    if check_negative_trigger(text):
        return ("DIRECT_ANSWER", "闲聊")

    # Step 2: 检查强制触发
    force = check_force_trigger(text)
    if force:
        return ("FULL_WORKFLOW", "完整流程")

    # Step 3: 尝试语义路由 (如果启用)
    if use_semantic:
        try:
            import os
            experimental_path = os.path.join(os.path.dirname(__file__), "experimental")
            if experimental_path not in sys.path:
                sys.path.insert(0, experimental_path)
            from semantic_router import route_semantic as semantic_route
            trigger_type, phase = semantic_route(text)
            if trigger_type == "STAGE":
                return (trigger_type, phase)
        except ImportError:
            pass  # 降级到关键词
        except Exception:
            pass  # 降级到关键词

    # Step 4: 检测阶段
    stage = detect_stage(text)
    return ("STAGE", stage)


def format_output(result: Tuple[str, str], text: str, format: str = 'simple') -> str:
    """格式化输出"""
    trigger_type, stage = result

    if format == 'json':
        import json
        return json.dumps({
            "input": text,
            "trigger_type": trigger_type,
            "stage": stage,
            "should_trigger_workflow": trigger_type in ("FULL_WORKFLOW", "STAGE")
        }, ensure_ascii=False, indent=2)

    elif format == 'simple':
        if trigger_type == "DIRECT_ANSWER":
            return "DIRECT_ANSWER | 闲聊 | NO_WORKFLOW"
        elif trigger_type == "FULL_WORKFLOW":
            return "FULL_WORKFLOW | 完整流程 | WORKFLOW"
        else:
            return f"STAGE | {stage} | WORKFLOW"

    else:  # verbose
        lines = [
            "=" * 50,
            f"输入: {text}",
            "-" * 50,
            f"触发类型: {trigger_type}",
            f"阶段: {stage}",
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
