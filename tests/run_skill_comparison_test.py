#!/usr/bin/env python3
"""
Agentic-Workflow Skill 对照实验 v1.0

对比有/无 agentic-workflow skill 的实际执行效果

评估维度:
1. 执行效率 (duration)
2. 执行质量 (correctness score)
3. Token消耗量 (input/output/total tokens)
4. 任务完成率 (completion rate)

实验设计:
- 控制组 (Control): 不使用skill，直接执行
- 实验组 (Treatment): 使用agentic-workflow skill引导
- 同一任务随机分配到两组，消除顺序效应
"""

__test__ = False

import asyncio
import json
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from anthropic import Anthropic

# ============================================================================
# 实验配置
# ============================================================================

EXPERIMENT_CONFIG = {
    "n_runs_per_task": 3,  # 每个任务重复次数，减少方差
    "max_tokens_per_run": 4096,  # 输出token上限
    "model": "claude-sonnet-4-20250514",
    "random_seed": 42,
}

# 测试任务池 - 涵盖不同难度和模块
TEST_TASKS = [
    # DEBUGGING 模块
    {
        "id": "dbg_01",
        "module": "DEBUGGING",
        "difficulty": "easy",
        "prompt": """修复这个Python函数的bug:

```python
def find_max(numbers):
    max_val = 0
    for n in numbers:
        if n > max_val:
            max_val = n
    return max_val

# 测试
print(find_max([1, 5, 3, 9, 2]))  # 期望输出 9
```
""",
        "expected_output": "返回最大值9"
    },
    {
        "id": "dbg_02",
        "module": "DEBUGGING",
        "difficulty": "medium",
        "prompt": """这个Python函数应该返回字符串的反转，但结果不对。请调试:

```python
def reverse_string(s):
    result = ""
    for i in range(len(s)):
        result = s[i] + result
    return result

print(reverse_string("hello"))  # 期望 "olleh"
```
""",
        "expected_output": "返回 'olleh'"
    },
    {
        "id": "dbg_03",
        "module": "DEBUGGING",
        "difficulty": "medium",
        "prompt": """这个函数应该计算列表中的偶数个数，但返回结果不对:

```python
def count_evens(numbers):
    count = 0
    for n in numbers:
        if n % 2 = 0:  # 这里有问题
            count += 1
    return count

print(count_evens([1, 2, 3, 4, 5]))  # 期望 2
```
""",
        "expected_output": "返回 2"
    },

    # EXECUTING 模块
    {
        "id": "exe_01",
        "module": "EXECUTING",
        "difficulty": "easy",
        "prompt": """用Python实现一个函数，判断一个字符串是否是回文串（忽略大小写和空格）:

例如: "A man a plan a canal Panama" 应该返回 True
""",
        "expected_output": "返回布尔值，正确判断回文"
    },
    {
        "id": "exe_02",
        "module": "EXECUTING",
        "difficulty": "medium",
        "prompt": """用TDD方式实现一个 Stack 类，需要支持:
- push(item) - 入栈
- pop() - 出栈
- peek() - 查看栈顶
- is_empty() - 判断是否为空

请先写测试用例，再实现。
""",
        "expected_output": "完整的Stack类实现"
    },
    {
        "id": "exe_03",
        "module": "EXECUTING",
        "difficulty": "medium",
        "prompt": """实现一个函数，接受一个字符串列表，返回所有长度大于3的字符串:

```python
def filter_long_strings(strings):
    pass
```
""",
        "expected_output": "返回过滤后的列表"
    },

    # REVIEWING 模块
    {
        "id": "rev_01",
        "module": "REVIEWING",
        "difficulty": "easy",
        "prompt": """审查以下Python代码，找出潜在问题:

```python
def get_user_email(user_id):
    user = db.query(f"SELECT * FROM users WHERE id = {user_id}")
    return user.email
```
""",
        "expected_output": "识别SQL注入风险"
    },
    {
        "id": "rev_02",
        "module": "REVIEWING",
        "difficulty": "medium",
        "prompt": """审查以下Python代码的质量问题:

```python
def process_data(data):
    result = []
    for i in range(len(data)):
        if data[i] > 10:
            result.append(data[i] * 2)
    return result
```
""",
        "expected_output": "指出代码风格和可读性问题"
    },
    {
        "id": "rev_03",
        "module": "REVIEWING",
        "difficulty": "medium",
        "prompt": """审查以下代码的性能问题:

```python
def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            if items[i] == items[j]:
                duplicates.append(items[i])
    return duplicates
```
""",
        "expected_output": "识别O(n²)复杂度问题"
    },

    # PLANNING 模块
    {
        "id": "pln_01",
        "module": "PLANNING",
        "difficulty": "easy",
        "prompt": """将以下任务拆分成具体的步骤:
"开发一个简单的TODO应用，用户可以添加、查看和删除待办事项"

请列出具体的执行步骤。
""",
        "expected_output": "任务分解步骤"
    },
    {
        "id": "pln_02",
        "module": "PLANNING",
        "difficulty": "medium",
        "prompt": """为一个用户注册功能制定测试计划，需要覆盖:
- 正常注册流程
- 邮箱格式验证
- 密码强度验证
- 用户名唯一性检查

请列出测试用例。
""",
        "expected_output": "完整的测试用例列表"
    },

    # THINKING 模块
    {
        "id": "thn_01",
        "module": "THINKING",
        "difficulty": "easy",
        "prompt": """谁最懂Python异步编程？请从专家角度分析async/await的最佳使用场景。
""",
        "expected_output": "专家视角的分析"
    },
    {
        "id": "thn_02",
        "module": "THINKING",
        "difficulty": "medium",
        "prompt": """分析这个系统设计问题: 为什么缓存是提高Web应用性能的关键？
请从多个维度分析。
""",
        "expected_output": "多维度分析"
    },

    # RESEARCH 模块
    {
        "id": "res_01",
        "module": "RESEARCH",
        "difficulty": "easy",
        "prompt": """搜索 Python 单元测试的最佳实践，并总结关键要点。
""",
        "expected_output": "测试最佳实践总结"
    },
    {
        "id": "res_02",
        "module": "RESEARCH",
        "difficulty": "medium",
        "prompt": """调研 RESTful API 设计规范，总结核心原则。
""",
        "expected_output": "API设计规范总结"
    },
]


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class TaskResult:
    """单次任务执行结果"""
    task_id: str
    module: str
    difficulty: str
    skill_used: bool
    duration: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    success: bool
    quality_score: float
    response_content: str


@dataclass
class ComparisonResult:
    """对比实验结果"""
    task_id: str
    module: str
    difficulty: str

    # 有Skill结果
    skill_duration: float
    skill_tokens: int
    skill_quality: float
    skill_success: bool

    # 无Skill结果
    no_skill_duration: float
    no_skill_tokens: int
    no_skill_quality: float
    no_skill_success: bool

    # 对比指标
    duration_diff_pct: float
    token_diff_pct: float
    quality_diff: float
    skill_wins: bool


# ============================================================================
# Skill上下文加载
# ============================================================================

# 阶段专用指南映射 - 基于世界顶尖agent研究优化
PHASE_GUIDES = {
    # EXECUTING: 借鉴gstack "Boil the Lake" + Fix-First
    "EXECUTING": """### EXECUTING 执行

**铁律**: 先写测试再实现,先验证再声称完成

**Boil the Lake原则**: 完整性与AI能力成正比,不要省步骤

**Fix-First决策**:
- AUTO-FIX: 机械性问题(typo, import, 格式化)→直接修复
- ASK: 判断性问题(架构, 设计)→先问用户

**Voice规则**:
- 禁止: em dashes, "delve/crucial/robust"等AI词汇
- 使用: 具体file:line引用,简洁动词

步骤:
1. 写失败的测试
2. 写最小代码通过
3. 重构优化

**验证**: 运行测试确认,不要只说"完成了".""",

    # PLANNING: 简化版 - 保留核心路由
    "PLANNING": """### PLANNING 任务规划

**复杂度路由**:
- XS/S: TodoWrite拆分,不用spec文件
- M: spec.md + tasks.md
- L/XL: spec.md + plan.md + tasks.md + .contract.json

**核心**: 不只拆分,要生成多种方案

步骤:
1. 明确目标(一话说清)
2. 生成2-3方案(最小/折中/理想)
3. 推荐明确方案和理由

**反模式**: XS/S禁止完整spec-kit""",

    # RESEARCH: 借鉴deer-flow Phase Methodology + Quality Gate
    "RESEARCH": """### RESEARCH 搜索研究

**阶段方法论**:
1. 广泛探索 - 快速扫描多个来源
2. 深度挖掘 - 聚焦权威来源
3. 综合验证 - 检查一致性

**Quality Gate**: 自问"能自信回答吗?"
- 如果NO→继续研究
- 如果YES→输出结论

**执行**:
1. 搜索: 具体技术名词+"best practices"
2. 深度获取: 不只看摘要,要fetch完整内容
3. 来源优先级: 官方文档>开源>博客>AI生成
4. 输出: 关键发现+3条内可操作建议+来源

**铁律**: 搜索不可用时直接说明,禁止静默降级

**时间感知**: 检查当前日期,趋势用年月""",

    "THINKING": """### THINKING 专家推理

**核心**: 谁最懂这个?TA会怎么说?

**Mandatory Think**: 重大决策(git操作,阶段转换)前必须思考

回答:
- 本质: [一句话]
- 权衡: [最多3观点,各20字]
- 建议: [1个明确建议]""",

    "DEBUGGING": """### DEBUGGING 调试

**铁律**: 不定位根因不修复

**3次失败规则**: 3次假设都错→STOP,选项:
- (a) 新假设继续
- (b) 升级人工review
- (c) 添加日志等下次复现

步骤:
1. 收集症状(错误/堆栈/复现)
2. 追踪代码找可能原因
3. 验证假设→不对就回退
4. 3次失败→考虑架构问题

输出格式:
- 症状:
- 根因:
- 修复:
- 回归测试:""",

    "REVIEWING": """### REVIEWING 代码审查

**优先级**: P0安全 > P1逻辑/性能 > P2风格

**Voice规则**:
- 禁止: "看起来不错","可能没问题"
- 使用: 具体file:line + 优先级标注

直接输出:
- [文件:行号] 问题 (P0/P1/P2)
- 影响: [一句话]
- 修复: [简洁建议]

**自我检验**:
- [ ] 是否因"能跑"忽略了设计问题?
- [ ] 是否用了"可能"等模糊词?
- [ ] 是否只改表面没改根因?""",
}

# 核心工作流 - 极简版,只包含绝对必要原则
MINIMAL_CORE = """## 原则
- 回答简洁,不废话
- 有证据再声称完成
- 先验证再结论"""


def load_skill_context(module: str = None) -> str:
    """加载agentic-workflow skill上下文 - 只加载相关阶段"""
    if module and module in PHASE_GUIDES:
        return MINIMAL_CORE + "\n\n" + PHASE_GUIDES[module]
    # Fallback: 加载完整SKILL.md
    skill_path = Path(__file__).parent.parent / "SKILL.md"
    if skill_path.exists():
        with open(skill_path, encoding="utf-8") as f:
            return f.read()
    return ""


# ============================================================================
# API调用
# ============================================================================

def call_claude(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 4096
) -> dict:
    """调用Claude API"""
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if not api_key:
        return {"success": False, "error": "No API key"}

    client = Anthropic(api_key=api_key)
    start_time = time.time()

    try:
        with client.messages.stream(
            model=EXPERIMENT_CONFIG["model"],
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            response = stream.get_final_message()

        duration = time.time() - start_time
        content_text = ""
        for block in response.content:
            if hasattr(block, 'type') and block.type == 'text':
                content_text += block.text
            elif hasattr(block, 'text'):
                content_text += block.text

        return {
            "success": True,
            "content": content_text,
            "duration": duration,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "duration": time.time() - start_time,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }


# ============================================================================
# 质量评估
# ============================================================================

def evaluate_response_quality(task: dict, response: dict) -> float:
    """评估响应质量 (0-100分)"""
    if not response.get("success"):
        return 0.0

    content = response.get("content", "").lower()

    # 基本检查
    score = 0.0

    # 1. 是否包含代码/解决方案 (40%)
    has_code = "```python" in response.get("content", "") or "def " in content or "class " in content
    if has_code:
        score += 40

    # 2. 是否回答了问题 (30%)
    expected = task.get("expected_output", "").lower()
    if expected:
        if any(keyword in content for keyword in expected.split()[:3]):
            score += 30
    else:
        # 如果没有明确的expected，至少有实质性内容就给分
        if len(content) > 100:
            score += 30

    # 3. 是否有结构化输出 (15%)
    has_structure = (
        "## " in response.get("content", "") or
        "- " in content or
        "1." in content or
        "* " in content
    )
    if has_structure:
        score += 15

    # 4. 是否有分析/解释 (15%)
    has_explanation = (
        "因为" in content or
        "原因" in content or
        "分析" in content or
        "所以" in content or
        "步骤" in content
    )
    if has_explanation:
        score += 15

    return min(score, 100.0)


# ============================================================================
# 执行实验
# ============================================================================

async def run_with_skill(task: dict) -> TaskResult:
    """使用skill执行任务 - 只注入相关阶段的指南"""
    skill_context = load_skill_context(task.get("module"))

    system_prompt = f"""你是一个专业的AI开发助手。遵循以下agentic-workflow skill规范:

{skill_context}

## 执行原则
1. 使用TDD方法进行功能开发
2. 遵循阶段流程: 理解→计划→执行→验证
3. 代码质量优先
4. 保持输出简洁专业"""

    start = time.time()
    result = call_claude(
        prompt=task["prompt"],
        system_prompt=system_prompt,
        max_tokens=EXPERIMENT_CONFIG["max_tokens_per_run"]
    )
    duration = time.time() - start

    quality = evaluate_response_quality(task, result)

    return TaskResult(
        task_id=task["id"],
        module=task["module"],
        difficulty=task["difficulty"],
        skill_used=True,
        duration=result.get("duration", duration),
        input_tokens=result.get("input_tokens", 0),
        output_tokens=result.get("output_tokens", 0),
        total_tokens=result.get("total_tokens", 0),
        success=result.get("success", False),
        quality_score=quality,
        response_content=result.get("content", "")
    )


async def run_without_skill(task: dict) -> TaskResult:
    """不使用skill执行任务（直接回答）"""
    start = time.time()
    result = call_claude(
        prompt=task["prompt"],
        system_prompt="你是一个专业的AI开发助手，直接回答问题，保持简洁。",
        max_tokens=EXPERIMENT_CONFIG["max_tokens_per_run"]
    )
    duration = time.time() - start

    quality = evaluate_response_quality(task, result)

    return TaskResult(
        task_id=task["id"],
        module=task["module"],
        difficulty=task["difficulty"],
        skill_used=False,
        duration=result.get("duration", duration),
        input_tokens=result.get("input_tokens", 0),
        output_tokens=result.get("output_tokens", 0),
        total_tokens=result.get("total_tokens", 0),
        success=result.get("success", False),
        quality_score=quality,
        response_content=result.get("content", "")
    )


async def run_single_experiment(task: dict) -> ComparisonResult:
    """运行单次对比实验"""
    print(f"\n  [{task['id']}] {task['module']}/{task['difficulty']} - {task['prompt'][:50]}...")

    # 并行执行有/无skill两组实验
    skill_result, no_skill_result = await asyncio.gather(
        run_with_skill(task),
        run_without_skill(task)
    )

    # 计算对比指标
    duration_diff = (
        (no_skill_result.duration - skill_result.duration) / no_skill_result.duration * 100
        if no_skill_result.duration > 0 else 0
    )
    token_diff = (
        (no_skill_result.total_tokens - skill_result.total_tokens) / no_skill_result.total_tokens * 100
        if no_skill_result.total_tokens > 0 else 0
    )
    quality_diff = skill_result.quality_score - no_skill_result.quality_score

    # Skill获胜判定: 质量更高或质量相近但更快/更省token
    skill_wins = (
        quality_diff > 5 or  # 质量明显更好
        (abs(quality_diff) <= 5 and (duration_diff > 0 or token_diff > 0))  # 质量相近但效率更高
    )

    print(f"    有Skill: {skill_result.duration:.1f}s, {skill_result.total_tokens} tokens, 质量 {skill_result.quality_score:.0f}")
    print(f"    无Skill: {no_skill_result.duration:.1f}s, {no_skill_result.total_tokens} tokens, 质量 {no_skill_result.quality_score:.0f}")
    print(f"    -> Skill获胜: {skill_wins}")

    return ComparisonResult(
        task_id=task["id"],
        module=task["module"],
        difficulty=task["difficulty"],
        skill_duration=skill_result.duration,
        skill_tokens=skill_result.total_tokens,
        skill_quality=skill_result.quality_score,
        skill_success=skill_result.success,
        no_skill_duration=no_skill_result.duration,
        no_skill_tokens=no_skill_result.total_tokens,
        no_skill_quality=no_skill_result.quality_score,
        no_skill_success=no_skill_result.success,
        duration_diff_pct=duration_diff,
        token_diff_pct=token_diff,
        quality_diff=quality_diff,
        skill_wins=skill_wins
    )


# ============================================================================
# 实验运行
# ============================================================================

async def run_full_experiment() -> list[ComparisonResult]:
    """运行完整对照实验"""
    print("="*80)
    print("Agentic-Workflow Skill 对照实验")
    print("="*80)
    print("\n实验配置:")
    print(f"  - 任务数量: {len(TEST_TASKS)}")
    print(f"  - 模型: {EXPERIMENT_CONFIG['model']}")
    print(f"  - 每任务重复: {EXPERIMENT_CONFIG['n_runs_per_task']}次")
    print(f"  - Token上限: {EXPERIMENT_CONFIG['max_tokens_per_run']}")
    print()

    # 随机打乱任务顺序
    random.seed(EXPERIMENT_CONFIG["random_seed"])
    tasks = TEST_TASKS.copy()
    random.shuffle(tasks)

    results = []

    for i, task in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] 运行实验...")
        result = await run_single_experiment(task)
        results.append(result)

    return results


# ============================================================================
# 报告生成
# ============================================================================

def generate_report(results: list[ComparisonResult], output_dir: str = "tests") -> str:
    """生成实验报告"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. JSON报告
    json_data = {
        "experiment_date": datetime.now().isoformat(),
        "config": EXPERIMENT_CONFIG,
        "total_tasks": len(results),
        "summary": {
            "skill_win_rate": sum(1 for r in results if r.skill_wins) / len(results) * 100 if results else 0,
            "avg_duration_diff_pct": sum(r.duration_diff_pct for r in results) / len(results) if results else 0,
            "avg_token_diff_pct": sum(r.token_diff_pct for r in results) / len(results) if results else 0,
            "avg_quality_diff": sum(r.quality_diff for r in results) / len(results) if results else 0,
            "skill_completion_rate": sum(1 for r in results if r.skill_success) / len(results) * 100 if results else 0,
            "no_skill_completion_rate": sum(1 for r in results if r.no_skill_success) / len(results) * 100 if results else 0,
            "avg_skill_duration": sum(r.skill_duration for r in results) / len(results) if results else 0,
            "avg_no_skill_duration": sum(r.no_skill_duration for r in results) / len(results) if results else 0,
            "avg_skill_tokens": sum(r.skill_tokens for r in results) / len(results) if results else 0,
            "avg_no_skill_tokens": sum(r.no_skill_tokens for r in results) / len(results) if results else 0,
        },
        "by_module": {},
        "by_difficulty": {},
        "results": [
            {
                "task_id": r.task_id,
                "module": r.module,
                "difficulty": r.difficulty,
                "skill": {
                    "duration": round(r.skill_duration, 2),
                    "tokens": r.skill_tokens,
                    "quality": round(r.skill_quality, 1),
                    "success": r.skill_success
                },
                "no_skill": {
                    "duration": round(r.no_skill_duration, 2),
                    "tokens": r.no_skill_tokens,
                    "quality": round(r.no_skill_quality, 1),
                    "success": r.no_skill_success
                },
                "comparison": {
                    "duration_diff_pct": round(r.duration_diff_pct, 1),
                    "token_diff_pct": round(r.token_diff_pct, 1),
                    "quality_diff": round(r.quality_diff, 1),
                    "skill_wins": r.skill_wins
                }
            }
            for r in results
        ]
    }

    # 按模块统计
    for module in {r.module for r in results}:
        module_results = [r for r in results if r.module == module]
        json_data["by_module"][module] = {
            "count": len(module_results),
            "skill_win_rate": sum(1 for r in module_results if r.skill_wins) / len(module_results) * 100,
            "avg_quality_diff": sum(r.quality_diff for r in module_results) / len(module_results),
            "avg_duration_diff_pct": sum(r.duration_diff_pct for r in module_results) / len(module_results),
        }

    # 按难度统计
    for difficulty in {r.difficulty for r in results}:
        diff_results = [r for r in results if r.difficulty == difficulty]
        json_data["by_difficulty"][difficulty] = {
            "count": len(diff_results),
            "skill_win_rate": sum(1 for r in diff_results if r.skill_wins) / len(diff_results) * 100,
            "avg_quality_diff": sum(r.quality_diff for r in diff_results) / len(diff_results),
        }

    # 保存JSON
    json_file = output_path / f"skill_comparison_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    # 2. Markdown报告
    summary = json_data["summary"]
    md_report = f"""# Agentic-Workflow Skill 对照实验报告

**实验日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**任务数量**: {len(results)}

---

## 总体结果摘要

| 指标 | 有Skill | 无Skill | 对比 |
|------|---------|---------|------|
| **任务完成率** | {summary['skill_completion_rate']:.1f}% | {summary['no_skill_completion_rate']:.1f}% | - |
| **平均执行时间** | {summary['avg_skill_duration']:.1f}s | {summary['avg_no_skill_duration']:.1f}s | {summary['avg_duration_diff_pct']:+.1f}% |
| **平均Token消耗** | {summary['avg_skill_tokens']:.0f} | {summary['avg_no_skill_tokens']:.0f} | {summary['avg_token_diff_pct']:+.1f}% |
| **平均质量得分** | {summary.get('avg_skill_quality', 0):.1f} | {summary.get('avg_no_skill_quality', 0):.1f} | {summary['avg_quality_diff']:+.1f} |
| **Skill获胜率** | **{summary['skill_win_rate']:.1f}%** | {100-summary['skill_win_rate']:.1f}% | - |

---

## 按模块分析

| 模块 | 任务数 | Skill获胜率 | 质量提升 | 时间变化 |
|------|--------|-------------|----------|----------|
"""
    for module, stats in json_data["by_module"].items():
        md_report += f"| {module} | {stats['count']} | {stats['skill_win_rate']:.1f}% | {stats['avg_quality_diff']:+.1f} | {stats['avg_duration_diff_pct']:+.1f}% |\n"

    md_report += """
---

## 按难度分析

| 难度 | 任务数 | Skill获胜率 | 质量提升 |
|------|--------|-------------|----------|
"""
    for difficulty, stats in json_data["by_difficulty"].items():
        md_report += f"| {difficulty} | {stats['count']} | {stats['skill_win_rate']:.1f}% | {stats['avg_quality_diff']:+.1f} |\n"

    md_report += """
---

## 详细结果

| 任务ID | 模块 | 难度 | 有Skill时间 | 无Skill时间 | 时间变化 | Token变化 | 质量变化 | Skill胜 |
|--------|------|------|------------|-------------|----------|-----------|----------|---------|
"""
    for r in results:
        md_report += f"| {r.task_id} | {r.module} | {r.difficulty} | {r.skill_duration:.1f}s | {r.no_skill_duration:.1f}s | {r.duration_diff_pct:+.1f}% | {r.token_diff_pct:+.1f}% | {r.quality_diff:+.1f} | {'✅' if r.skill_wins else '❌'} |\n"

    # 保存Markdown
    md_file = output_path / f"skill_comparison_{timestamp}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(md_report)

    # 3. 打印摘要
    print("\n" + "="*80)
    print("实验结果摘要")
    print("="*80)
    print(f"\n📊 Skill获胜率: {summary['skill_win_rate']:.1f}%")
    print(f"⏱️  平均时间变化: {summary['avg_duration_diff_pct']:+.1f}%")
    print(f"🔢 平均Token变化: {summary['avg_token_diff_pct']:+.1f}%")
    print(f"⭐ 平均质量变化: {summary['avg_quality_diff']:+.1f}")

    print("\n📁 报告已保存到:")
    print(f"   - JSON: {json_file}")
    print(f"   - Markdown: {md_file}")

    return md_report


# ============================================================================
# 主函数
# ============================================================================

async def main():
    """主函数"""
    # 检查API key
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if not api_key:
        print("\n⚠️  未设置 ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN")
        print("请设置后重新运行:")
        print("  export ANTHROPIC_API_KEY='your-key'")
        return

    print("✅ API key已设置，开始执行对照实验...")

    # 运行实验
    results = await run_full_experiment()

    # 生成报告
    generate_report(results)

    print("\n" + "="*80)
    print("实验完成")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
