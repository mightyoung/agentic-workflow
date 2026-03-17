#!/usr/bin/env python3
"""
测试验证脚本 - 验证 agentic-workflow skill 路由准确性
测试用例: t09-t16 (8个测试)
"""

import json

# 测试用例
TESTS = [
    {"id": "t09", "prompt": "开发一个RESTful API", "expected": "EXECUTING"},
    {"id": "t10", "prompt": "我的代码运行报错", "expected": "DEBUGGING"},
    {"id": "t11", "prompt": "帮我制定一个开发计划", "expected": "PLANNING"},
    {"id": "t12", "prompt": "谁能告诉我怎么优化这个算法", "expected": "THINKING"},
    {"id": "t13", "prompt": "请检查这段代码的质量", "expected": "REVIEWING"},
    {"id": "t14", "prompt": "微服务架构最佳实践是什么？", "expected": "RESEARCH"},
    {"id": "t15", "prompt": "hello", "expected": None},  # 不触发
    {"id": "t16", "prompt": "你好", "expected": None},  # 不触发
]

# 路由逻辑实现（根据 SKILL.md）
def should_not_trigger(prompt: str) -> bool:
    """检查是否不应该触发"""
    # 简单闲聊问题
    if any(kw in prompt.lower() for kw in ["天气", "笑话", "你好", "hi", "hello", "bye", "谢谢", "ok", "yes", "no", "maybe"]):
        if not any(kw in prompt for kw in ["开发", "代码", "实现", "调试", "bug", "错误"]):
            return True
    return False

def route(prompt: str) -> str:
    """路由到对应模块"""
    if should_not_trigger(prompt):
        return None

    # RESEARCH 触发
    if any(kw in prompt for kw in ["怎么做", "如何实现", "最佳实践", "有什么", "有哪些", "参考", "案例"]):
        return "RESEARCH"

    # THINKING 触发
    if any(kw in prompt for kw in ["谁最懂", "专家", "顶级", "best minds", "优化", "分析"]):
        return "THINKING"

    # PLANNING 触发
    if any(kw in prompt for kw in ["计划", "规划", "拆分任务", "安排", "制定"]):
        return "PLANNING"

    # DEBUGGING 触发
    if any(kw in prompt for kw in ["bug", "错误", "调试", "修复", "报错", "崩溃", "异常", "解决"]):
        return "DEBUGGING"

    # REVIEWING 触发
    if any(kw in prompt for kw in ["审查", "review", "检查"]):
        return "REVIEWING"

    # EXECUTING 默认触发
    return "EXECUTING"

# 执行测试
def run_tests():
    print("=" * 60)
    print("agentic-workflow 路由准确性测试 (t09-t16)")
    print("=" * 60)

    passed = 0
    failed = 0

    for test in TESTS:
        actual = route(test["prompt"])
        expected = test["expected"]

        if actual == expected:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1

        print(f"{test['id']}: {test['prompt'][:30]}")
        print(f"   预期: {expected or '不触发'}")
        print(f"   实际: {actual or '不触发'}")
        print(f"   结果: {status}")
        print()

    print("=" * 60)
    print(f"总计: {len(TESTS)} 个测试")
    print(f"通过: {passed} | 失败: {failed}")
    print(f"通过率: {passed/len(TESTS)*100:.1f}%")
    print("=" * 60)

    return passed, failed

if __name__ == "__main__":
    run_tests()
