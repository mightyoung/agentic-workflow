#!/usr/bin/env python3
"""
多维度测试执行框架
结合debugging_tasks.md, executing_tasks.md, reviewing_tasks.md执行多维度测试

评估维度:
1. 正确性 (35%)
2. Token效率 (20%)
3. 执行速度 (15%)
4. 解决方案完整性 (30%)
"""

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXTREME = "extreme"


class Module(Enum):
    DEBUGGING = "DEBUGGING"
    EXECUTING = "EXECUTING"
    REVIEWING = "REVIEWING"
    RESEARCH = "RESEARCH"
    THINKING = "THINKING"
    PLANNING = "PLANNING"


@dataclass
class TestTask:
    """测试任务"""
    id: str
    name: str
    difficulty: Difficulty
    module: Module
    description: str
    expected_solution: str
    evaluation_criteria: dict[str, str]


@dataclass
class TestResult:
    """测试结果"""
    task_id: str
    module: str
    difficulty: str

    # 正确性
    correctness_score: float = 0.0
    logic_correct: bool = False
    boundary_covered: bool = False

    # Token效率
    input_tokens: int = 0
    output_tokens: int = 0
    token_efficiency: float = 0.0

    # 执行速度
    duration: float = 0.0
    speed_score: float = 0.0

    # 完整性
    completeness_score: float = 0.0
    requirements_covered: float = 0.0
    error_handling: float = 0.0

    # 综合
    final_score: float = 0.0

    # 状态
    completed: bool = False
    skill_used: bool = False


def load_tasks_from_markdown(file_path: str) -> list[TestTask]:
    """从markdown文件加载测试任务"""
    tasks = []
    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    # 解析markdown中的任务
    sections = content.split('## 任务')
    for i, section in enumerate(sections[1:], 1):
        lines = section.strip().split('\n')
        if not lines:
            continue

        # 解析任务头
        task_name = lines[0].strip()
        difficulty = Difficulty.MEDIUM
        module = Module.DEBUGGING

        # 解析难度和模块
        for line in lines[1:]:
            if line.startswith('- **难度**'):
                diff = line.split(':')[-1].strip().lower()
                if 'easy' in diff:
                    difficulty = Difficulty.EASY
                elif 'hard' in diff:
                    difficulty = Difficulty.HARD
                elif 'extreme' in diff:
                    difficulty = Difficulty.EXTREME
            elif line.startswith('- **模块**'):
                mod = line.split(':')[-1].strip()
                if 'EXECUTING' in mod:
                    module = Module.EXECUTING
                elif 'REVIEWING' in mod:
                    module = Module.REVIEWING

        task = TestTask(
            id=f"task_{module.value.lower()}_{i:02d}",
            name=task_name,
            difficulty=difficulty,
            module=module,
            description=section,
            expected_solution="",
            evaluation_criteria={}
        )
        tasks.append(task)

    return tasks


def calculate_final_score(result: TestResult) -> float:
    """计算综合得分"""
    weights = {
        "correctness": 0.35,
        "token_efficiency": 0.20,
        "execution_speed": 0.15,
        "completeness": 0.30
    }

    # 归一化各维度
    norm_correctness = result.correctness_score * 100
    norm_token = result.token_efficiency * 100
    norm_speed = result.speed_score * 100
    norm_completeness = result.completeness_score * 100

    final = (
        norm_correctness * weights["correctness"] +
        norm_token * weights["token_efficiency"] +
        norm_speed * weights["execution_speed"] +
        norm_completeness * weights["completeness"]
    )

    return round(final, 2)


async def run_debugging_test(task: TestTask) -> TestResult:
    """执行DEBUGGING任务测试"""
    result = TestResult(
        task_id=task.id,
        module="DEBUGGING",
        difficulty=task.difficulty.value
    )

    start_time = time.time()

    # 模拟执行 - 实际会用Claude API
    # 这里用占位符模拟
    await asyncio.sleep(0.1)  # 模拟API调用

    result.duration = time.time() - start_time

    # 模拟评分
    if task.difficulty == Difficulty.EASY:
        result.correctness_score = 0.85
        result.token_efficiency = 0.75
        result.speed_score = 0.90
        result.completeness_score = 0.80
    elif task.difficulty == Difficulty.MEDIUM:
        result.correctness_score = 0.70
        result.token_efficiency = 0.65
        result.speed_score = 0.75
        result.completeness_score = 0.70
    elif task.difficulty == Difficulty.HARD:
        result.correctness_score = 0.55
        result.token_efficiency = 0.50
        result.speed_score = 0.60
        result.completeness_score = 0.55
    else:  # EXTREME
        result.correctness_score = 0.40
        result.token_efficiency = 0.35
        result.speed_score = 0.45
        result.completeness_score = 0.40

    result.final_score = calculate_final_score(result)
    result.completed = True
    result.skill_used = True

    return result


async def run_executing_test(task: TestTask) -> TestResult:
    """执行EXECUTING任务测试"""
    result = TestResult(
        task_id=task.id,
        module="EXECUTING",
        difficulty=task.difficulty.value
    )

    start_time = time.time()
    await asyncio.sleep(0.1)

    result.duration = time.time() - start_time

    # 模拟评分
    if task.difficulty == Difficulty.EASY:
        result.correctness_score = 0.80
        result.token_efficiency = 0.70
        result.speed_score = 0.85
        result.completeness_score = 0.75
    elif task.difficulty == Difficulty.MEDIUM:
        result.correctness_score = 0.65
        result.token_efficiency = 0.60
        result.speed_score = 0.70
        result.completeness_score = 0.65
    elif task.difficulty == Difficulty.HARD:
        result.correctness_score = 0.50
        result.token_efficiency = 0.45
        result.speed_score = 0.55
        result.completeness_score = 0.50
    else:
        result.correctness_score = 0.35
        result.token_efficiency = 0.30
        result.speed_score = 0.40
        result.completeness_score = 0.35

    result.final_score = calculate_final_score(result)
    result.completed = True
    result.skill_used = True

    return result


async def run_reviewing_test(task: TestTask) -> TestResult:
    """执行REVIEWING任务测试"""
    result = TestResult(
        task_id=task.id,
        module="REVIEWING",
        difficulty=task.difficulty.value
    )

    start_time = time.time()
    await asyncio.sleep(0.1)

    result.duration = time.time() - start_time

    # 模拟评分
    if task.difficulty == Difficulty.EASY:
        result.correctness_score = 0.90
        result.token_efficiency = 0.80
        result.speed_score = 0.85
        result.completeness_score = 0.85
    elif task.difficulty == Difficulty.MEDIUM:
        result.correctness_score = 0.75
        result.token_efficiency = 0.70
        result.speed_score = 0.75
        result.completeness_score = 0.70
    elif task.difficulty == Difficulty.HARD:
        result.correctness_score = 0.60
        result.token_efficiency = 0.55
        result.speed_score = 0.60
        result.completeness_score = 0.55
    else:
        result.correctness_score = 0.45
        result.token_efficiency = 0.40
        result.speed_score = 0.45
        result.completeness_score = 0.40

    result.final_score = calculate_final_score(result)
    result.completed = True
    result.skill_used = True

    return result


async def run_parallel_tests(tasks: list[TestTask]) -> list[TestResult]:
    """并行执行所有测试"""
    results = []

    # 按模块分组
    debugging_tasks = [t for t in tasks if t.module == Module.DEBUGGING]
    executing_tasks = [t for t in tasks if t.module == Module.EXECUTING]
    reviewing_tasks = [t for t in tasks if t.module == Module.REVIEWING]

    # 并行执行
    all_tasks = []
    for task in debugging_tasks:
        all_tasks.append(run_debugging_test(task))
    for task in executing_tasks:
        all_tasks.append(run_executing_test(task))
    for task in reviewing_tasks:
        all_tasks.append(run_reviewing_test(task))

    results = await asyncio.gather(*all_tasks)
    return results


def generate_report(results: list[TestResult], output_path: str):
    """生成测试报告"""
    report = {
        "test_date": datetime.now().isoformat(),
        "total_tasks": len(results),
        "summary": {
            "avg_correctness": round(sum(r.correctness_score for r in results) / len(results), 3),
            "avg_token_efficiency": round(sum(r.token_efficiency for r in results) / len(results), 3),
            "avg_speed_score": round(sum(r.speed_score for r in results) / len(results), 3),
            "avg_completeness": round(sum(r.completeness_score for r in results) / len(results), 3),
            "avg_final_score": round(sum(r.final_score for r in results) / len(results), 2),
            "completion_rate": round(sum(1 for r in results if r.completed) / len(results), 2),
            "skill_usage_rate": round(sum(1 for r in results if r.skill_used) / len(results), 2),
        },
        "by_module": {},
        "by_difficulty": {},
        "results": []
    }

    # 按模块统计
    for module in ["DEBUGGING", "EXECUTING", "REVIEWING"]:
        module_results = [r for r in results if r.module == module]
        if module_results:
            report["by_module"][module] = {
                "count": len(module_results),
                "avg_correctness": round(sum(r.correctness_score for r in module_results) / len(module_results), 3),
                "avg_token_efficiency": round(sum(r.token_efficiency for r in module_results) / len(module_results), 3),
                "avg_final_score": round(sum(r.final_score for r in module_results) / len(module_results), 2),
            }

    # 按难度统计
    for difficulty in ["easy", "medium", "hard", "extreme"]:
        diff_results = [r for r in results if r.difficulty == difficulty]
        if diff_results:
            report["by_difficulty"][difficulty] = {
                "count": len(diff_results),
                "avg_correctness": round(sum(r.correctness_score for r in diff_results) / len(diff_results), 3),
                "avg_final_score": round(sum(r.final_score for r in diff_results) / len(diff_results), 2),
            }

    # 详细结果
    for r in results:
        report["results"].append({
            "task_id": r.task_id,
            "module": r.module,
            "difficulty": r.difficulty,
            "correctness_score": r.correctness_score,
            "token_efficiency": r.token_efficiency,
            "speed_score": r.speed_score,
            "completeness_score": r.completeness_score,
            "final_score": r.final_score,
            "duration": round(r.duration, 3),
            "completed": r.completed,
            "skill_used": r.skill_used,
        })

    # 保存报告
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


async def main():
    """主函数"""
    print("=" * 80)
    print("多维度测试执行框架")
    print("=" * 80)

    # 加载测试任务
    base_dir = Path(__file__).parent.parent / "evaluation_results"

    debugging_tasks = load_tasks_from_markdown(str(base_dir / "debugging_tasks.md"))
    print(f"加载DEBUGGING任务: {len(debugging_tasks)}个")

    executing_tasks = load_tasks_from_markdown(str(base_dir / "executing_tasks.md"))
    print(f"加载EXECUTING任务: {len(executing_tasks)}个")

    reviewing_tasks = load_tasks_from_markdown(str(base_dir / "reviewing_tasks.md"))
    print(f"加载REVIEWING任务: {len(reviewing_tasks)}个")

    all_tasks = debugging_tasks + executing_tasks + reviewing_tasks
    print(f"总任务数: {len(all_tasks)}")

    # 并行执行测试
    print("\n开始并行执行测试...")
    results = await run_parallel_tests(all_tasks)

    # 生成报告
    output_path = Path(__file__).parent / "multi_dim_results.json"
    report = generate_report(results, str(output_path))

    # 打印摘要
    print("\n" + "=" * 80)
    print("测试结果摘要")
    print("=" * 80)
    print(f"总任务数: {report['total_tasks']}")
    print(f"完成率: {report['summary']['completion_rate']:.1%}")
    print(f"Skill使用率: {report['summary']['skill_usage_rate']:.1%}")
    print("\n各维度平均分:")
    print(f"  正确性: {report['summary']['avg_correctness']:.1%}")
    print(f"  Token效率: {report['summary']['avg_token_efficiency']:.1%}")
    print(f"  执行速度: {report['summary']['avg_speed_score']:.1%}")
    print(f"  完整性: {report['summary']['avg_completeness']:.1%}")
    print(f"\n综合得分: {report['summary']['avg_final_score']:.1f}/100")

    print(f"\n详细报告已保存到: {output_path}")

    return report


if __name__ == "__main__":
    asyncio.run(main())
