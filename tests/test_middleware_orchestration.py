#!/usr/bin/env python3
"""
Middleware Chain Orchestration Test

测试中间层的完整编排能力:
1. 意图识别 - 根据输入决定触发哪个阶段
2. 复杂度评估 - 根据输入评估任务复杂度
3. 阶段序列生成 - 根据复杂度生成正确的阶段序列
4. Skill上下文切换 - 每个阶段加载对应的skill指南
5. 阶段推进 - advance()方法正确切换阶段

Usage:
    python3 tests/test_middleware_orchestration.py
"""

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

# 添加项目根目录到sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.middleware import (
    Complexity,
    Phase,
    Request,
    SkillMiddleware,
    create_default_chain,
)


@dataclass
class OrchestrationResult:
    """编排测试结果"""
    test_name: str
    passed: bool
    expected: str
    actual: str
    details: str


class MiddlewareOrchestrationTester:
    """中间层编排测试器"""

    def __init__(self):
        self.chain = create_default_chain()
        self.results: list[OrchestrationResult] = []

    def run_test(self, name: str, request: Request, assertions: list) -> bool:
        """运行单个测试"""
        print(f"\n{'='*60}")
        print(f"测试: {name}")
        print(f"{'='*60}")

        # 执行中间件链
        response = self.chain.execute(request)

        print(f"输入: {request.text}")
        print("\n--- 中间层编排结果 ---")
        print(f"意图: {request.intent}")
        print(f"阶段: {request.phase.value}")
        print(f"复杂度: {request.complexity.value}")
        print(f"使用Skill: {request.use_skill}")
        print(f"Skill激活级别: {request.skill_activation_level}")
        print(f"Token预估: {request.tokens_expected}")
        print(f"阶段序列: {[p.value for p in request.metadata.get('phase_sequence', [])]}")

        # 实际值映射
        actual_values = {
            'intent': request.intent,
            'phase': request.phase,
            'complexity': request.complexity,
            'use_skill': request.use_skill,
            'skill_activation_level': request.skill_activation_level,
            'tokens_expected': request.tokens_expected,
            'phase_sequence': request.metadata.get('phase_sequence', []),
        }

        all_passed = True
        for assertion in assertions:
            if len(assertion) == 3:
                attr_name, expected, _ = assertion
            else:
                attr_name, expected = assertion

            actual = actual_values.get(attr_name)

            # 处理特殊比较
            if expected is True:  # 检查是否为真
                passed = bool(actual)
            elif expected is False:  # 检查是否为假
                passed = not actual
            elif isinstance(expected, list) and expected:
                # 检查列表长度
                if isinstance(expected[0], int):
                    passed = actual is not None and hasattr(actual, "__len__") and len(actual) >= expected[0]
                else:
                    passed = actual == expected
            elif isinstance(expected, str) and expected.startswith('contains'):
                passed = expected.split(':')[1] in str(actual)
            else:
                passed = expected == actual

            status = "✅" if passed else "❌"
            print(f"\n{status} {attr_name}: 期望={expected}, 实际={actual}")
            if not passed:
                all_passed = False

        # 测试阶段推进
        print("\n--- 阶段推进测试 ---")
        if request.metadata.get('phase_sequence'):
            phase_seq = request.metadata['phase_sequence']
            if len(phase_seq) > 1:
                next_phase = phase_seq[1]
                request.phase = next_phase

                # 重新执行SkillMiddleware获取新的skill_context
                skill_mw = SkillMiddleware()
                skill_mw.process(request, response)

                print(f"推进到阶段: {next_phase.value}")
                print(f"新Skill Context预览: {request.skill_context[:150]}...")

                # 验证skill_context改变了
                passed = len(request.skill_context) > 0
                status = "✅" if passed else "❌"
                print(f"\n{status} skill_context更新: {passed}")

        result = OrchestrationResult(
            test_name=name,
            passed=all_passed,
            expected=str([a[1] for a in assertions]),
            actual=str([actual_values.get(a[0]) for a in assertions]),
            details=f"意图={request.intent}, 阶段={request.phase.value}, 复杂度={request.complexity.value}"
        )
        self.results.append(result)

        return all_passed

    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "="*70)
        print("Middleware Chain 编排能力测试")
        print("="*70)

        # 测试1: 简单调试任务
        self.run_test(
            "简单调试任务 (DEBUGGING)",
            Request(text="修复这个bug"),
            [
                ("intent", "DEBUGGING"),
                ("complexity", Complexity.S),
                ("use_skill", False),
                ("skill_activation_level", 0),
            ]
        )

        # 测试2: 搜索研究任务
        self.run_test(
            "搜索研究任务 (RESEARCH)",
            Request(text="帮我搜索RESTful API最佳实践"),
            [
                ("intent", "RESEARCH"),
                ("complexity", Complexity.M),
                ("use_skill", False),
                ("skill_activation_level", 0),
            ]
        )

        # 测试3: 思考分析任务
        self.run_test(
            "思考分析任务 (THINKING)",
            Request(text="谁最懂Python异步编程"),
            [
                ("intent", "THINKING"),
                ("complexity", Complexity.M),
                ("use_skill", False),
                ("skill_activation_level", 0),
            ]
        )

        # 测试4: 规划任务
        self.run_test(
            "规划任务 (PLANNING)",
            Request(text="帮我做一个项目计划"),
            [
                ("intent", "PLANNING"),
                ("use_skill", False),
                ("skill_activation_level", 0),
            ]
        )

        # 测试5: 执行任务 (TDD)
        self.run_test(
            "执行任务 (EXECUTING)",
            Request(text="用TDD方式实现一个栈"),
            [
                ("intent", "EXECUTING"),
                ("use_skill", True),
                ("skill_activation_level", 50),
                ("tokens_expected", 1000),
            ]
        )

        # 测试6: FULL_WORKFLOW触发
        self.run_test(
            "完整工作流 (/agentic-workflow)",
            Request(text="/agentic-workflow 开发一个电商系统"),
            [
                ("intent", "FULL_WORKFLOW"),
                ("phase", Phase.RESEARCH),
                ("use_skill", False),
                ("skill_activation_level", 0),
            ]
        )

        # 测试7: 简单执行任务
        self.run_test(
            "简单执行 (XS复杂度)",
            Request(text="写一个回文检测函数"),
            [
                ("intent", "EXECUTING"),
                ("complexity", Complexity.XS),
                ("use_skill", False),
                ("skill_activation_level", 0),
                ("tokens_expected", 1000),
                ("phase_sequence", [2]),  # 检查长度>=2
            ]
        )

        # 测试8: 负面意图检测
        self.run_test(
            "负面意图 (CHAT)",
            Request(text="今天天气怎么样"),
            [
                ("intent", "CHAT"),
                ("phase", Phase.IDLE),
                ("use_skill", False),
                ("skill_activation_level", 0),
            ]
        )

        # 打印总结
        self.print_summary()

    def print_summary(self):
        """打印测试总结"""
        print("\n" + "="*70)
        print("测试结果总结")
        print("="*70)

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)

        print(f"\n通过: {passed}/{total}")

        for r in self.results:
            status = "✅" if r.passed else "❌"
            print(f"{status} {r.test_name}")

        if passed < total:
            print("\n失败测试:")
            for r in self.results:
                if not r.passed:
                    print(f"  ❌ {r.test_name}")
                    print(f"     详情: {r.details}")

        print(f"\n{'='*70}")
        print(f"中间层编排能力测试 {'全部通过!' if passed == total else '有失败项'}")

        return passed == total


def main():
    tester = MiddlewareOrchestrationTester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())


@pytest.mark.parametrize(
    ("text", "intent", "phase", "complexity"),
    [
        ("修复这个bug", "DEBUGGING", Phase.DEBUGGING, Complexity.S),
        ("帮我搜索RESTful API最佳实践", "RESEARCH", Phase.RESEARCH, Complexity.M),
        ("/agentic-workflow 开发一个电商系统", "FULL_WORKFLOW", Phase.RESEARCH, Complexity.XL),
    ],
)
def test_middleware_chain_routes_expected_phase(
    text: str, intent: str, phase: Phase, complexity: Complexity
) -> None:
    chain = create_default_chain()
    request = Request(text=text)

    chain.execute(request)

    assert request.intent == intent
    assert request.phase == phase
    assert request.complexity == complexity
    assert request.metadata.get("phase_sequence")
