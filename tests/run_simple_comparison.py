#!/usr/bin/env python3
"""
简化版真实对照实验

使用Claude Code subprocess进行真实执行，对比:
- 有agentic-workflow skill引导
- 无skill直接执行

验证方式: 直接导入生成的代码并执行，验证正确性
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path("/Users/muyi/Downloads/dev/agentic-workflow")


@dataclass
class SimpleResult:
    task_id: str
    module: str
    skill_used: bool
    duration: float
    code: str
    correct: bool
    error: str = ""


@dataclass
class SimpleComparison:
    task_id: str
    module: str
    skill_correct: bool
    no_skill_correct: bool
    skill_duration: float
    no_skill_duration: float
    winner: str  # "skill", "baseline", "tie"


# ============================================================================
# 简单测试任务
# ============================================================================

SIMPLE_TASKS = [
    {
        "id": "simple_01",
        "module": "EXECUTING",
        "prompt": """实现一个回文检测函数 is_palindrome(s):
- 区分大小写
- 空串和单字符返回True
- None输入抛出TypeError

只输出Python代码，不要解释。""",
        "test_code": """
from src import is_palindrome
assert is_palindrome("racecar") == True
assert is_palindrome("hello") == False
assert is_palindrome("") == True
assert is_palindrome("a") == True
try:
    is_palindrome(None)
    assert False, "Should raise TypeError"
except TypeError:
    pass
print("simple_01 PASSED")
"""
    },
    {
        "id": "simple_02",
        "module": "EXECUTING",
        "prompt": """实现一个Stack类:
- push(item) 入栈
- pop() 出栈，空栈抛出IndexError
- peek() 查看栈顶，空栈抛出IndexError
- is_empty() 判断是否为空

只输出Python代码，不要解释。""",
        "test_code": """
from src import Stack
s = Stack()
s.push(1)
assert s.pop() == 1
s.push(42)
assert s.peek() == 42
assert s.is_empty() == False
try:
    s.pop()
    assert False, "Should raise IndexError"
except IndexError:
    pass
print("simple_02 PASSED")
"""
    },
    {
        "id": "simple_03",
        "module": "EXECUTING",
        "prompt": """实现一个LRUCache类(capacity):
- get(key) 获取值，不存在返回None
- put(key, value) 放入缓存，超容量淘汰最久未使用

只输出Python代码，不要解释。""",
        "test_code": """
from src import LRUCache
cache = LRUCache(2)
cache.put(1, "a")
cache.put(2, "b")
assert cache.get(1) == "a"
cache.put(3, "c")
assert cache.get(1) is None  # evicted
assert cache.get(2) == "b"
print("simple_03 PASSED")
"""
    },
    {
        "id": "simple_04",
        "module": "DEBUGGING",
        "prompt": """修复以下函数的bug - 空列表返回None而不是0:

```python
def sum_list(numbers):
    result = 0
    for n in numbers:
        result = result + n
    return result
```

只输出修复后的完整Python代码，不要解释。""",
        "test_code": """
from src import sum_list
assert sum_list([]) == 0
assert sum_list([1, 2, 3]) == 6
assert sum_list([5]) == 5
print("simple_04 PASSED")
"""
    },
    {
        "id": "simple_05",
        "module": "DEBUGGING",
        "prompt": """修复以下函数 - None输入应该抛出TypeError:

```python
def reverse_string(s):
    return s[::-1]
```

只输出修复后的完整Python代码，不要解释。""",
        "test_code": """
from src import reverse_string
assert reverse_string("hello") == "olleh"
assert reverse_string("") == ""
try:
    reverse_string(None)
    assert False, "Should raise TypeError"
except TypeError:
    pass
print("simple_05 PASSED")
"""
    },
]


# ============================================================================
# 核心函数
# ============================================================================

def call_claude(prompt: str, timeout: int = 60) -> tuple[str, float, str]:
    """调用Claude Code"""
    start = time.time()
    try:
        result = subprocess.run(
            ["claude", "-p", "--print", "--output-format", "json", prompt],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(PROJECT_ROOT)
        )
        duration = time.time() - start

        if result.returncode == 0:
            try:
                output = json.loads(result.stdout.strip())
                # 尝试多种字段
                for field in ["result", "text", "content", "message"]:
                    if field in output:
                        return output[field], duration, ""
            except json.JSONDecodeError:
                pass
            return result.stdout.strip(), duration, ""
        else:
            return "", duration, result.stderr
    except subprocess.TimeoutExpired:
        return "", time.time() - start, "Timeout"
    except Exception as e:
        return "", time.time() - start, str(e)


def extract_code(text: str) -> str:
    """提取Python代码"""
    lines = text.split('\n')
    code_lines = []
    in_block = False

    for line in lines:
        if line.strip().startswith('```python'):
            in_block = True
            continue
        if line.strip().startswith('```') and in_block:
            in_block = False
            continue
        if in_block:
            # 跳过print和注释
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or stripped.startswith('print('):
                continue
            code_lines.append(line)

    # 如果没有代码块，提取def/class行
    if not code_lines:
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('def ') or stripped.startswith('class '):
                code_lines.append(line)

    return '\n'.join(code_lines)


def run_code(code: str, test_code: str) -> tuple[bool, str]:
    """在临时目录中运行代码测试"""
    if not code or not code.strip():
        return False, "Empty code"

    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / "src.py"
        src_path.write_text(code)

        test_path = Path(tmpdir) / "test.py"
        test_path.write_text(test_code)

        try:
            result = subprocess.run(
                ["python3", test_path],
                capture_output=True, text=True, timeout=15,
                cwd=tmpdir
            )
            output = result.stdout + result.stderr
            passed = result.returncode == 0 and "PASSED" in output
            return passed, output[:500]
        except Exception as e:
            return False, str(e)


# ============================================================================
# Skill上下文
# ============================================================================

SKILL_GUIDE = """## 执行原则
- 代码简洁，直接解决问题
- 先理解需求，再实现
- 验证边界条件
- 不要过度工程

## 输出要求
- 只输出Python代码
- 不需要解释
- 代码必须可直接运行"""


# ============================================================================
# 执行函数
# ============================================================================

def run_with_skill(task: dict) -> SimpleResult:
    """使用Skill执行"""
    print(f"    [有Skill] 执行中...")
    prompt = f"""{SKILL_GUIDE}

## 任务
{task['prompt']}
"""
    text, duration, error = call_claude(prompt)
    if error:
        return SimpleResult(task["id"], task["module"], True, duration, "", False, error)

    code = extract_code(text)
    correct, output = run_code(code, task["test_code"])

    return SimpleResult(
        task["id"], task["module"], True, duration, code[:200], correct, output[:200] if not correct else ""
    )


def run_without_skill(task: dict) -> SimpleResult:
    """不使用Skill执行"""
    print(f"    [无Skill] 执行中...")
    text, duration, error = call_claude(task["prompt"])
    if error:
        return SimpleResult(task["id"], task["module"], False, duration, "", False, error)

    code = extract_code(text)
    correct, output = run_code(code, task["test_code"])

    return SimpleResult(
        task["id"], task["module"], False, duration, code[:200], correct, output[:200] if not correct else ""
    )


def run_comparison(task: dict) -> Optional[SimpleComparison]:
    """运行单个对比"""
    print(f"\n  [{task['id']}] {task['module']}")

    with_skill = run_with_skill(task)
    no_skill = run_without_skill(task)

    if with_skill.correct and not no_skill.correct:
        winner = "skill"
    elif no_skill.correct and not with_skill.correct:
        winner = "baseline"
    elif with_skill.correct and no_skill.correct:
        winner = "tie"
    else:
        winner = "none"

    print(f"      有Skill: {with_skill.duration:.1f}s, 正确: {with_skill.correct}")
    print(f"      无Skill: {no_skill.duration:.1f}s, 正确: {no_skill.correct}")
    print(f"      获胜: {winner}")

    return SimpleComparison(
        task["id"], task["module"],
        with_skill.correct, no_skill.correct,
        with_skill.duration, no_skill.duration,
        winner
    )


# ============================================================================
# 主函数
# ============================================================================

def main():
    print("=" * 70)
    print("  简化版真实对照实验 - 验证代码执行正确性")
    print("=" * 70)
    print(f"\n任务数量: {len(SIMPLE_TASKS)}\n")

    results = []
    for task in SIMPLE_TASKS:
        result = run_comparison(task)
        if result:
            results.append(result)

    # 统计
    total = len(results)
    skill_wins = sum(1 for r in results if r.winner == "skill")
    baseline_wins = sum(1 for r in results if r.winner == "baseline")
    ties = sum(1 for r in results if r.winner == "tie")

    print("\n" + "=" * 70)
    print("  实验结果汇总")
    print("=" * 70)
    print(f"\n  总计: {total} 个任务")
    print(f"  Skill获胜: {skill_wins} ({skill_wins/total*100:.0f}%)")
    print(f"  基线获胜: {baseline_wins} ({baseline_wins/total*100:.0f}%)")
    print(f"  平局: {ties} ({ties/total*100:.0f}%)")

    # 按模块统计
    by_module = {}
    for r in results:
        if r.module not in by_module:
            by_module[r.module] = {"total": 0, "skill": 0, "baseline": 0}
        by_module[r.module]["total"] += 1
        if r.winner == "skill":
            by_module[r.module]["skill"] += 1
        elif r.winner == "baseline":
            by_module[r.module]["baseline"] += 1

    print("\n  按模块:")
    for module, stats in by_module.items():
        print(f"    {module}: Skill {stats['skill']}/{stats['total']}, 基线 {stats['baseline']}/{stats['total']}")

    # 详细结果表
    print("\n  详细结果:")
    print("  " + "-" * 66)
    print(f"  {'任务ID':<12} {'模块':<12} {'有Skill':<10} {'无Skill':<10} {'获胜者'}")
    print("  " + "-" * 66)
    for r in results:
        with_str = "✅" if r.skill_correct else "❌"
        no_str = "✅" if r.no_skill_correct else "❌"
        print(f"  {r.task_id:<12} {r.module:<12} {with_str:<10} {no_str:<10} {r.winner}")

    # 保存报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = PROJECT_ROOT / "tests" / "simple_comparison_results"
    output_dir.mkdir(exist_ok=True)

    report = {
        "date": datetime.now().isoformat(),
        "total": total,
        "skill_wins": skill_wins,
        "baseline_wins": baseline_wins,
        "ties": ties,
        "skill_win_rate": skill_wins / total * 100 if total > 0 else 0,
        "by_module": by_module,
        "results": [
            {
                "task_id": r.task_id,
                "module": r.module,
                "skill_correct": r.skill_correct,
                "no_skill_correct": r.no_skill_correct,
                "winner": r.winner
            }
            for r in results
        ]
    }

    json_file = output_dir / f"simple_comparison_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n  📄 报告已保存: {json_file}")

    return report


if __name__ == "__main__":
    main()
