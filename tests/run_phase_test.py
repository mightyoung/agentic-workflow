#!/usr/bin/env python3
"""
阶段路由测试 - 直接验证真实 router.py 的阶段选择行为

测试用例: p01-p40 (每个模块若干测试)
说明:
- 本文件只验证路由结果
- 不再复写独立的测试版路由逻辑
- phase 的详细行为验证应由独立集成测试覆盖
"""

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ROUTER_PATH = REPO_ROOT / "scripts" / "router.py"


def load_router_module():
    spec = importlib.util.spec_from_file_location("agentic_workflow_router", ROUTER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


router_module = load_router_module()

# 加载测试数据
with open(REPO_ROOT / "tests" / "evals" / "evals_100.json", encoding="utf-8") as f:
    test_data = json.load(f)

PHASE_TESTS = test_data["phase_tests"]

def check_module_behavior(prompt: str, expected_module: str, checks: list) -> dict:
    """
    检查真实 router.py 是否把 prompt 路由到预期阶段
    """
    trigger_type, actual_module = router_module.route(prompt)
    if trigger_type == "DIRECT_ANSWER":
        actual_module = None
    routing_correct = (actual_module == expected_module)

    return {
        "routing_correct": routing_correct,
        "actual_module": actual_module,
        "expected_module": expected_module,
        "checks": checks,
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
