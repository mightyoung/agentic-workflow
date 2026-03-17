#!/usr/bin/env python3
"""
阶段路由测试 - 验证每个模块的特定行为是否正确触发
测试用例: p01-p40 (每个模块8个测试)

注：此测试验证路由正确性 + 预期行为关键词
实际执行需要 Claude API 调用
"""

import json
import re

# 加载测试数据
with open("tests/evals/evals_100.json", "r", encoding="utf-8") as f:
    test_data = json.load(f)

PHASE_TESTS = test_data["phase_tests"]

# 模块行为规范 (根据 SKILL.md)
MODULE_BEHAVIORS = {
    "RESEARCH": {
        "keywords": ["搜索", "Tavily", "findings", "最佳实践", "案例", "调研"],
        "file_check": "findings.md",
        "description": "搜索最佳实践，输出到 findings.md"
    },
    "THINKING": {
        "keywords": ["专家", "链式推理", "问题定义", "要素拆解", "推理", "分析"],
        "description": "专家模拟 + 链式推理"
    },
    "PLANNING": {
        "keywords": ["task_plan", "任务拆分", "阶段", "计划", "里程碑"],
        "file_check": "task_plan.md",
        "description": "创建 task_plan.md，拆分任务"
    },
    "EXECUTING": {
        "keywords": ["测试", "TDD", "实现", "开发", "代码"],
        "description": "TDD 循环: 测试先行 → 失败 → 实现 → 通过"
    },
    "REVIEWING": {
        "keywords": ["审查", "问题分级", "致命", "严重", "建议", "review"],
        "description": "问题分级: 🔴致命 🟡严重 🟢建议"
    },
    "DEBUGGING": {
        "keywords": ["调试", "bug", "错误", "根因", "闻味道", "揪头发", "照镜子"],
        "description": "5步调试法 + 7项检查"
    }
}

# 路由逻辑
def route(prompt: str) -> str:
    """路由到对应模块"""
    import re

    # 不触发检查
    simple_keywords = ["天气", "笑话", "你好", "\\bhi\\b", "\\bhello\\b", "\\bbye\\b", "谢谢", "\\bok\\b", "\\byes\\b", "\\bno\\b", "\\bmaybe\\b"]
    for kw in simple_keywords:
        if re.search(kw, prompt, re.IGNORECASE):
            if not any(dev_kw in prompt for dev_kw in ["开发", "代码", "实现", "调试", "bug", "错误"]):
                return None

    # RESEARCH 触发 - 最佳实践相关 (最高优先级)
    if any(kw in prompt for kw in ["最佳实践", "有什么", "有哪些", "选型", "部署", "方法"]):
        return "RESEARCH"

    if any(kw in prompt for kw in ["怎么做", "如何实现", "参考", "案例", "Best Practices", "best practices"]):
        # 如果同时有专家相关词汇，优先THINKING
        if not any(kw in prompt for kw in ["谁最懂", "专家", "顶级", "best minds", "分析", "怎么做", "理解"]):
            return "RESEARCH"

    # THINKING 触发 - 专家/分析
    if any(kw in prompt for kw in ["谁最懂", "专家", "顶级", "best minds", "分析", "怎么做", "理解"]):
        return "THINKING"

    # PLANNING 触发 - 计划/规划/设计
    if any(kw in prompt for kw in ["计划", "规划", "拆分", "设计", "安排", "制定"]):
        return "PLANNING"

    # DEBUGGING 触发 - 错误/调试
    if any(kw in prompt for kw in ["bug", "错误", "调试", "修复", "报错", "崩溃", "异常", "定位", "Error"]):
        return "DEBUGGING"

    # REVIEWING 触发 - 审查/检查
    if any(kw in prompt for kw in ["审查", "review", "检查"]):
        return "REVIEWING"

    # EXECUTING 默认触发 - 开发/实现
    return "EXECUTING"

def check_module_behavior(prompt: str, expected_module: str, checks: list) -> dict:
    """
    检查模块行为是否符合预期
    返回: {routing_correct: bool, behavior_keywords_found: list, missing_keywords: list}
    """
    actual_module = route(prompt)
    routing_correct = (actual_module == expected_module)

    # 查找预期行为关键词
    behavior = MODULE_BEHAVIORS.get(expected_module, {})
    expected_keywords = behavior.get("keywords", [])

    found_keywords = []
    missing_keywords = []

    for check in checks:
        # 检查每个关键词
        for kw in expected_keywords:
            if kw.lower() in check.lower():
                found_keywords.append(kw)
                break
        else:
            # 如果checks中的关键词都不匹配预期关键词，记录缺失
            if check not in found_keywords:
                missing_keywords.append(check)

    return {
        "routing_correct": routing_correct,
        "actual_module": actual_module,
        "expected_module": expected_module,
        "checks": checks,
        "found_keywords": found_keywords,
        "missing_keywords": missing_keywords,
        "routing_pass": routing_correct
    }

def run_phase_tests():
    print("=" * 80)
    print("agentic-workflow 阶段路由测试 (p01-p40)")
    print("=" * 80)

    results = []
    passed = 0
    failed = 0

    # 按模块统计
    module_stats = {
        "RESEARCH": {"total": 0, "passed": 0},
        "THINKING": {"total": 0, "passed": 0},
        "PLANNING": {"total": 0, "passed": 0},
        "EXECUTING": {"total": 0, "passed": 0},
        "REVIEWING": {"total": 0, "passed": 0},
        "DEBUGGING": {"total": 0, "passed": 0}
    }

    for test in PHASE_TESTS:
        module = test["module"]
        checks = test["checks"]

        result = check_module_behavior(test["prompt"], module, checks)

        module_stats[module]["total"] += 1

        if result["routing_pass"]:
            status = "✅"
            passed += 1
            module_stats[module]["passed"] += 1
        else:
            status = "❌"
            failed += 1

        print(f"{test['id']}: {status} {test['prompt'][:40]:40} → {module:12} | 实际: {result['actual_module']}")

        results.append({
            "id": test["id"],
            "prompt": test["prompt"],
            "expected": module,
            "actual": result["actual_module"],
            "passed": result["routing_pass"]
        })

    print("=" * 80)
    print("\n按模块统计:")
    print("-" * 50)
    for module, stats in module_stats.items():
        rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"  {module:12}: {stats['passed']}/{stats['total']} ({rate:.0f}%)")

    print("-" * 50)
    print(f"总计: {len(PHASE_TESTS)} 个测试")
    print(f"通过: {passed} | 失败: {failed}")
    print(f"通过率: {passed/len(PHASE_TESTS)*100:.1f}%")
    print("=" * 80)

    return passed, failed, results

if __name__ == "__main__":
    run_phase_tests()
