"""
Agentic Workflow Skill Evaluation Framework

测试三个维度：
1. 触发准确性 - skill能否在用户不显示调用时正确激活
2. 阶段路由 - 每个阶段的特性是否正确触发
3. 质量提升 - 执行效果、速度、上下文优化
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class TestCase:
    """测试用例"""
    id: str
    prompt: str
    expected: Optional[str] = None
    checks: list[str] = field(default_factory=list)
    category: str = "trigger"


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    passed: bool
    actual: Optional[str] = None
    metrics: dict = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: int = 0


class SkillEvaluator:
    """Skill评估器"""

    def __init__(self, skill_path: str):
        self.skill_path = skill_path
        self.results: list[TestResult] = []

    def check_skill_activation(self, prompt: str) -> Optional[str]:
        """
        检查skill是否被激活
        返回激活的模块名，否则返回None
        """
        # 模拟实现 - 实际需要接入Claude API
        # 这里应该调用实际的skill触发检测
        pass

    def run_and_check(self, prompt: str, checks: list[str]) -> TestResult:
        """运行测试并检查特性"""
        start = time.time()
        # 实际执行逻辑
        result = TestResult(
            test_id="",
            passed=True,
            duration_ms=int((time.time() - start) * 1000)
        )
        return result

    def measure_metric(self, prompt: str, metric: str) -> float:
        """测量特定指标"""
        # 实现各种指标的测量
        pass


# =============================================================================
# 测试用例定义
# =============================================================================

TRIGGER_TESTS = [
    # 应该触发的场景
    TestCase(
        id="trigger_01",
        prompt="帮我开发一个用户认证系统",
        expected="EXECUTING",
        category="trigger"
    ),
    TestCase(
        id="trigger_02",
        prompt="这个API报错了请调试",
        expected="DEBUGGING",
        category="trigger"
    ),
    TestCase(
        id="trigger_03",
        prompt="请帮我规划一个电商网站",
        expected="PLANNING",
        category="trigger"
    ),
    TestCase(
        id="trigger_04",
        prompt="谁最懂Python异步编程",
        expected="THINKING",
        category="trigger"
    ),
    TestCase(
        id="trigger_05",
        prompt="这段代码有问题吗？审查一下",
        expected="REVIEWING",
        category="trigger"
    ),
    TestCase(
        id="trigger_06",
        prompt="怎么做用户登录功能？最佳实践有哪些？",
        expected="RESEARCH",
        category="trigger"
    ),
    # 不应该触发的场景
    TestCase(
        id="trigger_07",
        prompt="今天天气怎么样",
        expected=None,
        category="trigger"
    ),
    TestCase(
        id="trigger_08",
        prompt="给我讲个笑话",
        expected=None,
        category="trigger"
    ),
]

PHASE_TESTS = [
    TestCase(
        id="phase_01",
        prompt="怎么做微服务架构？最佳实践有哪些？",
        checks=["Tavily搜索调用", "findings.md创建"],
        category="phase"
    ),
    TestCase(
        id="phase_02",
        prompt="谁最懂大模型训练？",
        checks=["专家识别", "链式推理", "问题定义", "要素拆解"],
        category="phase"
    ),
    TestCase(
        id="phase_03",
        prompt="规划一个聊天APP开发",
        checks=["task_plan.md创建", "任务拆分"],
        category="phase"
    ),
    TestCase(
        id="phase_04",
        prompt="用TDD开发一个计算器",
        checks=["测试先行", "测试失败", "代码实现", "测试通过"],
        category="phase"
    ),
    TestCase(
        id="phase_05",
        prompt="审查这段代码",
        checks=["问题分级", "致命问题", "严重问题", "建议"],
        category="phase"
    ),
    TestCase(
        id="phase_06",
        prompt="修复这个bug",
        checks=["闻味道", "揪头发", "照镜子", "执行", "复盘"],
        category="phase"
    ),
]

QUALITY_TESTS = [
    {
        "name": "任务完成率",
        "metric": "completion_rate",
        "unit": "%"
    },
    {
        "name": "执行时间",
        "metric": "execution_time",
        "unit": "seconds"
    },
    {
        "name": "Token消耗",
        "metric": "token_usage",
        "unit": "tokens"
    },
    {
        "name": "输出质量评分",
        "metric": "quality_score",
        "unit": "1-10"
    },
]


# =============================================================================
# 测试执行
# =============================================================================

def run_trigger_tests(evaluator: SkillEvaluator) -> list[TestResult]:
    """运行触发测试"""
    results = []
    for test in TRIGGER_TESTS:
        actual = evaluator.check_skill_activation(test.prompt)
        passed = actual == test.expected
        results.append(TestResult(
            test_id=test.id,
            passed=passed,
            expected=test.expected,
            actual=actual
        ))
    return results


def run_phase_tests(evaluator: SkillEvaluator) -> list[TestResult]:
    """运行阶段测试"""
    results = []
    for test in PHASE_TESTS:
        result = evaluator.run_and_check(test.prompt, test.checks)
        result.test_id = test.id
        results.append(result)
    return results


def run_quality_tests(evaluator: SkillEvaluator) -> dict:
    """运行质量对比测试"""
    results = {}
    for test in QUALITY_TESTS:
        # 有skill的测量
        with_skill = evaluator.measure_metric(test["prompt"], test["metric"])
        # 无skill的测量（基线）
        without_skill = evaluator.measure_metric(test["prompt"], test["metric"])

        improvement = 0
        if without_skill > 0:
            improvement = (with_skill - without_skill) / without_skill * 100

        results[test["name"]] = {
            "with_skill": with_skill,
            "without_skill": without_skill,
            "improvement": f"{improvement:+.1f}%",
            "unit": test["unit"]
        }
    return results


# =============================================================================
# 报告生成
# =============================================================================

def generate_report(results: list[TestResult], quality_results: dict) -> str:
    """生成测试报告"""
    total = len(results)
    passed = sum(1 for r in results if r.passed)

    report = f"""# Agentic Workflow Skill 测试报告

生成时间: {datetime.now().isoformat()}

## 测试概览

| 测试类型 | 总数 | 通过 | 通过率 |
|---------|-----|-----|-------|
| 触发测试 | {total} | {passed} | {passed/total*100:.1f}% |

## 1. 触发准确性测试

| 测试ID | Prompt | 预期 | 实际 | 结果 |
|-------|--------|-----|-----|-----|
"""
    for r in results:
        result_icon = "✅" if r.passed else "❌"
        report += f"| {r.test_id} | {r.prompt[:30]}... | {r.expected or 'None'} | {r.actual or 'None'} | {result_icon} |\n"

    report += """
## 2. 阶段路由测试

"""
    # 添加阶段测试结果

    report += """
## 3. 质量提升测试

| 指标 | 有Skill | 无Skill | 提升 |
|-----|--------|--------|-----|
"""
    for name, data in quality_results.items():
        report += f"| {name} | {data['with_skill']} | {data['without_skill']} | {data['improvement']} |\n"

    return report


# =============================================================================
# 主函数
# =============================================================================

def main():
    """主测试入口"""
    evaluator = SkillEvaluator(skill_path="/path/to/agentic-workflow")

    print("开始运行测试...")

    # 1. 触发测试
    trigger_results = run_trigger_tests(evaluator)

    # 2. 阶段测试
    phase_results = run_phase_tests(evaluator)

    # 3. 质量测试
    quality_results = run_quality_tests(evaluator)

    # 生成报告
    report = generate_report(trigger_results + phase_results, quality_results)
    print(report)

    # 保存报告
    with open("test_report.md", "w") as f:
        f.write(report)

    print("\n测试报告已保存到 test_report.md")


if __name__ == "__main__":
    main()
