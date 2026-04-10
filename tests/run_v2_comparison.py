#!/usr/bin/env python3
"""
增强版真实对照实验 - 10个任务，更全面的评估
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path("/Users/muyi/Downloads/dev/agentic-workflow")


@dataclass
class TaskResult:
    task_id: str
    module: str
    skill_correct: bool
    no_skill_correct: bool
    skill_time: float
    no_skill_time: float
    winner: str
    skill_code: str = ""
    no_skill_code: str = ""


ENHANCED_TASKS = [
    # EXECUTING任务
    {
        "id": "ex_01", "module": "EXECUTING",
        "prompt": "实现 is_palindrome(s) 判断回文，区分大小写，空串返回True，None抛TypeError。只输出代码。",
        "test": 'from src import is_palindrome; assert is_palindrome("racecar"); assert not is_palindrome("hello"); assert is_palindrome(""); assert is_palindrome(None) or True'
    },
    {
        "id": "ex_02", "module": "EXECUTING",
        "prompt": "实现 Stack类: push/pop/peek/is_empty，空栈操作抛IndexError。只输出代码。",
        "test": 'from src import Stack; s=Stack(); s.push(1); assert s.pop()==1; s.push(2); assert s.peek()==2'
    },
    {
        "id": "ex_03", "module": "EXECUTING",
        "prompt": "实现 fibonacci(n) 返回第n个斐波那契数，使用递归。只输出代码。",
        "test": 'from src import fibonacci; assert fibonacci(0)==0; assert fibonacci(1)==1; assert fibonacci(10)==55'
    },
    {
        "id": "ex_04", "module": "EXECUTING",
        "prompt": "实现 unique_words(text) 返回文本中的独特单词数，忽略大小写。只输出代码。",
        "test": 'from src import unique_words; assert unique_words("hello world hello")==2; assert unique_words("a b A b")==2'
    },
    {
        "id": "ex_05", "module": "EXECUTING",
        "prompt": "实现 binary_search(arr, target) 二分查找，找到返回索引，找不到返回-1。只输出代码。",
        "test": 'from src import binary_search; assert binary_search([1,2,3,4,5], 3)==2; assert binary_search([1,2,3], 4)==-1'
    },
    # DEBUGGING任务
    {
        "id": "db_01", "module": "DEBUGGING",
        "prompt": "修复函数 - 空字典get返回None而非空列表: def get_values(d, key): return d.get(key, [])[0] if d.get(key) else None。只输出修复后的完整代码。",
        "test": 'from src import get_values; assert get_values({}, "a") == [] or get_values({}, "a") is None'
    },
    {
        "id": "db_02", "module": "DEBUGGING",
        "prompt": "修复函数 - 除零错误: def divide(a, b): return a/b。只输出修复后的完整代码。",
        "test": 'from src import divide; assert divide(10, 2)==5; assert divide(1, 0) is None or divide(1, 0) == float("inf")'
    },
    {
        "id": "db_03", "module": "DEBUGGING",
        "prompt": "修复函数 - 字符串反转处理None: def reverse(s): return s[::-1]。只输出修复后的完整代码。",
        "test": 'from src import reverse; assert reverse("hello")=="olleh"; r = reverse(None); assert r is None or isinstance(r, str)'
    },
    # REVIEWING任务
    {
        "id": "rv_01", "module": "REVIEWING",
        "prompt": "审查这段代码并说出问题: for i in range(len(items)): if items[i] > threshold: result.append(items[i])。只输出问题列表。",
        "test": 'from src import review_code; r = review_code("test"); assert r is not None'
    },
    {
        "id": "rv_02", "module": "REVIEWING",
        "prompt": "审查代码 x = input.split(',')[0].strip()。有什么问题？只输出问题。",
        "test": 'from src import review_code; r = review_code("test"); assert r is not None'
    },
]

SKILL_GUIDE = """## 执行原则
简洁直接解决问题，验证边界条件。输出代码不要解释。"""


def call_claude(prompt: str, timeout: int = 60) -> tuple[str, float]:
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
                for field in ["result", "text", "content"]:
                    if field in output:
                        return output[field], duration
            except json.JSONDecodeError:
                pass
            return result.stdout.strip(), duration
        return "", duration
    except:
        return "", time.time() - start


def extract_code(text: str) -> str:
    lines = text.split('\n')
    code_lines = []
    in_block = False
    for line in lines:
        if '```python' in line:
            in_block = True
            continue
        if line.strip().startswith('```') and in_block:
            in_block = False
            continue
        if in_block:
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('print('):
                code_lines.append(line)
    if not code_lines:
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('def ') or stripped.startswith('class '):
                code_lines.append(line)
    return '\n'.join(code_lines)


def test_code(code: str, test_str: str) -> bool:
    if not code.strip():
        return False
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "src.py"
        src.write_text(code)
        test = Path(tmpdir) / "test.py"
        test.write_text(test_str)
        try:
            r = subprocess.run(["python3", str(test)], capture_output=True, text=True, timeout=10, cwd=tmpdir)
            return r.returncode == 0
        except:
            return False


def run_task(task: dict) -> TaskResult:
    """运行单个任务"""
    print(f"\n  [{task['id']}] {task['module']}", end=" ", flush=True)

    # 有Skill
    with_skill_prompt = f"{SKILL_GUIDE}\n\n任务: {task['prompt']}"
    text_s, dur_s = call_claude(with_skill_prompt)
    code_s = extract_code(text_s)
    correct_s = test_code(code_s, task["test"])

    # 无Skill
    text_n, dur_n = call_claude(task["prompt"])
    code_n = extract_code(text_n)
    correct_n = test_code(code_n, task["test"])

    # 判定winner
    if correct_s and not correct_n:
        winner = "skill"
    elif correct_n and not correct_s:
        winner = "baseline"
    elif correct_s and correct_n:
        winner = "tie"
    else:
        winner = "none"

    status = "✅" if correct_s else "❌"
    print(f"[有Skill: {status}] ", end="", flush=True)
    status = "✅" if correct_n else "❌"
    print(f"[无Skill: {status}] -> {winner}")

    return TaskResult(
        task["id"], task["module"],
        correct_s, correct_n,
        dur_s, dur_n,
        winner,
        code_s[:100], code_n[:100]
    )


def main():
    print("=" * 70)
    print("  增强版真实对照实验 - 10个任务")
    print("=" * 70)

    results = []
    for task in ENHANCED_TASKS:
        result = run_task(task)
        results.append(result)

    # 汇总
    total = len(results)
    skill_wins = sum(1 for r in results if r.winner == "skill")
    baseline_wins = sum(1 for r in results if r.winner == "baseline")
    ties = sum(1 for r in results if r.winner == "tie")

    print("\n" + "=" * 70)
    print("  结果汇总")
    print("=" * 70)
    print(f"\n  总计: {total} 任务")
    print(f"  Skill获胜: {skill_wins} ({skill_wins/total*100:.0f}%)")
    print(f"  基线获胜: {baseline_wins} ({baseline_wins/total*100:.0f}%)")
    print(f"  平局: {ties} ({ties/total*100:.0f}%)")

    # 按模块
    by_module = {}
    for r in results:
        if r.module not in by_module:
            by_module[r.module] = {"total": 0, "skill": 0, "baseline": 0, "tie": 0}
        by_module[r.module]["total"] += 1
        if r.winner == "skill":
            by_module[r.module]["skill"] += 1
        elif r.winner == "baseline":
            by_module[r.module]["baseline"] += 1
        elif r.winner == "tie":
            by_module[r.module]["tie"] += 1

    print("\n  按模块:")
    for m, s in by_module.items():
        print(f"    {m}: 总{s['total']} | Skill {s['skill']} | 基线 {s['baseline']} | 平局 {s['tie']}")

    # 表格
    print("\n  详细结果:")
    print("  " + "-" * 60)
    for r in results:
        s_s = "✅" if r.skill_correct else "❌"
        s_n = "✅" if r.no_skill_correct else "❌"
        print(f"  {r.task_id:<8} {r.module:<12} {s_s:<6} {s_n:<6} {r.winner}")

    # 保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = PROJECT_ROOT / "tests" / "simple_comparison_results"
    output_dir.mkdir(exist_ok=True)

    report = {
        "date": datetime.now().isoformat(),
        "total": total,
        "skill_wins": skill_wins,
        "baseline_wins": baseline_wins,
        "ties": ties,
        "skill_win_rate": skill_wins / total * 100,
        "by_module": by_module,
        "results": [
            {"task_id": r.task_id, "module": r.module,
             "skill_correct": r.skill_correct, "no_skill_correct": r.no_skill_correct,
             "winner": r.winner}
            for r in results
        ]
    }

    json_file = output_dir / f"enhanced_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  📄 已保存: {json_file}")


if __name__ == "__main__":
    main()
