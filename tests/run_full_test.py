#!/usr/bin/env python3
"""
完整测试验证脚本 - 验证 agentic-workflow skill 路由准确性
测试用例: 全部40个触发测试 (t01-t40)
"""

import json

# 加载测试数据
with open("tests/evals/evals_100.json", "r", encoding="utf-8") as f:
    test_data = json.load(f)

TESTS = test_data["trigger_tests"]

# 路由逻辑实现（根据 SKILL.md）
def should_not_trigger(prompt: str) -> bool:
    """检查是否不应该触发 - 使用单词边界匹配"""
    import re
    # 简单闲聊问题 - 使用正则表达式进行单词边界匹配
    simple_keywords = ["天气", "笑话", "你好", "\\bhi\\b", "\\bhello\\b", "\\bbye\\b", "谢谢", "\\bok\\b", "\\byes\\b", "\\bno\\b", "\\bmaybe\\b"]

    # 检查是否包含简单闲聊关键词（作为完整词）
    for kw in simple_keywords:
        if re.search(kw, prompt, re.IGNORECASE):
            # 如果同时包含开发相关词，则应该触发
            if not any(dev_kw in prompt for dev_kw in ["开发", "代码", "实现", "调试", "bug", "错误"]):
                return True
    return False

def route(prompt: str) -> str:
    """路由到对应模块"""
    if should_not_trigger(prompt):
        return None

    # RESEARCH 触发 - 最佳实践相关 (低优先级)
    if any(kw in prompt for kw in ["怎么做", "如何实现", "最佳实践", "有什么", "有哪些", "参考", "案例", "Best Practices", "best practices"]):
        # 如果同时有专家相关词汇，优先THINKING
        if not any(kw in prompt for kw in ["谁最懂", "专家", "顶级", "best minds", "优化", "分析"]):
            return "RESEARCH"

    # THINKING 触发 - 专家/分析 (高优先级)
    if any(kw in prompt for kw in ["谁最懂", "专家", "顶级", "best minds", "优化", "分析", "怎么做"]):
        return "THINKING"

    # PLANNING 触发 - 计划/规划/设计
    if any(kw in prompt for kw in ["计划", "规划", "拆分", "设计", "安排", "制定"]):
        return "PLANNING"

    # DEBUGGING 触发 - 错误/调试
    if any(kw in prompt for kw in ["bug", "错误", "调试", "修复", "报错", "崩溃", "异常", "解决"]):
        return "DEBUGGING"

    # REVIEWING 触发 - 审查/检查
    if any(kw in prompt for kw in ["审查", "review", "检查"]):
        return "REVIEWING"

    # EXECUTING 默认触发 - 开发/实现
    return "EXECUTING"

# 执行测试
def run_tests():
    print("=" * 70)
    print("agentic-workflow 完整路由准确性测试 (t01-t40)")
    print("=" * 70)

    passed = 0
    failed = 0
    results = []

    for test in TESTS:
        actual = route(test["prompt"])
        expected = test["expected"]

        if actual == expected:
            status = "✅"
            passed += 1
        else:
            status = "❌"
            failed += 1
            results.append({
                "id": test["id"],
                "prompt": test["prompt"],
                "expected": expected,
                "actual": actual
            })

        print(f"{test['id']}: {status} {test['prompt'][:35]:35} → {expected or '不触发':12} | {actual or '不触发':12}")

    print("=" * 70)
    print(f"总计: {len(TESTS)} 个测试")
    print(f"通过: {passed} | 失败: {failed}")
    print(f"通过率: {passed/len(TESTS)*100:.1f}%")
    print("=" * 70)

    if failed > 0:
        print("\n失败用例:")
        for r in results:
            print(f"  {r['id']}: '{r['prompt']}'")
            print(f"         预期: {r['expected']}, 实际: {r['actual']}")

    return passed, failed, results

if __name__ == "__main__":
    run_tests()
