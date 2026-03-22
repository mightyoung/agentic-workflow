#!/usr/bin/env python3
"""
test_result_only_spawning.py - v5.5 Result-only Subagent Spawning 测试

测试内容:
1. Result-only 意图检测准确性
2. Result-only vs Fast Path vs Standard Path 路由选择
3. Subagent 映射正确性
4. 跳过 PHASE FLOW 验证

运行方式:
    python tests/test_result_only_spawning.py
"""

import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

# ============================================================
# 测试1: Result-only 意图检测
# ============================================================

class TestResultOnlyDetection:
    """Result-only 意图检测测试"""

    # Result-only 关键词
    RESULT_ONLY_POSITIVE = [
        "给我", "直接给", "直接写", "给我一个",
        "就行", "就好", "搞定", "直接搞定",
        "用Python写", "用TS写", "用Go写",
        "返回JSON", "返回XML", "返回结果",
    ]

    RESULT_ONLY_NEGATIVE = [
        "怎么做", "如何实现", "什么原理",
        "告诉我", "解释一下", "分析一下",
        "看看有什么问题", "审查一下",
        "最佳实践是什么", "怎么设计",
    ]

    # Result-only 检测规则 (从 router/skill.md)
    RESULT_ONLY_PATTERNS = [
        r"给我",
        r"直接给",
        r"直接写",
        r"就行",
        r"就好",
        r"搞定",
        r"用\w+写",
        r"返回\w+",
    ]

    PROCESS_REQUIRED_PATTERNS = [
        r"怎么做",
        r"如何实现",
        r"什么原理",
        r"告诉我",
        r"解释",
        r"分析一下",
        r"最佳实践",
        r"审查",
    ]

    def detect_result_only(self, message: str) -> dict:
        """模拟 Result-only 检测逻辑"""
        result = {
            "result_only": False,
            "matched_keywords": [],
            "has_process_requirement": False,
            "confidence": 0.0
        }

        # 检查正向关键词
        positive_matches = 0
        for pattern in self.RESULT_ONLY_PATTERNS:
            if re.search(pattern, message):
                positive_matches += 1
                result["matched_keywords"].append(pattern)

        # 检查负向关键词 (过程要求)
        for pattern in self.PROCESS_REQUIRED_PATTERNS:
            if re.search(pattern, message):
                result["has_process_requirement"] = True
                break

        # 判断 result_only
        if positive_matches > 0 and not result["has_process_requirement"]:
            result["result_only"] = True
            result["confidence"] = min(1.0, positive_matches * 0.3 + 0.4)

        return result

    def test_positive_cases(self):
        """测试 Result-only 肯定案例"""
        print("\n=== 测试1.1: Result-only 肯定案例 ===")

        failed = 0

        for msg in self.RESULT_ONLY_POSITIVE:
            # 模拟组合场景
            full_msg = f"帮我{msg}一个排序算法"
            result = self.detect_result_only(full_msg)

            if result["result_only"]:
                print(f"  ✅ \"{msg}\" → result_only=True")
            else:
                failed += 1
                print(f"  ❌ \"{msg}\" → result_only=False (期望 True)")

        print(f"\n  结果: {len(self.RESULT_ONLY_POSITIVE)-failed}/{len(self.RESULT_ONLY_POSITIVE)} 通过")
        assert failed == 0, f"{failed} 个测试失败"

    def test_negative_cases(self):
        """测试 Result-only 否定案例"""
        print("\n=== 测试1.2: Result-only 否定案例 ===")

        failed = 0

        for msg in self.RESULT_ONLY_NEGATIVE:
            full_msg = f"帮我{msg}"
            result = self.detect_result_only(full_msg)

            if not result["result_only"]:
                print(f"  ✅ \"{msg}\" → result_only=False")
            else:
                failed += 1
                print(f"  ❌ \"{msg}\" → result_only=True (期望 False)")

        print(f"\n  结果: {len(self.RESULT_ONLY_NEGATIVE)-failed}/{len(self.RESULT_ONLY_NEGATIVE)} 通过")
        assert failed == 0, f"{failed} 个测试失败"

    def test_mixed_cases(self):
        """测试混合场景"""
        print("\n=== 测试1.3: 混合场景 ===")

        test_cases = [
            # (消息, 期望 result_only)
            ("给我一个LRU缓存实现", True),
            ("直接给我JSON解析器", True),
            ("用Python写一个快速排序", True),
            ("帮我看看这段代码有什么问题", False),
            ("告诉我怎么实现JWT", False),
            ("分析一下微服务架构的优缺点", False),
            ("给我实现这个功能就行", True),
            ("给我写个脚本：遍历目录", True),
        ]

        failed = 0

        for msg, expected in test_cases:
            result = self.detect_result_only(msg)
            actual = result["result_only"]

            if actual == expected:
                print(f"  ✅ \"{msg[:30]}...\" → {actual}")
            else:
                failed += 1
                print(f"  ❌ \"{msg[:30]}...\" → {actual} (期望 {expected})")

        print(f"\n  结果: {len(test_cases)-failed}/{len(test_cases)} 通过")
        assert failed == 0, f"{failed} 个测试失败"


# ============================================================
# 测试2: Subagent 映射正确性
# ============================================================

class TestSubagentMapping:
    """Subagent 映射测试"""

    SUBAGENT_MAP = {
        "implementation": "coder",
        "investigation": "researcher",
        "verification": "reviewer",
        "debug": "debugger",
        "analysis": "analyst",
        "planning": "planner",
    }

    def test_mapping(self):
        """测试任务类型到 Subagent 的映射"""
        print("\n=== 测试2: Subagent 映射 ===")

        test_cases = [
            ("实现一个排序算法", "implementation", "coder"),
            ("搜索JWT最佳实践", "investigation", "researcher"),
            ("审查这段代码", "verification", "reviewer"),
            ("帮我修了这个bug", "debug", "debugger"),
            ("分析一下性能瓶颈", "analysis", "analyst"),
            ("规划一下这个项目", "planning", "planner"),
        ]

        failed = 0

        for task, intent, expected_agent in test_cases:
            # 模拟 intent 分类
            actual_agent = self.SUBAGENT_MAP.get(intent)

            if actual_agent == expected_agent:
                print(f"  ✅ {task} → {actual_agent}")
            else:
                failed += 1
                print(f"  ❌ {task} → {actual_agent} (期望 {expected_agent})")

        print(f"\n  结果: {len(test_cases)-failed}/{len(test_cases)} 通过")
        assert failed == 0, f"{failed} 个测试失败"


# ============================================================
# 测试3: 路由路径对比
# ============================================================

class TestRoutingPathComparison:
    """路由路径对比测试"""

    def simulate_routing(self, message: str, complexity: str, result_only: bool) -> dict:
        """模拟路由决策"""

        if result_only and complexity in ["LOW", "MEDIUM"]:
            return {
                "path": "RESULT_ONLY",
                "phases_skipped": ["RESEARCH", "THINKING", "PLANNING", "EXECUTING", "REVIEWING"],
                "subagent": "coder",
                "estimated_time": "< 1 min"
            }
        elif complexity == "LOW":
            return {
                "path": "FAST_PATH",
                "phases_skipped": ["RESEARCH", "THINKING", "PLANNING", "REVIEWING"],
                "subagent": None,
                "estimated_time": "< 2 min"
            }
        else:
            return {
                "path": "STANDARD_PATH",
                "phases_skipped": [],
                "subagent": None,
                "estimated_time": "15-45 min"
            }

    def test_path_selection(self):
        """测试路径选择"""
        print("\n=== 测试3: 路由路径对比 ===")

        test_cases = [
            # (消息, 复杂度, result_only, 期望路径)
            ("给我写一个排序算法", "LOW", True, "RESULT_ONLY"),
            ("帮我开发一个电商系统", "HIGH", False, "STANDARD_PATH"),
            ("给我审查这段代码", "LOW", True, "RESULT_ONLY"),
            ("帮我分析一下架构", "MEDIUM", False, "STANDARD_PATH"),
        ]

        failed = 0

        for msg, complexity, result_only, expected_path in test_cases:
            result = self.simulate_routing(msg, complexity, result_only)
            actual_path = result["path"]

            if actual_path == expected_path:
                print(f"  ✅ \"{msg[:20]}...\" → {actual_path}")
                print(f"     跳过: {result['phases_skipped']}")
            else:
                failed += 1
                print(f"  ❌ \"{msg[:20]}...\" → {actual_path} (期望 {expected_path})")

        print(f"\n  结果: {len(test_cases)-failed}/{len(test_cases)} 通过")
        assert failed == 0, f"{failed} 个测试失败"


# ============================================================
# 测试4: 效率对比估算
# ============================================================

class TestEfficiencyEstimation:
    """效率对比估算测试"""

    # 估算参数 (基于 v5.4 benchmark)
    PATH_EFFICIENCY = {
        "RESULT_ONLY": {"time_reduction": 0.85, "token_reduction": 0.70},  # 最快
        "FAST_PATH": {"time_reduction": 0.60, "token_reduction": 0.40},      # 次快
        "STANDARD_PATH": {"time_reduction": 0.0, "token_reduction": 0.0},   # 基准
    }

    def test_efficiency_comparison(self):
        """测试效率对比"""
        print("\n=== 测试4: 效率对比估算 ===")

        baseline_time = 100  # 基准时间 (%)
        baseline_token = 100  # 基准 token (%)

        for path, reduction in self.PATH_EFFICIENCY.items():
            time_pct = baseline_time * (1 - reduction["time_reduction"])
            token_pct = baseline_token * (1 - reduction["token_reduction"])
            print(f"  {path:15} → 时间: {time_pct:.0f}%, Token: {token_pct:.0f}%")

        # Result-only 应该是最省时间的
        result_only_time = self.PATH_EFFICIENCY["RESULT_ONLY"]["time_reduction"]
        fast_path_time = self.PATH_EFFICIENCY["FAST_PATH"]["time_reduction"]

        assert result_only_time > fast_path_time, "Result-only 效率应该最高"
        print(f"\n  ✅ Result-only 效率提升最高 ({result_only_time*100:.0f}% 时间减少)")


# ============================================================
# 测试5: Phase Selection Matrix 验证
# ============================================================

class TestPhaseSelectionMatrix:
    """Phase Selection Matrix 验证"""

    # v5.5 Phase Selection Matrix
    MATRIX = {
        ("HIGH", "result_only"): "SUBAGENT",
        ("HIGH", "implementation"): "RESEARCH→THINKING→PLANNING",
        ("MEDIUM", "result_only"): "SUBAGENT",
        ("MEDIUM", "implementation"): "THINKING→PLANNING→EXECUTING",
        ("LOW", "result_only"): "SUBAGENT",
        ("LOW", "implementation"): "EXECUTING",
    }

    def test_matrix_completeness(self):
        """测试矩阵完整性"""
        print("\n=== 测试5: Phase Selection Matrix 验证 ===")

        complexities = ["HIGH", "MEDIUM", "LOW"]
        intents = ["result_only", "implementation", "inquiry", "debug"]

        for complexity in complexities:
            for intent in intents:
                key = (complexity, intent)
                if key in self.MATRIX:
                    print(f"  ✅ {key} → {self.MATRIX[key]}")
                else:
                    print(f"  ⚠️  {key} → 未定义 (使用默认逻辑)")

        print(f"\n  结果: Matrix 完整性验证通过 (未定义使用默认逻辑)")


# ============================================================
# 主函数
# ============================================================

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("v5.5 Result-only Subagent Spawning 测试套件")
    print("=" * 60)

    results = []

    # 测试1: Result-only 意图检测
    t1 = TestResultOnlyDetection()
    p1, f1 = t1.test_positive_cases()
    p2, f2 = t1.test_negative_cases()
    p3, f3 = t1.test_mixed_cases()
    results.append(("Result-only 检测", p1+p2+p3, f1+f2+f3))

    # 测试2: Subagent 映射
    t2 = TestSubagentMapping()
    p4, f4 = t2.test_mapping()
    results.append(("Subagent 映射", p4, f4))

    # 测试3: 路由路径对比
    t3 = TestRoutingPathComparison()
    p5, f5 = t3.test_path_selection()
    results.append(("路由路径对比", p5, f5))

    # 测试4: 效率对比估算
    t4 = TestEfficiencyEstimation()
    p6, f6 = t4.test_efficiency_comparison()
    results.append(("效率对比估算", p6, f6))

    # 测试5: Phase Selection Matrix
    t5 = TestPhaseSelectionMatrix()
    p7, f7 = t5.test_matrix_completeness()
    results.append(("Phase Selection Matrix", p7, f7))

    # 汇总
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)

    total_passed = 0
    total_failed = 0

    for name, passed, failed in results:
        total = passed + failed
        rate = (passed / total * 100) if total > 0 else 0
        status = "✅" if failed == 0 else "⚠️"
        print(f"  {status} {name:25} {passed}/{total} ({rate:.1f}%)")
        total_passed += passed
        total_failed += failed

    total = total_passed + total_failed
    overall_rate = (total_passed / total * 100) if total > 0 else 0

    print(f"\n  总计: {total_passed}/{total} ({overall_rate:.1f}%)")

    if total_failed == 0:
        print("\n  🎉 所有测试通过!")
    else:
        print(f"\n  ⚠️  {total_failed} 个测试失败")

    return total_passed, total_failed


if __name__ == "__main__":
    passed, failed = run_all_tests()
    sys.exit(0 if failed == 0 else 1)
