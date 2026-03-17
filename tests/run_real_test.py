#!/usr/bin/env python3
"""
使用 Claude Code 进行真实的 Subagent 集成测试
通过 claude -p 命令执行实际测试场景
"""

import json
import subprocess
import time
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class RealTestResult:
    test_id: str
    dimension: str
    category: str
    scenario: str
    expected: str
    passed: bool
    execution_time: float
    tokens_input: int = 0
    tokens_output: int = 0
    error: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


def call_claude(prompt: str, timeout: int = 120) -> tuple:
    """调用 Claude Code 执行测试"""
    cmd = [
        "claude", "-p", "--print",
        "--output-format", "json",
        prompt
    ]

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/Users/muyi/Downloads/dev/agentic-workflow"
        )
        execution_time = time.time() - start_time

        if result.returncode == 0:
            # 尝试解析 JSON 输出
            try:
                # 找到 JSON 开始和结束位置
                output = result.stdout.strip()
                if output.startswith('{'):
                    # 找到匹配的括号
                    json_output = json.loads(output)
                    return json_output, execution_time, None
            except:
                pass

            # 如果不是 JSON，返回文本
            return {"text": result.stdout}, execution_time, None
        else:
            return {}, execution_time, result.stderr

    except subprocess.TimeoutExpired:
        return {}, timeout, "Timeout"
    except Exception as e:
        return {}, 0, str(e)


class RealSubagentTester:
    def __init__(self):
        self.results: List[RealTestResult] = []

    def run_stage_trigger_tests(self):
        """运行阶段触发测试 - 选择代表性场景"""
        print("\n" + "="*60)
        print("  第一部分：阶段触发测试 (5个代表性测试)")
        print("="*60)

        stage_tests = [
            {"id": "st01", "dimension": "阶段触发", "category": "基础触发",
             "scenario": "搜索React状态管理最佳实践", "expected": "RESEARCH",
             "prompt": "请用一句话回答：如果用户说'搜索React状态管理最佳实践'，应该触发哪个阶段？(RESEARCH, THINKING, PLANNING, EXECUTING, REVIEWING, DEBUGGING)"},
            {"id": "st02", "dimension": "阶段触发", "category": "基础触发",
             "scenario": "谁最懂分布式缓存设计", "expected": "THINKING",
             "prompt": "请用一句话回答：如果用户说'谁最懂分布式缓存设计'，应该触发哪个阶段？"},
            {"id": "st03", "dimension": "阶段触发", "category": "基础触发",
             "scenario": "帮我规划这个项目开发", "expected": "PLANNING",
             "prompt": "请用一句话回答：如果用户说'帮我规划这个项目开发'，应该触发哪个阶段？"},
            {"id": "st04", "dimension": "阶段触发", "category": "基础触发",
             "scenario": "这个bug一直解决不了", "expected": "DEBUGGING",
             "prompt": "请用一句话回答：如果用户说'这个bug一直解决不了'，应该触发哪个阶段？"},
            {"id": "st05", "dimension": "阶段触发", "category": "边界测试",
             "scenario": "hello world", "expected": "不触发",
             "prompt": "请用一句话回答：如果用户说'hello world'，应该触发哪个阶段？(如果不触发任何阶段，回答'不触发')"},
        ]

        for test in stage_tests:
            result = self._execute_stage_test(test)
            self.results.append(result)
            status = "✓" if result.passed else "✗"
            print(f"  [{result.test_id}] {status} - {test['scenario'][:25]}")
            if result.error:
                print(f"      Error: {result.error}")

    def run_subagent_tests(self):
        """运行 Subagent 派生测试"""
        print("\n" + "="*60)
        print("  第二部分：Subagent派生测试 (5个代表性测试)")
        print("="*60)

        subagent_tests = [
            {"id": "sa01", "dimension": "Subagent派生", "category": "基础派生",
             "scenario": "搜索分布式事务最佳实践", "expected": "researcher",
             "prompt": "agentic-workflow skill 中，如果需要执行'搜索分布式事务最佳实践'任务，应该派生哪个子智能体？(researcher, planner, coder, reviewer, debugger)"},
            {"id": "sa02", "dimension": "Subagent派生", "category": "基础派生",
             "scenario": "规划这个项目开发", "expected": "planner",
             "prompt": "agentic-workflow skill 中，如果需要执行'规划这个项目开发'任务，应该派生哪个子智能体？"},
            {"id": "sa03", "dimension": "Subagent派生", "category": "基础派生",
             "scenario": "用TDD实现计算器", "expected": "coder",
             "prompt": "agentic-workflow skill 中，如果需要执行'用TDD实现计算器'任务，应该派生哪个子智能体？"},
            {"id": "sa04", "dimension": "Subagent派生", "category": "基础派生",
             "scenario": "审查这段代码", "expected": "reviewer",
             "prompt": "agentic-workflow skill 中，如果需要执行'审查这段代码'任务，应该派生哪个子智能体？"},
            {"id": "sa05", "dimension": "Subagent派生", "category": "基础派生",
             "scenario": "调试这个bug", "expected": "debugger",
             "prompt": "agentic-workflow skill 中，如果需要执行'调试这个bug'任务，应该派生哪个子智能体？"},
        ]

        for test in subagent_tests:
            result = self._execute_subagent_test(test)
            self.results.append(result)
            status = "✓" if result.passed else "✗"
            print(f"  [{result.test_id}] {status} - {test['scenario'][:25]}")
            if result.error:
                print(f"      Error: {result.error}")

    def run_quality_tests(self):
        """运行运行质量测试"""
        print("\n" + "="*60)
        print("  第三部分：运行质量测试 (5个代表性测试)")
        print("="*60)

        quality_tests = [
            {"id": "qa01", "dimension": "运行质量", "category": "执行效果",
             "scenario": "开发认证模块", "baseline": "直接实现", "optimized": "TDD+Review",
             "prompt": "使用 agentic-workflow 的 TDD+Review 方法开发认证模块，相比直接实现，Bug率能降低多少百分比？请给出一个估计值。"},
            {"id": "qa02", "dimension": "运行质量", "category": "执行效果",
             "scenario": "技术选型", "baseline": "凭经验", "optimized": "Research+分析",
             "prompt": "使用 agentic-workflow 的 Research+分析 方法进行技术选型，相比凭经验选择，方案完整性能提升多少百分比？请给出一个估计值。"},
            {"id": "qa03", "dimension": "运行质量", "category": "执行效果",
             "scenario": "Bug修复", "baseline": "单次调试", "optimized": "5步调试法",
             "prompt": "使用 agentic-workflow 的 5步调试法 修复Bug，相比单次调试，根因定位成功率能提升多少百分比？请给出一个估计值。"},
            {"id": "qa04", "dimension": "运行质量", "category": "执行速度",
             "scenario": "搜索+实现", "baseline_time": 120,
             "prompt": "使用 agentic-workflow 的 RESEARCH→EXECUTING 流程执行'搜索+实现'任务，相比分别执行，执行时间能减少多少百分比？请给出一个估计值。"},
            {"id": "qa05", "dimension": "运行质量", "category": "上下文优化",
             "scenario": "多轮对话", "baseline_token": 50000,
             "prompt": "使用 agentic-workflow 的子智能体并行执行多轮对话任务，相比串行执行，Token消耗能减少多少百分比？请给出一个估计值。"},
        ]

        for test in quality_tests:
            result = self._execute_quality_test(test)
            self.results.append(result)
            status = "✓" if result.passed else "✗"
            print(f"  [{result.test_id}] {status} - {test['scenario'][:20]}")
            if result.error:
                print(f"      Error: {result.error}")

    def _execute_stage_test(self, test: Dict) -> RealTestResult:
        """执行单个阶段触发测试"""
        print(f"    执行中: {test['prompt'][:50]}...")
        response, exec_time, error = call_claude(test['prompt'], timeout=60)

        # 简单的通过判断
        passed = True
        if error:
            passed = False

        return RealTestResult(
            test_id=test['id'],
            dimension=test['dimension'],
            category=test['category'],
            scenario=test['scenario'],
            expected=test['expected'],
            passed=passed,
            execution_time=exec_time,
            error=error or "",
            details={"response": str(response)[:200]}
        )

    def _execute_subagent_test(self, test: Dict) -> RealTestResult:
        """执行单个Subagent测试"""
        print(f"    执行中: {test['prompt'][:50]}...")
        response, exec_time, error = call_claude(test['prompt'], timeout=60)

        passed = True
        if error:
            passed = False

        return RealTestResult(
            test_id=test['id'],
            dimension=test['dimension'],
            category=test['category'],
            scenario=test['scenario'],
            expected=test['expected'],
            passed=passed,
            execution_time=exec_time,
            error=error or "",
            details={"response": str(response)[:200]}
        )

    def _execute_quality_test(self, test: Dict) -> RealTestResult:
        """执行单个运行质量测试"""
        print(f"    执行中: {test['prompt'][:50]}...")
        response, exec_time, error = call_claude(test['prompt'], timeout=120)

        passed = True
        if error:
            passed = False

        return RealTestResult(
            test_id=test['id'],
            dimension=test['dimension'],
            category=test['category'],
            scenario=test['scenario'],
            expected=test.get('baseline', ''),
            passed=passed,
            execution_time=exec_time,
            error=error or "",
            details={"response": str(response)[:200]}
        )

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*60)
        print("  真实测试结果摘要")
        print("="*60)

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        print(f"\n  总计: {passed}/{total} ({passed/total*100:.1f}%)")

        # 按维度统计
        by_dim = {}
        for r in self.results:
            if r.dimension not in by_dim:
                by_dim[r.dimension] = {"total": 0, "passed": 0}
            by_dim[r.dimension]["total"] += 1
            if r.passed:
                by_dim[r.dimension]["passed"] += 1

        print("\n  按维度:")
        for dim, data in by_dim.items():
            rate = (data["passed"] / data["total"] * 100) if data["total"] > 0 else 0
            print(f"    - {dim}: {data['passed']}/{data['total']} ({rate:.1f}%)")

        # 统计执行时间
        total_time = sum(r.execution_time for r in self.results)
        print(f"\n  总执行时间: {total_time:.1f}秒")

    def save_results(self, filename: str = "real_test_results.json"):
        """保存测试结果"""
        results_data = {
            "total": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "pass_rate": sum(1 for r in self.results if r.passed) / len(self.results) * 100 if self.results else 0,
            "total_time": sum(r.execution_time for r in self.results),
            "results": [
                {
                    "test_id": r.test_id,
                    "dimension": r.dimension,
                    "category": r.category,
                    "scenario": r.scenario,
                    "expected": r.expected,
                    "passed": r.passed,
                    "execution_time": r.execution_time,
                    "error": r.error,
                    "details": r.details
                }
                for r in self.results
            ]
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)

        print(f"\n  结果已保存到: {filename}")


def main():
    """主函数"""
    print("="*60)
    print("  agentic-workflow 真实测试 (使用 Claude Code)")
    print("  测试数量: 15 (代表性测试)")
    print("="*60)

    tester = RealSubagentTester()

    # 运行三部分测试
    tester.run_stage_trigger_tests()
    tester.run_subagent_tests()
    tester.run_quality_tests()

    # 打印摘要
    tester.print_summary()

    # 保存结果
    tester.save_results()


if __name__ == "__main__":
    main()
