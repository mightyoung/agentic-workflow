#!/usr/bin/env python3
"""
完整测试验证脚本 - 验证 agentic-workflow skill 路由准确性
测试用例: 全部40个触发测试 (t01-t40)
"""

import json
from pathlib import Path

from router_helpers import load_router_module

router_module = load_router_module()

# 加载测试数据
with open(Path(__file__).resolve().parent / "evals" / "evals_100.json", encoding="utf-8") as f:
    test_data = json.load(f)

TESTS = test_data["trigger_tests"]

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
