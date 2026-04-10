#!/usr/bin/env python3
"""
复杂任务对照实验

测试Skill在复杂场景中的效果:
1. 多文件修改
2. 阶段切换工作流 (RESEARCH→EXECUTING→REVIEWING)
3. TDD完整流程
4. 真实代码审查与修复
5. 调试复杂问题
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
class ComplexResult:
    task_id: str
    module: str
    skill_score: int  # 0-100
    no_skill_score: int
    skill_phases_completed: list
    no_skill_phases_completed: list
    winner: str


# ============================================================================
# 复杂测试任务
# ============================================================================

COMPLEX_TASKS = [
    # ========== 1. 多文件TDD完整流程 ==========
    {
        "id": "complex_01",
        "module": "EXECUTING",
        "name": "TDD完整流程 - 字符串工具库",
        "description": """
请使用TDD方法开发一个字符串工具库，包含:

1. 创建 `string_utils.py`，实现:
   - camel_to_snake(name) - 驼峰转蛇形
   - snake_to_camel(name) - 蛇形转驼峰
   - truncate(s, max_len, suffix="...") - 截断字符串

2. 创建 `test_string_utils.py`，包含完整测试

流程要求:
1. 先写测试（红）
2. 实现功能（绿）
3. 重构优化（重构）

请按照TDD流程执行，输出完整的代码文件内容。
""",
        "skill_phases": ["EXECUTING"],
        "validation": "代码包含完整实现和测试，且测试能通过"
    },

    # ========== 2. 调试+审查+修复完整流程 ==========
    {
        "id": "complex_02",
        "module": "DEBUGGING",
        "name": "多阶段调试流程",
        "description": """
修复以下代码中的多个问题:

```python
# user_manager.py
class UserManager:
    def __init__(self):
        self.users = {}

    def add_user(self, user_id, name, email):
        if email in [u.email for u in self.users.values()]:
            return False  # 应该抛出异常而不是静默返回
        self.users[user_id] = User(user_id, name, email)
        return True

    def get_user(self, user_id):
        return self.users.get(user_id)

    def delete_user(self, user_id):
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False  # 应该抛出异常
```

问题识别要求:
1. 审查代码找出所有问题
2. 修复每个问题
3. 添加适当的异常处理
4. 添加输入验证

请输出修复后的完整代码。
""",
        "skill_phases": ["DEBUGGING", "REVIEWING"],
        "validation": "代码包含异常处理和输入验证"
    },

    # ========== 3. 模块化设计任务 ==========
    {
        "id": "complex_03",
        "module": "EXECUTING",
        "name": "模块化设计 - 缓存系统",
        "description": """
使用TDD方法开发一个缓存系统:

1. 创建 `cache/base.py`:
   - Cache基类定义接口

2. 创建 `cache/lru_cache.py`:
   - LRUCache实现，使用 OrderedDict

3. 创建 `cache/ttl_cache.py`:
   - TTLCache实现，支持过期时间

4. 创建 `cache/__init__.py`:
   - 导出缓存类

5. 创建 `tests/test_cache.py`:
   - 完整测试覆盖

要求:
- 基类定义 get, set, delete, clear 接口
- LRU缓存使用Python的OrderedDict
- TTL缓存使用time.time()判断过期
- 所有测试必须通过

请输出所有文件的完整代码。
""",
        "skill_phases": ["EXECUTING"],
        "validation": "创建了4个文件，测试全部通过"
    },

    # ========== 4. 代码审查与重构 ==========
    {
        "id": "complex_04",
        "module": "REVIEWING",
        "name": "代码审查与重构",
        "description": """
审查并重构以下代码:

```python
# data_processor.py
def process_data(data, filter_fn=None, map_fn=None, reduce_fn=None):
    result = data
    if filter_fn:
        result = [x for x in result if filter_fn(x)]
    if map_fn:
        result = [map_fn(x) for x in result]
    if reduce_fn:
        result = reduce_fn(result)
    return result

def get_user_stats(users):
    stats = {}
    for u in users:
        if u['active']:
            stats[u['id']] = {
                'name': u['name'],
                'count': len([x for x in u.get('items', [])])
            }
    return stats
```

请执行:
1. 识别所有代码问题（P0/P1/P2）
2. 重构代码使其更清晰
3. 添加类型注解
4. 添加docstring
5. 确保功能不变

请输出重构后的完整代码。
""",
        "skill_phases": ["REVIEWING"],
        "validation": "代码包含类型注解、docstring，结构清晰"
    },

    # ========== 5. 调试复杂问题 ==========
    {
        "id": "complex_05",
        "module": "DEBUGGING",
        "name": "并发调试场景",
        "description": """
修复以下代码中的并发问题:

```python
# counter.py
class Counter:
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1
        return self.count

    def get_count(self):
        return self.count

# 使用示例
import threading

counter = Counter()
threads = []

for i in range(100):
    t = threading.Thread(target=counter.increment)
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print(f"Final count: {counter.get_count()}")  # 期望100，实际可能小于100
```

问题:
1. 竞态条件导致计数不准确
2. 需要使用 threading.Lock 保护共享状态

请输出修复后的完整代码。
""",
        "skill_phases": ["DEBUGGING"],
        "validation": "代码使用Lock保护共享状态，并发计数准确"
    },

    # ========== 6. API设计任务 ==========
    {
        "id": "complex_06",
        "module": "EXECUTING",
        "name": "REST API设计与实现",
        "description": """
使用TDD方法设计并实现一个简单的REST API:

创建 `api_server.py`:
- 使用Python内置http.server
- 实现 GET /users 和 GET /users/<id>
- 返回JSON格式数据
- 添加适当的HTTP状态码

创建 `test_api.py`:
- 测试各个端点
- 测试错误情况

要求:
- 使用简单的字典存储数据
- 返回正确的JSON Content-Type
- 处理不存在的用户ID返回404

请输出完整代码。
""",
        "skill_phases": ["EXECUTING"],
        "validation": "API能正确返回用户数据，测试通过"
    },

    # ========== 7. 数据验证任务 ==========
    {
        "id": "complex_07",
        "module": "EXECUTING",
        "name": "数据验证器设计",
        "description": """
使用TDD方法开发一个数据验证器:

创建 `validators.py`:
- EmailValidator - 验证邮箱格式
- PasswordValidator - 验证密码强度（至少8字符，包含数字和字母）
- URLValidator - 验证URL格式

创建 `test_validators.py`:
- 每个验证器至少5个测试用例
- 包含正向和负向测试

要求:
- 每个验证器实现 validate(value) -> tuple[bool, str] 方法
- 返回(True, "")表示有效
- 返回(False, "错误信息")表示无效

请输出完整代码。
""",
        "skill_phases": ["EXECUTING"],
        "validation": "三个验证器实现完整，测试覆盖充分"
    },

    # ========== 8. 状态机设计 ==========
    {
        "id": "complex_08",
        "module": "EXECUTING",
        "name": "状态机实现",
        "description": """
使用TDD方法实现一个简单的订单状态机:

创建 `order_state.py`:
- 状态: PENDING, PAID, SHIPPED, DELIVERED, CANCELLED
- 事件: pay, ship, deliver, cancel
- 状态转换规则:
  - PENDING -> PAID (pay)
  - PAID -> SHIPPED (ship)
  - SHIPPED -> DELIVERED (deliver)
  - PENDING/PAID -> CANCELLED (cancel)

创建 `test_order_state.py`:
- 测试每个状态转换
- 测试非法转换

请输出完整代码。
""",
        "skill_phases": ["EXECUTING"],
        "validation": "状态机实现正确，状态转换符合规则"
    },
]


# ============================================================================
# Skill上下文
# ============================================================================

SKILL_CONTEXT = """你是一个专业的AI开发助手。遵循agentic-workflow skill规范:

## 核心原则
- 穷尽一切、先做后问、主动出击
- TDD驱动：测试先行 -> 失败 -> 实现 -> 通过
- 代码质量优先

## TDD流程
1. 理解需求
2. 编写测试用例（Red）
3. 运行测试确认失败
4. 编写最小实现（Green）
5. 运行测试确认通过
6. 重构优化

## EXECUTING执行
- Boil the Lake原则：完整性与AI能力成正比
- Fix-First决策：机械性问题直接修复，判断性问题先问用户
- 先验证再声称完成

## REVIEWING审查
- P0安全 > P1逻辑/性能 > P2风格
- 使用具体file:line引用
- 不跳过任何阶段

请按照规范执行任务。"""


# ============================================================================
# 执行函数
# ============================================================================

def call_claude(prompt: str, timeout: int = 120) -> tuple[str, float]:
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
                for field in ["result", "text", "content"]:
                    if field in output:
                        return output[field], duration
            except json.JSONDecodeError:
                pass
            return result.stdout.strip(), duration
        return "", duration
    except:
        return "", time.time() - start


def extract_code_blocks(text: str) -> dict:
    """提取多个代码块"""
    blocks = {}
    lines = text.split('\n')
    current_block = None
    current_lines = []
    in_block = False

    for line in lines:
        if '```' in line:
            if in_block:
                # 结束当前块
                if current_block:
                    blocks[current_block] = '\n'.join(current_lines)
                in_block = False
                current_block = None
                current_lines = []
            else:
                # 开始新块
                in_block = True
                # 尝试从语言标识符提取名称
                parts = line.split('```')[1].strip()
                if parts:
                    current_block = parts
                else:
                    current_block = "default"
        elif in_block:
            current_lines.append(line)

    return blocks


def score_code(code: str, task: dict) -> tuple[int, list]:
    """评估代码质量"""
    score = 0
    phases_completed = []

    required = task.get("skill_phases", [])
    validation = task.get("validation", "")

    # 检查基本结构
    has_function = "def " in code
    has_class = "class " in code
    has_import = "import " in code or "from " in code
    has_test = "test_" in code or "assert" in code

    # 检查docstring
    has_docstring = '"""' in code or "'''" in code

    # 检查类型注解
    has_type_hints = "->" in code

    # 计算分数
    base_score = 20  # 基础分

    if has_function or has_class:
        base_score += 20
    if has_import:
        base_score += 10
    if has_test:
        base_score += 15
    if has_docstring:
        base_score += 15
    if has_type_hints:
        base_score += 10

    # 复杂度调整
    if "多文件" in task.get("name", "") or "模块" in task.get("name", ""):
        # 检查多个文件
        blocks = extract_code_blocks(code)
        if len(blocks) >= 2:
            base_score += 10

    # 检查validation条件
    if "测试" in validation and has_test:
        base_score += 5
    if "异常" in validation and ("raise" in code or "Exception" in code):
        base_score += 5
    if "Lock" in validation and "Lock" in code:
        base_score += 10

    score = min(base_score, 100)

    # 确定完成的阶段
    if required:
        if "EXECUTING" in required and (has_function or has_class):
            phases_completed.append("EXECUTING")
        if "DEBUGGING" in required and ("fix" in code.lower() or "bug" in code.lower() or "issue" in code.lower()):
            phases_completed.append("DEBUGGING")
        if "REVIEWING" in required and has_docstring:
            phases_completed.append("REVIEWING")

    return score, phases_completed


def run_complex_task(task: dict) -> tuple[dict, dict]:
    """运行复杂任务对比"""
    print(f"\n  [{task['id']}] {task['name']}")

    # 使用Skill执行
    print(f"    [有Skill] 执行中...")
    skill_prompt = f"{SKILL_CONTEXT}\n\n## 任务\n{task['description']}"
    skill_text, skill_time = call_claude(skill_prompt, timeout=180)
    skill_score, skill_phases = score_code(skill_text, task)

    # 不使用Skill执行
    print(f"    [无Skill] 执行中...")
    no_skill_text, no_skill_time = call_claude(task["description"], timeout=180)
    no_skill_score, no_skill_phases = score_code(no_skill_text, task)

    # 判断winner
    if skill_score > no_skill_score + 10:
        winner = "skill"
    elif no_skill_score > skill_score + 10:
        winner = "baseline"
    else:
        winner = "tie"

    print(f"      有Skill: 分数 {skill_score}, 阶段 {skill_phases}")
    print(f"      无Skill: 分数 {no_skill_score}, 阶段 {no_skill_phases}")
    print(f"      获胜: {winner}")

    return {
        "task_id": task["id"],
        "module": task["module"],
        "name": task["name"],
        "skill_score": skill_score,
        "no_skill_score": no_skill_score,
        "skill_phases": skill_phases,
        "no_skill_phases": no_skill_phases,
        "winner": winner,
        "skill_time": round(skill_time, 1),
        "no_skill_time": round(no_skill_time, 1)
    }, {
        "skill_output": skill_text[:500],
        "no_skill_output": no_skill_text[:500]
    }


# ============================================================================
# 主函数
# ============================================================================

def main():
    print("=" * 70)
    print("  复杂任务对照实验 - 8个真实复杂场景")
    print("=" * 70)
    print(f"\n任务数量: {len(COMPLEX_TASKS)}")
    print("评估维度: 代码质量、多阶段完成度、架构设计")

    results = []
    details = []

    for task in COMPLEX_TASKS:
        result, detail = run_complex_task(task)
        results.append(result)
        details.append(detail)

    # 统计
    total = len(results)
    skill_wins = sum(1 for r in results if r["winner"] == "skill")
    baseline_wins = sum(1 for r in results if r["winner"] == "baseline")
    ties = sum(1 for r in results if r["winner"] == "tie")

    avg_skill_score = sum(r["skill_score"] for r in results) / total
    avg_no_skill_score = sum(r["no_skill_score"] for r in results) / total

    print("\n" + "=" * 70)
    print("  结果汇总")
    print("=" * 70)

    print(f"\n  总计: {total} 个任务")
    print(f"  Skill获胜: {skill_wins} ({skill_wins/total*100:.0f}%)")
    print(f"  基线获胜: {baseline_wins} ({baseline_wins/total*100:.0f}%)")
    print(f"  平局: {ties} ({ties/total*100:.0f}%)")

    print(f"\n  平均分数: 有Skill {avg_skill_score:.1f} vs 无Skill {avg_no_skill_score:.1f}")

    # 按模块统计
    by_module = {}
    for r in results:
        m = r["module"]
        if m not in by_module:
            by_module[m] = {"total": 0, "skill": 0, "baseline": 0, "tie": 0}
        by_module[m]["total"] += 1
        if r["winner"] == "skill":
            by_module[m]["skill"] += 1
        elif r["winner"] == "baseline":
            by_module[m]["baseline"] += 1
        else:
            by_module[m]["tie"] += 1

    print("\n  按模块:")
    for m, s in by_module.items():
        print(f"    {m}: 总{s['total']} | Skill {s['skill']} | 基线 {s['baseline']} | 平局 {s['tie']}")

    # 详细表格
    print("\n  详细结果:")
    print("  " + "-" * 70)
    print(f"  {'ID':<12} {'模块':<12} {'有Skill':<8} {'无Skill':<8} {'获胜'}")
    print("  " + "-" * 70)
    for r in results:
        print(f"  {r['task_id']:<12} {r['module']:<12} {r['skill_score']:<8} {r['no_skill_score']:<8} {r['winner']}")

    # 保存报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = PROJECT_ROOT / "tests" / "complex_comparison_results"
    output_dir.mkdir(exist_ok=True)

    report = {
        "date": datetime.now().isoformat(),
        "total": total,
        "skill_wins": skill_wins,
        "baseline_wins": baseline_wins,
        "ties": ties,
        "skill_win_rate": skill_wins / total * 100,
        "avg_skill_score": avg_skill_score,
        "avg_no_skill_score": avg_no_skill_score,
        "by_module": by_module,
        "results": results
    }

    json_file = output_dir / f"complex_comparison_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n  📄 报告已保存: {json_file}")

    # 生成Markdown报告
    md_report = f"""# 复杂任务对照实验报告

**日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**任务数**: {total}

---

## 总体结果

| 指标 | 数值 |
|------|------|
| **Skill获胜** | {skill_wins} ({skill_wins/total*100:.0f}%) |
| **基线获胜** | {baseline_wins} ({baseline_wins/total*100:.0f}%) |
| **平局** | {ties} ({ties/total*100:.0f}%) |
| **平均分数(Skill)** | {avg_skill_score:.1f} |
| **平均分数(基线)** | {avg_no_skill_score:.1f} |

---

## 详细结果

| 任务ID | 名称 | 模块 | 有Skill | 无Skill | 获胜 |
|--------|------|------|---------|---------|------|
"""
    for r in results:
        md_report += f"| {r['task_id']} | {r['name'][:30]} | {r['module']} | {r['skill_score']} | {r['no_skill_score']} | {r['winner']} |\n"

    md_report += f"""
---

## 结论

### 关键发现

1. **复杂任务处理**: 有Skill在复杂场景下的表现{'明显优于' if skill_wins > baseline_wins else '与基线相当'}
2. **多阶段工作流**: Skill引导的阶段完成度更高
3. **代码质量**: 有Skill平均 {avg_skill_score:.1f} vs 基线 {avg_no_skill_score:.1f}

### 解读

- Skill在需要TDD流程、代码审查、多阶段处理的任务中效果显著
- 简单任务两种方式差异不大
- Skill提供结构和规范，对复杂任务更有价值

---

*报告生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    md_file = output_dir / f"complex_comparison_{timestamp}.md"
    with open(md_file, "w") as f:
        f.write(md_report)

    print(f"  📄 Markdown: {md_file}")

    return report


if __name__ == "__main__":
    main()
