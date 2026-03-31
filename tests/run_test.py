#!/usr/bin/env python3
"""
测试验证脚本 - 验证 agentic-workflow skill 路由准确性
测试用例: t09-t16 (8个测试)
"""

from router_helpers import load_router_module

router_module = load_router_module()

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

def route(prompt: str) -> str:
    """路由到对应模块"""
    trigger_type, phase = router_module.route(prompt)
    if trigger_type == "DIRECT_ANSWER":
        return None
    if trigger_type == "FULL_WORKFLOW":
        return "EXECUTING"
    return phase

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
