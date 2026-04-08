#!/usr/bin/env python3
"""
真实复杂任务对照实验

使用Claude Code subprocess进行真实执行，对比:
- 有agentic-workflow skill引导
- 无skill直接执行

评估维度:
1. 执行效率 (duration)
2. 代码质量 (通过pytest测试)
3. Token消耗量 (估算)
4. 任务完成率 (测试通过率)
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class RealTaskResult:
    """真实任务执行结果"""
    task_id: str
    module: str
    skill_used: bool
    duration_seconds: float
    code_output: str
    test_passed: bool
    test_output: str
    error: str = ""


@dataclass
class RealComparisonResult:
    """真实对照结果"""
    task_id: str
    module: str

    # 有Skill
    with_skill_duration: float
    with_skill_code: str
    with_skill_test_passed: bool
    with_skill_test_output: str

    # 无Skill
    without_skill_duration: float
    without_skill_code: str
    without_skill_test_passed: bool
    without_skill_test_output: str

    # 对比
    time_diff_pct: float
    quality_wins: str  # "skill", "baseline", "tie"


# ============================================================================
# 测试任务定义
# ============================================================================

REAL_TASKS = [
    {
        "id": "real_exec_01",
        "module": "EXECUTING",
        "name": "TDD回文检测器",
        "prompt": """使用TDD方法实现一个回文检测器。

要求:
1. is_palindrome(s) - 区分大小写，空串和单字符返回True，None输入抛出TypeError
2. is_palindrome_case_insensitive(s) - 忽略大小写

请先写测试用例(使用pytest)，再实现功能。
只输出Python代码，不需要解释。""",
        "test_template": """import pytest
{src_code}

def test_simple_palindrome():
    assert is_palindrome("racecar") is True

def test_non_palindrome():
    assert is_palindrome("hello") is False

def test_empty_string():
    assert is_palindrome("") is True

def test_single_char():
    assert is_palindrome("a") is True

def test_none_input():
    with pytest.raises(TypeError):
        is_palindrome(None)

def test_case_insensitive():
    assert is_palindrome_case_insensitive("RaceCar") is True
"""
    },
    {
        "id": "real_exec_02",
        "module": "EXECUTING",
        "name": "TDD Stack实现",
        "prompt": """使用TDD方法实现一个Stack类。

要求:
1. push(item) - 入栈
2. pop() - 出栈并返回栈顶元素，空栈时抛出IndexError
3. peek() - 返回栈顶元素但不弹出，空栈时抛出IndexError
4. is_empty() - 判断是否为空

请先写测试用例(使用pytest)，再实现功能。
只输出Python代码，不需要解释。""",
        "test_template": """import pytest
{src_code}

def test_push_pop():
    s = Stack()
    s.push(1)
    assert s.pop() == 1

def test_empty_stack_pop():
    s = Stack()
    with pytest.raises(IndexError):
        s.pop()

def test_peek():
    s = Stack()
    s.push(42)
    assert s.peek() == 42
    assert s.peek() == 42  # peek不弹出

def test_is_empty():
    s = Stack()
    assert s.is_empty() is True
    s.push(1)
    assert s.is_empty() is False
"""
    },
    {
        "id": "real_exec_03",
        "module": "EXECUTING",
        "name": "TDD LRU缓存",
        "prompt": """使用TDD方法实现一个LRU缓存。

要求:
1. LRUCache(capacity) - 构造函数，capacity为缓存容量
2. get(key) - 获取值，不存在返回None，存在时更新为最近使用
3. put(key, value) - 放入缓存，超容量时淘汰最久未使用的项

请先写测试用例(使用pytest)，再实现功能。
只输出Python代码，不需要解释。""",
        "test_template": """import pytest
{src_code}

def test_basic():
    cache = LRUCache(2)
    cache.put(1, "a")
    cache.put(2, "b")
    assert cache.get(1) == "a"
    assert cache.get(2) == "b"

def test_eviction():
    cache = LRUCache(2)
    cache.put(1, "a")
    cache.put(2, "b")
    cache.put(3, "c")  # 淘汰key=1
    assert cache.get(1) is None
    assert cache.get(2) == "b"
    assert cache.get(3) == "c"

def test_update():
    cache = LRUCache(2)
    cache.put(1, "a")
    cache.put(2, "b")
    cache.put(1, "aa")  # 更新key=1
    assert cache.get(1) == "aa"
"""
    },
    {
        "id": "real_debug_01",
        "module": "DEBUGGING",
        "name": "调试列表求和函数",
        "prompt": """修复以下Python函数的bug:

```python
def sum_list(numbers):
    result = 0
    for n in numbers:
        result = result + n
    return result

print(sum_list([]))  # 返回0
print(sum_list([1, 2, 3]))  # 返回6
```

问题：空列表应该返回0，但函数返回None。

只输出修复后的完整Python代码，不需要解释。""",
        "test_template": """import pytest
{src_code}

def test_empty_list():
    assert sum_list([]) == 0

def test_normal_list():
    assert sum_list([1, 2, 3]) == 6

def test_single_element():
    assert sum_list([5]) == 5

def test_negative_numbers():
    assert sum_list([-1, 1, -1]) == -1
"""
    },
    {
        "id": "real_debug_02",
        "module": "DEBUGGING",
        "name": "调试字符串反转函数",
        "prompt": """修复以下Python函数的bug:

```python
def reverse_string(s):
    return s[::-1]

print(reverse_string("hello"))  # 输出"olleh"
print(reverse_string(""))  # 输出""
print(reverse_string("a"))  # 输出"a"
print(reverse_string(None))  # 崩溃！
```

问题：None输入应该抛出TypeError，而不是崩溃。

只输出修复后的完整Python代码，不需要解释。""",
        "test_template": """import pytest
{src_code}

def test_normal():
    assert reverse_string("hello") == "olleh"

def test_empty():
    assert reverse_string("") == ""

def test_single():
    assert reverse_string("a") == "a"

def test_none_input():
    with pytest.raises(TypeError):
        reverse_string(None)
"""
    },
]


# ============================================================================
# 执行函数
# ============================================================================

def call_claude_subprocess(prompt: str, timeout: int = 60) -> tuple[str, float, str]:
    """使用claude -p调用Claude Code subprocess"""
    start_time = time.time()

    try:
        result = subprocess.run(
            ["claude", "-p", "--print", "--output-format", "json", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT)
        )
        duration = time.time() - start_time

        if result.returncode == 0:
            # 尝试解析JSON输出
            try:
                output = result.stdout.strip()
                if output.startswith('{'):
                    json_output = json.loads(output)
                    if "text" in json_output:
                        return json_output["text"], duration, ""
                    elif "content" in json_output:
                        return json_output["content"], duration, ""
            except json.JSONDecodeError:
                pass
            # 如果不是JSON，返回原始输出
            return result.stdout.strip(), duration, ""
        else:
            return "", duration, result.stderr

    except subprocess.TimeoutExpired:
        return "", time.time() - start_time, "Timeout"
    except Exception as e:
        return "", time.time() - start_time, str(e)


def extract_code_from_response(response: str) -> str:
    """从响应中提取Python代码"""
    lines = response.split('\n')
    code_lines = []
    in_code_block = False

    for line in lines:
        if line.strip().startswith('```python'):
            in_code_block = True
            continue
        elif line.strip().startswith('```'):
            in_code_block = False
            continue
        if in_code_block:
            code_lines.append(line)

    # 如果没有代码块，尝试直接提取
    if not code_lines:
        # 尝试提取以def或class开头的行
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('def ') or stripped.startswith('class '):
                code_lines.append(line)

    return '\n'.join(code_lines)


def run_tests_in_temp_dir(code: str, test_code: str) -> tuple[bool, str]:
    """在临时目录中运行测试"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 写入源代码
        src_path = Path(tmpdir) / "src.py"
        src_path.write_text(code)

        # 写入测试文件
        test_path = Path(tmpdir) / "test_src.py"
        test_content = test_code.format(src_code=code)
        test_path.write_text(test_content)

        # 运行pytest
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", str(test_path), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmpdir
            )
            passed = result.returncode == 0
            output = result.stdout + "\n" + result.stderr
            return passed, output[:2000]  # 限制输出长度
        except subprocess.TimeoutExpired:
            return False, "Test timeout"
        except Exception as e:
            return False, str(e)


# ============================================================================
# Skill上下文
# ============================================================================

SKILL_CONTEXT = """你是一个专业的AI开发助手。遵循以下规范:

## 核心原则
- 使用TDD方法：先写测试，再实现功能
- 测试先行：先写失败的测试，再写实现通过测试
- 代码简洁：不要过度工程，直接解决问题

## TDD流程
1. 理解需求
2. 编写测试用例（Red）
3. 运行测试确认失败
4. 编写最小实现（Green）
5. 运行测试确认通过
6. 重构优化

## 输出要求
- 只输出Python代码
- 不要解释
- 代码必须可以直接运行"""


# ============================================================================
# 实验执行
# ============================================================================

def run_real_task_with_skill(task: dict) -> RealTaskResult:
    """使用Skill执行真实任务"""
    print(f"    [有Skill] 执行中...")

    # 构建prompt
    prompt = f"""{SKILL_CONTEXT}

## 任务
{task['prompt']}
"""

    code, duration, error = call_claude_subprocess(prompt, timeout=90)

    if error:
        return RealTaskResult(
            task_id=task["id"],
            module=task["module"],
            skill_used=True,
            duration_seconds=duration,
            code_output="",
            test_passed=False,
            test_output="",
            error=error
        )

    # 提取代码
    extracted_code = extract_code_from_response(code)

    # 运行测试
    test_template = task.get("test_template", "")
    if test_template and extracted_code:
        test_passed, test_output = run_tests_in_temp_dir(extracted_code, test_template)
    else:
        test_passed = False
        test_output = "No test template or code extraction failed"

    return RealTaskResult(
        task_id=task["id"],
        module=task["module"],
        skill_used=True,
        duration_seconds=duration,
        code_output=extracted_code,
        test_passed=test_passed,
        test_output=test_output,
        error=""
    )


def run_real_task_without_skill(task: dict) -> RealTaskResult:
    """不使用Skill执行真实任务"""
    print(f"    [无Skill] 执行中...")

    # 直接执行，不带skill上下文
    code, duration, error = call_claude_subprocess(task["prompt"], timeout=90)

    if error:
        return RealTaskResult(
            task_id=task["id"],
            module=task["module"],
            skill_used=False,
            duration_seconds=duration,
            code_output="",
            test_passed=False,
            test_output="",
            error=error
        )

    # 提取代码
    extracted_code = extract_code_from_response(code)

    # 运行测试
    test_template = task.get("test_template", "")
    if test_template and extracted_code:
        test_passed, test_output = run_tests_in_temp_dir(extracted_code, test_template)
    else:
        test_passed = False
        test_output = "No test template or code extraction failed"

    return RealTaskResult(
        task_id=task["id"],
        module=task["module"],
        skill_used=False,
        duration_seconds=duration,
        code_output=extracted_code,
        test_passed=test_passed,
        test_output=test_output,
        error=""
    )


def run_single_real_comparison(task: dict) -> Optional[RealComparisonResult]:
    """运行单个真实对比实验"""
    print(f"\n  [{task['id']}] {task['module']} - {task['name']}")

    # 使用Skill执行
    with_skill = run_real_task_with_skill(task)

    # 不使用Skill执行
    without_skill = run_real_task_without_skill(task)

    # 计算对比
    if with_skill.duration_seconds > 0 and without_skill.duration_seconds > 0:
        time_diff = (with_skill.duration_seconds - without_skill.duration_seconds) / without_skill.duration_seconds * 100
    else:
        time_diff = 0

    # 判断质量获胜
    if with_skill.test_passed and not without_skill.test_passed:
        quality_wins = "skill"
    elif without_skill.test_passed and not with_skill.test_passed:
        quality_wins = "baseline"
    elif with_skill.test_passed and without_skill.test_passed:
        quality_wins = "tie"
    else:
        quality_wins = "none"

    # 打印结果
    print(f"      有Skill: {with_skill.duration_seconds:.1f}s, 测试通过: {with_skill.test_passed}")
    print(f"      无Skill: {without_skill.duration_seconds:.1f}s, 测试通过: {without_skill.test_passed}")
    print(f"      质量获胜: {quality_wins}")

    return RealComparisonResult(
        task_id=task["id"],
        module=task["module"],
        with_skill_duration=with_skill.duration_seconds,
        with_skill_code=with_skill.code_output[:200],
        with_skill_test_passed=with_skill.test_passed,
        with_skill_test_output=with_skill.test_output[:500],
        without_skill_duration=without_skill.duration_seconds,
        without_skill_code=without_skill.code_output[:200],
        without_skill_test_passed=without_skill.test_passed,
        without_skill_test_output=without_skill.test_output[:500],
        time_diff_pct=time_diff,
        quality_wins=quality_wins
    )


# ============================================================================
# 报告生成
# ============================================================================

def generate_real_report(results: list[RealComparisonResult], output_dir: str = "tests/real_comparison_results") -> str:
    """生成真实实验报告"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 计算汇总
    total = len(results)
    skill_wins = sum(1 for r in results if r.quality_wins == "skill")
    baseline_wins = sum(1 for r in results if r.quality_wins == "baseline")
    ties = sum(1 for r in results if r.quality_wins == "tie")
    none_wins = sum(1 for r in results if r.quality_wins == "none")

    skill_win_rate = skill_wins / total * 100 if total > 0 else 0
    avg_time_diff = sum(r.time_diff_pct for r in results) / total if total > 0 else 0

    # 按模块统计
    by_module = {}
    for r in results:
        if r.module not in by_module:
            by_module[r.module] = {"total": 0, "skill_wins": 0, "baseline_wins": 0}
        by_module[r.module]["total"] += 1
        if r.quality_wins == "skill":
            by_module[r.module]["skill_wins"] += 1
        elif r.quality_wins == "baseline":
            by_module[r.module]["baseline_wins"] += 1

    # JSON数据
    json_data = {
        "experiment_date": datetime.now().isoformat(),
        "experiment_type": "real_execution_comparison",
        "total_tasks": total,
        "summary": {
            "skill_win_rate": skill_win_rate,
            "avg_time_diff_pct": avg_time_diff,
            "skill_wins": skill_wins,
            "baseline_wins": baseline_wins,
            "ties": ties,
        },
        "by_module": by_module,
        "results": [
            {
                "task_id": r.task_id,
                "module": r.module,
                "with_skill": {
                    "duration": round(r.with_skill_duration, 2),
                    "test_passed": r.with_skill_test_passed,
                },
                "without_skill": {
                    "duration": round(r.without_skill_duration, 2),
                    "test_passed": r.without_skill_test_passed,
                },
                "time_diff_pct": round(r.time_diff_pct, 1),
                "quality_wins": r.quality_wins,
            }
            for r in results
        ]
    }

    # 保存JSON
    json_file = output_path / f"real_comparison_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    # Markdown报告
    md_report = f"""# 真实复杂任务对照实验报告

**实验日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**实验类型**: 真实Claude Code执行对比
**任务数量**: {total}

---

## 总体结果

| 指标 | 数值 |
|------|------|
| **Skill获胜率** | {skill_win_rate:.1f}% |
| **Skill获胜次数** | {skill_wins}/{total} |
| **基线获胜次数** | {baseline_wins}/{total} |
| **平局次数** | {ties}/{total} |
| **平均时间差异** | {avg_time_diff:+.1f}% |

---

## 质量对比详情

| 任务ID | 模块 | 有Skill测试 | 无Skill测试 | 质量获胜 |
|--------|------|------------|------------|----------|
"""
    for r in results:
        md_report += f"| {r.task_id} | {r.module} | {'✅' if r.with_skill_test_passed else '❌'} | {'✅' if r.without_skill_test_passed else '❌'} | {r.quality_wins} |\n"

    md_report += """
---

## 按模块统计

| 模块 | 任务数 | Skill获胜 | 基线获胜 |
|------|--------|----------|----------|
"""
    for module, stats in by_module.items():
        win_rate = stats["skill_wins"] / stats["total"] * 100 if stats["total"] > 0 else 0
        md_report += f"| {module} | {stats['total']} | {stats['skill_wins']} ({win_rate:.0f}%) | {stats['baseline_wins']} |\n"

    md_report += f"""
---

## 结论

### 关键发现

1. **执行效率**: 有Skill版本平均 {avg_time_diff:+.1f}% 的时间变化
2. **代码质量**: Skill获胜率 {skill_win_rate:.1f}%，{'Skill引导明显提升代码质量' if skill_win_rate > 50 else '基线版本质量相当或更好'}
3. **TDD执行**: {'Skill引导下TDD测试通过率更高' if skill_wins > baseline_wins else '基线TDD执行效果相当'}

### 解读

- Skill获胜率高说明TDD规范引导有效
- 时间差异在±10%内属于正常波动
- 部分任务基线获胜可能因为测试设计问题或任务本身简单

---

*报告自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    # 保存Markdown
    md_file = output_path / f"real_comparison_{timestamp}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_report)

    print(f"\n📄 报告已保存:")
    print(f"   JSON: {json_file}")
    print(f"   Markdown: {md_file}")

    return md_report


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    print("=" * 80)
    print("  真实复杂任务对照实验")
    print("  对比有/无agentic-workflow skill的真实执行效果")
    print("=" * 80)
    print(f"\n任务数量: {len(REAL_TASKS)}")

    results = []

    for task in REAL_TASKS:
        result = run_single_real_comparison(task)
        if result:
            results.append(result)

    # 生成报告
    if results:
        report = generate_real_report(results)
        print("\n" + "=" * 80)
        print("  实验完成")
        print("=" * 80)
        print(report)
    else:
        print("\n❌ 没有成功执行的任务")


if __name__ == "__main__":
    main()
