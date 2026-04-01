#!/usr/bin/env python3
"""
完整质量提升测试 - 执行全部20个质量测试任务
需要 Claude API 来执行对比测试
"""

import os
import json
import time
import asyncio
from typing import Dict

# 完整的20个质量测试任务
TEST_TASKS = [
    # 任务完成率相关
    {
        "id": "task_01",
        "prompt": "用TDD方式开发一个计算器，支持加减乘除",
        "module": "EXECUTING",
        "metric": "completion_rate"
    },
    {
        "id": "task_02",
        "prompt": "帮我规划一个电商网站开发",
        "module": "PLANNING",
        "metric": "completion_rate"
    },
    {
        "id": "task_03",
        "prompt": "谁最懂Python异步编程？",
        "module": "THINKING",
        "metric": "completion_rate"
    },
    # 执行时间相关
    {
        "id": "task_04",
        "prompt": "帮我开发一个用户认证系统",
        "module": "EXECUTING",
        "metric": "execution_time"
    },
    {
        "id": "task_05",
        "prompt": "修复这个bug: NameError: x is not defined",
        "module": "DEBUGGING",
        "metric": "execution_time"
    },
    # Token消耗相关
    {
        "id": "task_06",
        "prompt": "审查这段代码: def add(a,b): return a+b",
        "module": "REVIEWING",
        "metric": "token_usage"
    },
    {
        "id": "task_07",
        "prompt": "怎么做微服务架构？最佳实践有哪些？",
        "module": "RESEARCH",
        "metric": "token_usage"
    },
    # 输出质量相关
    {
        "id": "task_08",
        "prompt": "帮我制定一个开发计划",
        "module": "PLANNING",
        "metric": "quality_score"
    },
    {
        "id": "task_09",
        "prompt": "顶级架构师怎么看系统设计？",
        "module": "THINKING",
        "metric": "quality_score"
    },
    # 代码正确性
    {
        "id": "task_10",
        "prompt": "用TDD开发一个栈数据结构",
        "module": "EXECUTING",
        "metric": "code_correctness"
    },
    # 问题覆盖度
    {
        "id": "task_11",
        "prompt": "帮我规划一个聊天APP开发",
        "module": "PLANNING",
        "metric": "issue_coverage"
    },
    # 测试覆盖率
    {
        "id": "task_12",
        "prompt": "用BDD方式开发一个登录功能",
        "module": "EXECUTING",
        "metric": "test_coverage"
    },
    # 文档完整性
    {
        "id": "task_13",
        "prompt": "帮我规划一个博客系统",
        "module": "PLANNING",
        "metric": "documentation"
    },
    # 调试效率
    {
        "id": "task_14",
        "prompt": "修复这个bug: IndexError: list index out of range",
        "module": "DEBUGGING",
        "metric": "debug_efficiency"
    },
    # 规划合理性
    {
        "id": "task_15",
        "prompt": "安排一下项目开发任务",
        "module": "PLANNING",
        "metric": "plan_quality"
    },
    # 专家分析深度
    {
        "id": "task_16",
        "prompt": "哪位专家最懂分布式系统？",
        "module": "THINKING",
        "metric": "expert_depth"
    },
    # 搜索结果质量
    {
        "id": "task_17",
        "prompt": "怎么做API网关？最佳实践有哪些？",
        "module": "RESEARCH",
        "metric": "search_quality"
    },
    # 审查严格度
    {
        "id": "task_18",
        "prompt": "代码审查建议",
        "module": "REVIEWING",
        "metric": "review_strictness"
    },
    # 推理完整性
    {
        "id": "task_19",
        "prompt": "分析这个技术问题",
        "module": "THINKING",
        "metric": "reasoning_completeness"
    },
    # 综合评分
    {
        "id": "task_20",
        "prompt": "帮我开发一个RESTful API",
        "module": "EXECUTING",
        "metric": "overall_score"
    },
]

async def call_claude(prompt: str, system_prompt: str = "") -> Dict:
    """调用 Claude API"""
    try:
        from anthropic import Anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        client = Anthropic(api_key=api_key)

        start_time = time.time()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        duration = time.time() - start_time

        # 处理不同的响应块类型
        content_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                content_text += block.text
            elif hasattr(block, 'type') and block.type == 'text':
                content_text += block.text

        return {
            "success": True,
            "content": content_text,
            "duration": duration,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

async def run_with_skill(task: Dict) -> Dict:
    """使用 skill 执行任务"""
    with open("SKILL.md", "r", encoding="utf-8") as f:
        skill_content = f.read()

    system_prompt = f"""你是一个专业的AI开发助手。遵循以下技能规范：

{skill_content}

请按照技能规范执行任务。"""

    return await call_claude(task["prompt"], system_prompt)

async def run_without_skill(task: Dict) -> Dict:
    """不使用 skill 执行任务"""
    return await call_claude(task["prompt"])

async def run_full_comparison():
    """运行完整对比测试"""
    print("=" * 80)
    print("agentic-workflow 完整质量提升测试 (20个任务)")
    print("=" * 80)
    print()

    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if not api_key:
        print("⚠️  未设置 API key")
        return

    results = []
    success_count = 0

    for i, task in enumerate(TEST_TASKS):
        print(f"[{i+1}/20] {task['id']} - {task['module']} ({task['metric']})")

        # 有 skill
        print("  执行 (有Skill)...", end=" ")
        result_with = await run_with_skill(task)

        if result_with["success"]:
            print(f"✓ {result_with['duration']:.1f}s, {result_with['total_tokens']} tokens")
        else:
            print(f"✗ {result_with.get('error', 'unknown')[:50]}")

        # 无 skill
        print("  执行 (无Skill)...", end=" ")
        result_without = await run_without_skill(task)

        if result_without["success"]:
            print(f"✓ {result_without['duration']:.1f}s, {result_without['total_tokens']} tokens")
        else:
            print(f"✗ {result_without.get('error', 'unknown')[:50]}")

        if result_with["success"] and result_without["success"]:
            success_count += 1

            time_improvement = (result_without["duration"] - result_with["duration"]) / result_without["duration"] * 100
            token_improvement = (result_without["total_tokens"] - result_with["total_tokens"]) / result_without["total_tokens"] * 100

            results.append({
                "task_id": task["id"],
                "module": task["module"],
                "metric": task["metric"],
                "with_skill": {
                    "duration": result_with["duration"],
                    "tokens": result_with["total_tokens"]
                },
                "without_skill": {
                    "duration": result_without["duration"],
                    "tokens": result_without["total_tokens"]
                },
                "time_improvement": time_improvement,
                "token_improvement": token_improvement
            })

            print(f"  → 时间: {time_improvement:+.1f}%, Token: {token_improvement:+.1f}%")

        print()

    # 保存结果
    with open("tests/quality_results_full.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # 统计
    if results:
        avg_time = sum(r["time_improvement"] for r in results) / len(results)
        avg_token = sum(r["token_improvement"] for r in results) / len(results)

        print("=" * 80)
        print(f"完成: {success_count}/20 任务")
        print(f"平均时间提升: {avg_time:+.1f}%")
        print(f"平均Token提升: {avg_token:+.1f}%")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_full_comparison())
