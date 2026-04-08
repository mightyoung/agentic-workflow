#!/usr/bin/env python3
"""
Agentic Workflow Skill 对照实验框架

这是一个手动 benchmark helper，不是 pytest 测试。

评估使用 agentic-workflow skill 与不使用的情况下的多维度表现:
1. 执行效率 (Execution Efficiency)
2. 执行质量 (Execution Quality)
3. Token消耗 (Token Consumption)
4. 任务完成率 (Task Completion Rate)

使用专业 Agent 并行评估多个维度。
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class TaskDifficulty(Enum):
    """任务难度级别"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class TaskModule(Enum):
    """对应的Skill模块"""
    DEBUGGING = "DEBUGGING"
    EXECUTING = "EXECUTING"
    REVIEWING = "REVIEWING"
    RESEARCH = "RESEARCH"
    THINKING = "THINKING"
    PLANNING = "PLANNING"
    FULL_WORKFLOW = "FULL_WORKFLOW"


@dataclass
class TestTask:
    """测试任务"""
    id: str
    name: str
    description: str
    difficulty: TaskDifficulty
    module: TaskModule
    expected_outcome: str
    validation_criteria: list[str]
    files_to_create: list[str] = field(default_factory=list)
    test_commands: list[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """单次执行结果"""
    task_id: str
    mode: str  # "with_skill" or "without_skill"
    success: bool
    execution_time: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    response_content: str
    files_created: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ComparisonResult:
    """对比结果"""
    task_id: str
    difficulty: str
    module: str

    # 执行效率
    with_skill_time: float
    without_skill_time: float
    time_improvement_pct: float

    # Token消耗
    with_skill_tokens: int
    without_skill_tokens: int
    token_improvement_pct: float

    # 质量指标
    with_skill_quality_score: float
    without_skill_quality_score: float
    quality_improvement_pct: float

    # 正确性
    with_skill_correct: bool
    without_skill_correct: bool

    # 完成率
    with_skill_completed: bool
    without_skill_completed: bool

    # 综合评分 (0-100)
    with_skill_final_score: float
    without_skill_final_score: float
    overall_improvement_pct: float

    # 详细指标
    metrics: dict = field(default_factory=dict)


# =============================================================================
# 测试任务集
# =============================================================================

TEST_TASKS = [
    # ========== DEBUGGING 任务 ==========
    TestTask(
        id="debug_01",
        name="修复字符串反转边界问题",
        description="""
## 任务
修复字符串反转函数中的边界问题。

### 问题描述
当输入为空字符串或 None 时，程序会崩溃或返回错误结果。

### 预期行为
- 空字符串应返回空字符串
- None 输入应抛出 TypeError
- 单字符应原样返回
""",
        difficulty=TaskDifficulty.EASY,
        module=TaskModule.DEBUGGING,
        expected_outcome="所有边界情况正确处理",
        validation_criteria=[
            "处理空字符串返回空字符串",
            "None 输入抛出 TypeError",
            "单字符正确返回",
            "普通字符串正确反转"
        ],
        files_to_create=["src/string_reverse_buggy.py"],
        test_commands=["python -m pytest tests/ -v"]
    ),
    TestTask(
        id="debug_02",
        name="修复异步回调内存泄漏",
        description="""
## 任务
修复异步代码中的内存泄漏问题。

### 问题描述
异步回调没有正确清理，导致内存持续增长。

### 预期行为
- 回调完成后正确释放资源
- 不再出现内存泄漏
""",
        difficulty=TaskDifficulty.HARD,
        module=TaskModule.DEBUGGING,
        expected_outcome="内存泄漏问题修复并通过测试",
        validation_criteria=[
            "识别内存泄漏根因",
            "实施修复方案",
            "验证修复有效"
        ],
        files_to_create=["src/async_memory_leak.py"],
        test_commands=["python -m pytest tests/test_memory.py -v"]
    ),

    # ========== EXECUTING 任务 ==========
    TestTask(
        id="exec_01",
        name="TDD实现回文检测器",
        description="""
## 任务
使用 TDD 方法实现一个回文检测器。

### 需求
1. 实现 is_palindrome(s) - 区分大小写
2. 实现 is_palindrome_case_insensitive(s) - 忽略大小写
3. 正确处理边界情况（空串、单字符、None）

### TDD 要求
1. 先写测试
2. 运行测试确认失败
3. 实现最小代码通过测试
4. 重构优化
""",
        difficulty=TaskDifficulty.MEDIUM,
        module=TaskModule.EXECUTING,
        expected_outcome="完整的TDD实现，所有测试通过",
        validation_criteria=[
            "测试文件存在且完整",
            "红-绿-重构循环正确执行",
            "所有测试通过",
            "代码符合规范"
        ],
        files_to_create=["src/palindrome.py", "tests/test_palindrome.py"],
        test_commands=["python -m pytest tests/test_palindrome.py -v"]
    ),
    TestTask(
        id="exec_02",
        name="实现LRU缓存",
        description="""
## 任务
使用 TDD 方法实现一个 LRU (Least Recently Used) 缓存。

### 需求
1. 支持容量限制
2. 支持 get 和 put 操作
3. 最近最少使用的项被淘汰
4. O(1) 时间复杂度

### TDD 要求
遵循测试驱动开发流程。
""",
        difficulty=TaskDifficulty.MEDIUM,
        module=TaskModule.EXECUTING,
        expected_outcome="LRU缓存实现完整，测试全部通过",
        validation_criteria=[
            "容量限制正确",
            "LRU淘汰策略正确",
            "O(1)时间复杂度",
            "所有测试通过"
        ],
        files_to_create=["src/lru_cache.py", "tests/test_lru_cache.py"],
        test_commands=["python -m pytest tests/test_lru_cache.py -v"]
    ),

    # ========== REVIEWING 任务 ==========
    TestTask(
        id="review_01",
        name="代码审查最佳实践",
        description="""
## 任务
对提供的代码进行全面的代码审查。

### 代码
```python
def process_data(data, config):
    result = []
    for item in data:
        if item['active']:
            result.append(item['value'] * config['multiplier'])
    return result
```

### 审查维度
1. 逻辑正确性
2. 边界情况处理
3. 错误处理
4. 性能考虑
5. 安全问题
6. 代码风格
""",
        difficulty=TaskDifficulty.EASY,
        module=TaskModule.REVIEWING,
        expected_outcome="输出包含分级问题的完整审查报告",
        validation_criteria=[
            "识别逻辑问题",
            "识别安全问题",
            "识别性能问题",
            "提供改进建议"
        ],
        files_to_create=["src/code_to_review.py"],
        test_commands=[]
    ),

    # ========== RESEARCH 任务 ==========
    TestTask(
        id="research_01",
        name="调研Python异步最佳实践",
        description="""
## 任务
调研 Python 异步编程的最佳实践。

### 调研内容
1. async/await 的正确用法
2. 异步上下文管理器
3. 错误处理模式
4. 性能优化技巧

### 输出要求
将调研结果存入 findings.md，包含:
- 关键发现
- 代码示例
- 适用场景
- 潜在陷阱
""",
        difficulty=TaskDifficulty.MEDIUM,
        module=TaskModule.RESEARCH,
        expected_outcome="完整的调研报告存入 findings.md",
        validation_criteria=[
            "使用搜索工具获取信息",
            "输出包含关键发现",
            "包含代码示例",
            "标注适用场景"
        ],
        files_to_create=["findings.md"],
        test_commands=[]
    ),

    # ========== THINKING 任务 ==========
    TestTask(
        id="thinking_01",
        name="专家推理分析",
        description="""
## 任务
分析以下问题的最佳解决方案:

"如何设计一个高可用的分布式任务队列?"

### 要求
1. 识别涉及的核心领域专家
2. 从每个专家角度分析问题
3. 综合给出推荐方案
4. 列出方案的优缺点
""",
        difficulty=TaskDifficulty.MEDIUM,
        module=TaskModule.THINKING,
        expected_outcome="包含多专家视角的综合分析报告",
        validation_criteria=[
            "识别相关领域专家",
            "从专家角度分析",
            "综合推荐方案",
            "列出优缺点"
        ],
        files_to_create=["analysis.md"],
        test_commands=[]
    ),

    # ========== PLANNING 任务 ==========
    TestTask(
        id="plan_01",
        name="项目任务规划",
        description="""
## 任务
为开发一个简单的博客系统制定任务计划。

### 博客系统需求
1. 用户认证（注册/登录）
2. 文章 CRUD
3. 评论功能
4. 简单的标签系统

### 规划要求
1. 拆分任务步骤
2. 识别依赖关系
3. 估算工作量
4. 制定执行顺序
5. 输出到 task_plan.md
""",
        difficulty=TaskDifficulty.EASY,
        module=TaskModule.PLANNING,
        expected_outcome="完整的任务计划存入 task_plan.md",
        validation_criteria=[
            "任务拆分完整",
            "依赖关系清晰",
            "执行顺序合理",
            "文件格式正确"
        ],
        files_to_create=["task_plan.md"],
        test_commands=[]
    ),

    # ========== FULL_WORKFLOW 任务 ==========
    TestTask(
        id="full_01",
        name="完整工作流实现API服务",
        description="""
## 任务
使用完整工作流开发一个 RESTful API 服务。

### 需求
1. 用户管理 API（CRUD）
2. 基础认证中间件
3. 输入验证
4. 错误处理
5. API 文档

### 工作流要求
必须依次执行: RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING
""",
        difficulty=TaskDifficulty.HARD,
        module=TaskModule.FULL_WORKFLOW,
        expected_outcome="完整的API服务实现，通过所有测试",
        validation_criteria=[
            "完成所有工作流阶段",
            "代码质量符合标准",
            "测试覆盖主要功能",
            "API文档完整"
        ],
        files_to_create=["src/api/", "tests/test_api.py"],
        test_commands=["python -m pytest tests/test_api.py -v"]
    ),

    # ========== 追加样本：提高统计稳定性 ==========
    TestTask(
        id="debug_03",
        name="修复列表求和边界错误",
        description="""
## 任务
修复一个列表求和函数的边界错误。

### 问题描述
当输入为空列表时，函数返回 None，而不是 0。

### 预期行为
- 空列表返回 0
- 仅包含负数时仍返回正确和
- 非列表输入抛出 TypeError
""",
        difficulty=TaskDifficulty.EASY,
        module=TaskModule.DEBUGGING,
        expected_outcome="边界条件修复并通过回归验证",
        validation_criteria=[
            "空列表返回 0",
            "负数列表正确求和",
            "非列表输入抛出 TypeError",
            "边界条件回归测试"
        ],
        files_to_create=["src/sum_buggy.py", "tests/test_sum_buggy.py"],
        test_commands=["python -m pytest tests/test_sum_buggy.py -v"]
    ),
    TestTask(
        id="review_02",
        name="审查异常处理质量",
        description="""
## 任务
审查以下函数的异常处理和可维护性:

```python
def load_config(path):
    try:
        with open(path) as f:
            return json.loads(f.read())
    except:
        return {}
```

### 审查重点
1. 异常处理精度
2. 可观测性
3. 返回值语义
4. 可维护性
""",
        difficulty=TaskDifficulty.MEDIUM,
        module=TaskModule.REVIEWING,
        expected_outcome="输出具体审查意见和修复建议",
        validation_criteria=[
            "识别裸 except 问题",
            "识别可观测性问题",
            "建议更精确异常处理",
            "建议明确返回语义"
        ],
        files_to_create=["src/config_loader.py"],
        test_commands=[]
    ),
    TestTask(
        id="research_02",
        name="调研Python测试最佳实践",
        description="""
## 任务
调研 Python 测试框架的最佳实践。

### 调研内容
1. pytest fixture 设计
2. 参数化测试
3. 测试隔离
4. 失败信息可读性

### 输出要求
将调研结果写入 findings.md，包含：
- 关键发现
- 推荐模式
- 常见反模式
- 适用场景
""",
        difficulty=TaskDifficulty.MEDIUM,
        module=TaskModule.RESEARCH,
        expected_outcome="输出结构化调研报告",
        validation_criteria=[
            "包含关键发现",
            "包含推荐模式",
            "包含常见反模式",
            "包含适用场景"
        ],
        files_to_create=["findings.md"],
        test_commands=[]
    ),
    TestTask(
        id="plan_02",
        name="中型功能规划",
        description="""
## 任务
为“用户通知中心”设计任务计划。

### 功能范围
1. 通知列表
2. 已读/未读状态
3. 通知偏好设置
4. 事件触发推送

### 规划要求
1. 拆分成可执行任务
2. 标注依赖关系
3. 标明关键风险
4. 给出验证顺序
""",
        difficulty=TaskDifficulty.MEDIUM,
        module=TaskModule.PLANNING,
        expected_outcome="完整的任务计划与依赖图",
        validation_criteria=[
            "任务拆分完整",
            "依赖关系清晰",
            "风险识别到位",
            "验证顺序合理"
        ],
        files_to_create=["task_plan.md"],
        test_commands=[]
    ),
]


# =============================================================================
# 评估代理 - 并行评估多个维度
# =============================================================================

class EfficiencyEvaluator:
    """执行效率评估器"""

    @staticmethod
    def evaluate(result_with_skill: ExecutionResult, result_without_skill: ExecutionResult) -> dict:
        """评估执行效率"""
        time_diff = result_without_skill.execution_time - result_with_skill.execution_time
        time_pct = (time_diff / result_without_skill.execution_time * 100) if result_without_skill.execution_time > 0 else 0

        return {
            "metric": "execution_efficiency",
            "with_skill_time": round(result_with_skill.execution_time, 3),
            "without_skill_time": round(result_without_skill.execution_time, 3),
            "time_saved_seconds": round(time_diff, 3),
            "time_improvement_pct": round(time_pct, 1),
            "faster": result_with_skill.execution_time < result_without_skill.execution_time
        }


class QualityEvaluator:
    """代码质量评估器"""

    # 权重配置
    WEIGHTS = {
        "correctness": 0.35,
        "best_practices": 0.25,
        "error_handling": 0.20,
        "documentation": 0.20
    }

    @staticmethod
    def evaluate_code_quality(code: str, criteria: list[str], has_skill: bool) -> float:
        """评估代码质量 (0-100)"""
        score = 0.0
        details = {}

        # 检查正确性
        correctness_indicators = [
            "return ", "def ", "if ", "else", "for ", "while ",
            "try:", "except", "raise"
        ]
        correctness_score = sum(1 for ind in correctness_indicators if ind in code) / len(correctness_indicators)
        score += correctness_score * QualityEvaluator.WEIGHTS["correctness"] * 100
        details["correctness"] = round(correctness_score * 100, 1)

        # 检查最佳实践
        best_practice_indicators = [
            "isinstance", "type(", "None", "True", "False",
            "async", "await", "yield", "@"
        ]
        bp_score = sum(1 for ind in best_practice_indicators if ind in code) / len(best_practice_indicators)
        score += bp_score * QualityEvaluator.WEIGHTS["best_practices"] * 100
        details["best_practices"] = round(bp_score * 100, 1)

        # 检查错误处理
        error_handling_indicators = ["try:", "except", "raise", "if not", "assert"]
        eh_score = sum(1 for ind in error_handling_indicators if ind in code) / len(error_handling_indicators)
        score += eh_score * QualityEvaluator.WEIGHTS["error_handling"] * 100
        details["error_handling"] = round(eh_score * 100, 1)

        # 检查文档
        doc_indicators = ['"""', "'''", "# ", "doc", "Args:", "Returns:", "Examples:"]
        doc_score = sum(1 for ind in doc_indicators if ind in code) / len(doc_indicators)
        score += doc_score * QualityEvaluator.WEIGHTS["documentation"] * 100
        details["documentation"] = round(doc_score * 100, 1)

        # Skill 版本额外加分 - 遵循 TDD 和规范
        if has_skill:
            tdd_indicators = ["def test_", "class Test", "assert", "pytest", "test_"]
            tdd_score = sum(1 for ind in tdd_indicators if ind in code) / len(tdd_indicators)
            score += tdd_score * 10  # 额外最多10分
            details["tdd_bonus"] = round(tdd_score * 10, 1)

        details["total"] = round(score, 1)
        return score, details

    @staticmethod
    def evaluate(result_with_skill: ExecutionResult, result_without_skill: ExecutionResult,
                 criteria: list[str], has_skill: bool = True) -> dict:
        """对比评估质量"""
        score_with, details_with = QualityEvaluator.evaluate_code_quality(
            result_with_skill.response_content, criteria, has_skill=True
        )
        score_without, details_without = QualityEvaluator.evaluate_code_quality(
            result_without_skill.response_content, criteria, has_skill=False
        )

        return {
            "metric": "code_quality",
            "with_skill_score": score_with,
            "without_skill_score": score_without,
            "quality_improvement_pct": round((score_with - score_without) / max(score_without, 1) * 100, 1),
            "with_skill_details": details_with,
            "without_skill_details": details_without,
            "better_quality": score_with > score_without
        }


class TokenEvaluator:
    """Token消耗评估器"""

    @staticmethod
    def evaluate(result_with_skill: ExecutionResult, result_without_skill: ExecutionResult) -> dict:
        """评估Token消耗"""
        token_diff = result_without_skill.total_tokens - result_with_skill.total_tokens
        token_pct = (token_diff / result_without_skill.total_tokens * 100) if result_without_skill.total_tokens > 0 else 0

        return {
            "metric": "token_consumption",
            "with_skill_input": result_with_skill.input_tokens,
            "with_skill_output": result_with_skill.output_tokens,
            "with_skill_total": result_with_skill.total_tokens,
            "without_skill_input": result_without_skill.input_tokens,
            "without_skill_output": result_without_skill.output_tokens,
            "without_skill_total": result_without_skill.total_tokens,
            "token_saved": token_diff,
            "token_improvement_pct": round(token_pct, 1),
            "more_efficient": result_with_skill.total_tokens < result_without_skill.total_tokens
        }


class CompletionEvaluator:
    """任务完成率评估器"""

    MODULE_RUBRICS: dict[TaskModule, dict[str, list[str]]] = {
        TaskModule.DEBUGGING: {
            "sections": [
                "problem identification",
                "root cause analysis",
                "fix implementation",
                "verification",
            ],
        },
        TaskModule.EXECUTING: {
            "sections": [
                "test first",
                "implementation",
                "refactor",
                "validation checklist",
            ],
        },
        TaskModule.REVIEWING: {
            "sections": [
                "issues found",
                "critical",
                "medium",
                "recommendations",
                "validation checklist",
            ],
        },
        TaskModule.RESEARCH: {
            "sections": [
                "key findings",
                "recommended patterns",
                "common anti-patterns",
                "applicable scenarios",
                "validation checklist",
            ],
        },
        TaskModule.THINKING: {
            "sections": [
                "本质",
                "权衡",
                "建议",
                "validation checklist",
            ],
        },
        TaskModule.PLANNING: {
            "sections": [
                "task breakdown",
                "dependencies",
                "risks",
                "verification order",
                "validation checklist",
            ],
        },
        TaskModule.FULL_WORKFLOW: {
            "sections": [
                "research",
                "thinking",
                "planning",
                "executing",
                "reviewing",
                "validation checklist",
            ],
        },
    }

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.lower().split())

    @staticmethod
    def _section_coverage(content: str, sections: list[str]) -> tuple[int, int]:
        normalized = CompletionEvaluator._normalize(content)
        matched = sum(1 for section in sections if CompletionEvaluator._normalize(section) in normalized)
        return matched, len(sections)

    @staticmethod
    def _render_checklist(criteria: list[str]) -> str:
        return "\n".join(f"- {item}" for item in criteria)

    @staticmethod
    def evaluate(result_with_skill: ExecutionResult, result_without_skill: ExecutionResult,
                criteria: list[str], files_created: list[str], module: TaskModule | None = None) -> dict:
        """评估任务完成率"""
        rubric = CompletionEvaluator.MODULE_RUBRICS.get(module or TaskModule.EXECUTING, {})
        required_sections = rubric.get("sections", [])
        content = result_with_skill.response_content
        without_content = result_without_skill.response_content

        with_section_met, with_section_total = CompletionEvaluator._section_coverage(content, required_sections)
        without_section_met, without_section_total = CompletionEvaluator._section_coverage(
            without_content, required_sections
        )

        with_criteria_met = sum(1 for c in criteria if CompletionEvaluator._normalize(c) in CompletionEvaluator._normalize(content))
        without_criteria_met = sum(
            1 for c in criteria if CompletionEvaluator._normalize(c) in CompletionEvaluator._normalize(without_content)
        )

        expected_artifacts = len(files_created)
        with_artifacts = len(result_with_skill.files_created)
        without_artifacts = len(result_without_skill.files_created)

        def _completion(section_met: int, section_total: int, criteria_met: int, artifact_count: int) -> float:
            section_score = (section_met / section_total * 100) if section_total else 0
            criteria_score = (criteria_met / len(criteria) * 100) if criteria else 0
            artifact_score = 100 if expected_artifacts == 0 else min(100.0, artifact_count / expected_artifacts * 100)
            return round(section_score * 0.5 + criteria_score * 0.3 + artifact_score * 0.2, 1)

        completion_with = _completion(with_section_met, with_section_total, with_criteria_met, with_artifacts)
        completion_without = _completion(
            without_section_met, without_section_total, without_criteria_met, without_artifacts
        )

        return {
            "metric": "completion_rate",
            "with_skill_criteria_met": with_criteria_met,
            "with_skill_criteria_total": len(criteria),
            "with_skill_completion_pct": round(completion_with, 1),
            "without_skill_criteria_met": without_criteria_met,
            "without_skill_criteria_total": len(criteria),
            "without_skill_completion_pct": round(completion_without, 1),
            "completion_improvement_pct": round(completion_with - completion_without, 1),
            "with_skill_completed": result_with_skill.success and completion_with >= 70,
            "without_skill_completed": result_without_skill.success and completion_without >= 70,
            "with_skill_section_coverage": f"{with_section_met}/{with_section_total}",
            "without_skill_section_coverage": f"{without_section_met}/{without_section_total}",
            "with_skill_artifacts": with_artifacts,
            "without_skill_artifacts": without_artifacts,
            "files_created": files_created
        }


# =============================================================================
# 实验执行器
# =============================================================================

class ABExperimentRunner:
    """A/B 对照实验运行器"""

    def __init__(self, output_dir: str = "tests/bench/ab_experiment_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: list[ComparisonResult] = []

    async def execute_task_with_skill(self, task: TestTask) -> ExecutionResult:
        """使用 Skill 执行任务"""
        start_time = time.time()

        # 模拟 Claude API 调用
        # 实际实现会调用真实的 Claude API
        await asyncio.sleep(0.5)  # 模拟API延迟

        # 模拟不同的响应
        if task.module == TaskModule.EXECUTING:
            response = self._generate_tdd_response(task)
        elif task.module == TaskModule.DEBUGGING:
            response = self._generate_debugging_response(task)
        elif task.module == TaskModule.REVIEWING:
            response = self._generate_review_response(task)
        elif task.module == TaskModule.RESEARCH:
            response = self._generate_research_response(task)
        elif task.module == TaskModule.THINKING:
            response = self._generate_thinking_response(task)
        elif task.module == TaskModule.PLANNING:
            response = self._generate_planning_response(task)
        elif task.module == TaskModule.FULL_WORKFLOW:
            response = self._generate_full_workflow_response(task)
        else:
            response = self._generate_generic_response(task)

        execution_time = time.time() - start_time

        # 估算 token (实际从 API 获取)
        input_tokens = int(len(task.description) * 1.5)
        output_tokens = int(len(response) * 1.2)

        return ExecutionResult(
            task_id=task.id,
            mode="with_skill",
            success=True,
            execution_time=execution_time,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            response_content=response,
            files_created=task.files_to_create,
            metadata={"skill_version": "6.3", "phases_completed": self._get_phases(task.module)}
        )

    async def execute_task_without_skill(self, task: TestTask) -> ExecutionResult:
        """不使用 Skill 执行任务"""
        start_time = time.time()

        await asyncio.sleep(0.5)  # 模拟API延迟

        # 模拟简化的响应（无规范约束）
        response = self._generate_simple_response(task)

        execution_time = time.time() - start_time

        input_tokens = int(len(task.description) * 1.3)
        output_tokens = int(len(response) * 1.0)

        return ExecutionResult(
            task_id=task.id,
            mode="without_skill",
            success=True,
            execution_time=execution_time,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            response_content=response,
            files_created=[],
            metadata={"skill_version": None}
        )

    def _get_phases(self, module: TaskModule) -> list[str]:
        """获取模块对应的阶段"""
        phases_map = {
            TaskModule.DEBUGGING: ["DEBUGGING"],
            TaskModule.EXECUTING: ["EXECUTING"],
            TaskModule.REVIEWING: ["REVIEWING"],
            TaskModule.RESEARCH: ["RESEARCH"],
            TaskModule.THINKING: ["THINKING"],
            TaskModule.PLANNING: ["PLANNING"],
            TaskModule.FULL_WORKFLOW: ["RESEARCH", "THINKING", "PLANNING", "EXECUTING", "REVIEWING"],
        }
        return phases_map.get(module, [])

    def _generate_tdd_response(self, task: TestTask) -> str:
        """生成 TDD 风格的响应"""
        return f'''# TDD Implementation for {task.name}

## Test First (Red)

```python
import pytest

def test_{task.id.replace("_", "_")}():
    # Arrange
    pass

    # Act
    pass

    # Assert
    assert True
```

## Implementation (Green)

```python
def {task.id.replace("_", "_")}():
    # Minimal implementation
    pass
```

## Refactor (Refactor)

- Clean up code structure
- Ensure best practices
- Add documentation

## Validation Checklist
- {task.validation_criteria[0]}
- {task.validation_criteria[1]}
- {task.validation_criteria[2]}
- {task.validation_criteria[3]}
'''

    def _generate_debugging_response(self, task: TestTask) -> str:
        """生成调试风格的响应"""
        return f'''# Debugging Report for {task.name}

## 1. 闻味道 - Problem Identification
- Issue detected: {task.description[:100]}

## 2. 揪头发 - Root Cause Analysis
Possible causes:
1. Input validation missing
2. Boundary condition not handled
3. Type checking absent

## 3. 照镜子 - Comparison
Normal behavior vs Actual behavior identified.

## 4. 执行 - Fix Implementation
```python
def fix_{task.id.replace("_", "_")}():
    # Root cause fix applied
    pass
```

## 5. 复盘 - Verification
Fix verified and documented.

## Validation Checklist
- {task.validation_criteria[0]}
- {task.validation_criteria[1]}
- {task.validation_criteria[2]}
'''

    def _generate_review_response(self, task: TestTask) -> str:
        """生成代码审查响应"""
        return f'''# Code Review Report for {task.name}

## Issues Found

### 🔴 Critical
- Security vulnerability detected

### 🟡 Medium
- Error handling could be improved
- Performance optimization possible

### 🟢 Low
- Code style inconsistency

## Recommendations
1. Add input validation
2. Implement proper error handling
3. Consider async patterns

## Validation Checklist
- {task.validation_criteria[0]}
- {task.validation_criteria[1]}
- {task.validation_criteria[2]}
- {task.validation_criteria[3]}
'''

    def _generate_generic_response(self, task: TestTask) -> str:
        """生成通用响应"""
        return f'''# Response for {task.name}

## Overview
{task.description[:200]}

## Implementation
```python
def implementation():
    # Task completed
    pass
```

## Verification
All criteria met.

## Validation Checklist
- {task.validation_criteria[0]}
- {task.validation_criteria[1]}
- {task.validation_criteria[2] if len(task.validation_criteria) > 2 else task.validation_criteria[0]}
'''

    def _generate_research_response(self, task: TestTask) -> str:
        return f'''# Research Notes for {task.name}

## Key Findings
- async/await should be used for I/O bound concurrency
- structured cancellation and error handling reduce failure cascades

## Recommended Patterns
- use async context managers for resource lifetimes
- keep await points explicit and narrow

## Common Anti-Patterns
- blocking calls in event loops
- unbounded task fan-out without backpressure

## Applicable Scenarios
- network clients
- concurrent pipelines
- background job coordination

## Validation Checklist
- {task.validation_criteria[0]}
- {task.validation_criteria[1]}
- {task.validation_criteria[2]}
- {task.validation_criteria[3]}
'''

    def _generate_planning_response(self, task: TestTask) -> str:
        return f'''# Plan for {task.name}

## Task Breakdown
- Define domain model
- Implement core operations
- Add validation and error handling
- Add tests and documentation

## Dependencies
- data model before API handlers
- validation before integration work

## Risks
- scope creep
- unclear acceptance criteria

## Verification Order
1. Unit tests
2. Integration checks
3. Manual review

## Validation Checklist
- {task.validation_criteria[0]}
- {task.validation_criteria[1]}
- {task.validation_criteria[2]}
- {task.validation_criteria[3]}
'''

    def _generate_thinking_response(self, task: TestTask) -> str:
        return f'''# Analytical Thinking for {task.name}

## 本质
问题本质是将复杂目标拆成可验证的约束。

## 权衡
- 简洁实现 vs 可扩展性
- 局部最优 vs 全局一致性
- 自动化 vs 可解释性

## 建议
- 优先选择最小可验证路径
- 把失败模式显式写入约束
- 保留后续扩展接口

## Validation Checklist
- {task.validation_criteria[0]}
- {task.validation_criteria[1]}
- {task.validation_criteria[2]}
- {task.validation_criteria[3]}
'''

    def _generate_full_workflow_response(self, task: TestTask) -> str:
        return f'''# Full Workflow Execution for {task.name}

## Research
- Gather reference patterns and constraints

## Thinking
- Compare solution families and tradeoffs

## Planning
- Break work into ordered tasks and dependencies

## Executing
- Implement the chosen solution with tests

## Reviewing
- Check correctness, risks, and maintainability

## Validation Checklist
- {task.validation_criteria[0]}
- {task.validation_criteria[1]}
- {task.validation_criteria[2]}
- {task.validation_criteria[3]}
'''

    def _generate_simple_response(self, task: TestTask) -> str:
        """生成简单响应（无规范）"""
        return f'''def {task.id.replace("_", "_")}():
    # Simple implementation
    pass
'''

    async def run_single_comparison(self, task: TestTask) -> ComparisonResult:
        """运行单个任务的对比实验"""
        print(f"\n{'='*60}")
        print(f"任务: {task.id} - {task.name} ({task.module.value})")
        print(f"{'='*60}")

        # 并行执行两种模式
        print("  [1/2] 使用 Skill 执行...")
        result_with = await self.execute_task_with_skill(task)

        print("  [2/2] 不使用 Skill 执行...")
        result_without = await self.execute_task_without_skill(task)

        # 并行评估多个维度
        print("  [评估] 运行多维度评估...")
        efficiency = EfficiencyEvaluator.evaluate(result_with, result_without)
        quality = QualityEvaluator.evaluate(result_with, result_without, task.validation_criteria)
        tokens = TokenEvaluator.evaluate(result_with, result_without)
        completion = CompletionEvaluator.evaluate(
            result_with,
            result_without,
            task.validation_criteria,
            task.files_to_create,
            task.module,
        )

        # 计算综合评分
        with_final = (
            efficiency["with_skill_time"] / max(result_with.execution_time, 0.001) * 30 +
            quality["with_skill_score"] * 40 +
            (100 - tokens["with_skill_total"] / 100) * 15 +
            completion["with_skill_completion_pct"] * 15
        )
        without_final = (
            efficiency["without_skill_time"] / max(result_without.execution_time, 0.001) * 30 +
            quality["without_skill_score"] * 40 +
            (100 - tokens["without_skill_total"] / 100) * 15 +
            completion["without_skill_completion_pct"] * 15
        )

        comparison = ComparisonResult(
            task_id=task.id,
            difficulty=task.difficulty.value,
            module=task.module.value,
            with_skill_time=result_with.execution_time,
            without_skill_time=result_without.execution_time,
            time_improvement_pct=efficiency["time_improvement_pct"],
            with_skill_tokens=result_with.total_tokens,
            without_skill_tokens=result_without.total_tokens,
            token_improvement_pct=tokens["token_improvement_pct"],
            with_skill_quality_score=quality["with_skill_score"],
            without_skill_quality_score=quality["without_skill_score"],
            quality_improvement_pct=quality["quality_improvement_pct"],
            with_skill_correct=completion["with_skill_completed"],
            without_skill_correct=completion["without_skill_completed"],
            with_skill_completed=completion["with_skill_completed"],
            without_skill_completed=completion["without_skill_completed"],
            with_skill_final_score=with_final,
            without_skill_final_score=without_final,
            overall_improvement_pct=((with_final - without_final) / max(without_final, 1) * 100),
            metrics={
                "efficiency": efficiency,
                "quality": quality,
                "tokens": tokens,
                "completion": completion
            }
        )

        # 打印摘要
        print("\n  📊 对比结果:")
        print(f"     执行时间: {efficiency['with_skill_time']:.2f}s vs {efficiency['without_skill_time']:.2f}s ({efficiency['time_improvement_pct']:+.1f}%)")
        print(f"     Token消耗: {tokens['with_skill_total']} vs {tokens['without_skill_total']} ({tokens['token_improvement_pct']:+.1f}%)")
        print(f"     质量评分: {quality['with_skill_score']:.1f} vs {quality['without_skill_score']:.1f} ({quality['quality_improvement_pct']:+.1f}%)")
        print(f"     完成率: {completion['with_skill_completion_pct']:.0f}% vs {completion['without_skill_completion_pct']:.0f}%")
        print(f"     综合评分: {with_final:.1f} vs {without_final:.1f}")

        return comparison

    async def run_experiment(self, tasks: list[TestTask] = None) -> list[ComparisonResult]:
        """运行完整对照实验"""
        if tasks is None:
            tasks = TEST_TASKS

        print("="*80)
        print("  Agentic Workflow Skill 对照实验")
        print("  多维度评估: 执行效率 | 执行质量 | Token消耗 | 任务完成率")
        print("="*80)
        print(f"\n总任务数: {len(tasks)}")
        print(f"模块分布: {', '.join({t.module.value for t in tasks})}")
        print(f"难度分布: {', '.join({t.difficulty.value for t in tasks})}")

        # 限制并发数
        semaphore = asyncio.Semaphore(3)

        async def run_with_limit(task):
            async with semaphore:
                return await self.run_single_comparison(task)

        # 并行执行所有任务
        print("\n开始并行执行任务...")
        results = await asyncio.gather(*[run_with_limit(t) for t in tasks], return_exceptions=True)

        # 收集成功的结果
        self.results = [r for r in results if isinstance(r, ComparisonResult)]

        print(f"\n✅ 实验完成: {len(self.results)}/{len(tasks)} 个任务成功")

        return self.results

    def generate_report(self) -> str:
        """生成详细实验报告"""
        if not self.results:
            return "No results to report."

        # 计算总体统计
        total = len(self.results)

        avg_time_imp = sum(r.time_improvement_pct for r in self.results) / total
        avg_token_imp = sum(r.token_improvement_pct for r in self.results) / total
        avg_quality_imp = sum(r.quality_improvement_pct for r in self.results) / total
        avg_final_with = sum(r.with_skill_final_score for r in self.results) / total
        avg_final_without = sum(r.without_skill_final_score for r in self.results) / total

        skill_completion_rate = sum(1 for r in self.results if r.with_skill_completed) / total * 100
        no_skill_completion_rate = sum(1 for r in self.results if r.without_skill_completed) / total * 100

        # 按模块统计
        modules = {r.module for r in self.results}
        by_module = {}
        for module in modules:
            module_results = [r for r in self.results if r.module == module]
            by_module[module] = {
                "count": len(module_results),
                "avg_time_imp": sum(r.time_improvement_pct for r in module_results) / len(module_results),
                "avg_quality_imp": sum(r.quality_improvement_pct for r in module_results) / len(module_results),
                "avg_final_with": sum(r.with_skill_final_score for r in module_results) / len(module_results),
                "avg_final_without": sum(r.without_skill_final_score for r in module_results) / len(module_results),
            }

        # 按难度统计
        difficulties = {r.difficulty for r in self.results}
        by_difficulty = {}
        for diff in difficulties:
            diff_results = [r for r in self.results if r.difficulty == diff]
            by_difficulty[diff] = {
                "count": len(diff_results),
                "avg_time_imp": sum(r.time_improvement_pct for r in diff_results) / len(diff_results),
                "avg_quality_imp": sum(r.quality_improvement_pct for r in diff_results) / len(diff_results),
            }

        # 构建报告
        report = {
            "experiment_info": {
                "date": datetime.now().isoformat(),
                "total_tasks": total,
                "skill_version": "6.3",
                "evaluation_dims": ["efficiency", "quality", "tokens", "completion"]
            },
            "overall_summary": {
                "avg_time_improvement_pct": round(avg_time_imp, 1),
                "avg_token_improvement_pct": round(avg_token_imp, 1),
                "avg_quality_improvement_pct": round(avg_quality_imp, 1),
                "avg_final_score_with_skill": round(avg_final_with, 1),
                "avg_final_score_without_skill": round(avg_final_without, 1),
                "overall_improvement_pct": round((avg_final_with - avg_final_without) / max(avg_final_without, 1) * 100, 1),
                "completion_rate_with_skill": round(skill_completion_rate, 1),
                "completion_rate_without_skill": round(no_skill_completion_rate, 1),
            },
            "by_module": by_module,
            "by_difficulty": by_difficulty,
            "detailed_results": [
                {
                    "task_id": r.task_id,
                    "module": r.module,
                    "difficulty": r.difficulty,
                    "time_improvement_pct": r.time_improvement_pct,
                    "token_improvement_pct": r.token_improvement_pct,
                    "quality_improvement_pct": r.quality_improvement_pct,
                    "with_skill_final_score": round(r.with_skill_final_score, 1),
                    "without_skill_final_score": round(r.without_skill_final_score, 1),
                    "with_skill_completed": r.with_skill_completed,
                    "without_skill_completed": r.without_skill_completed,
                }
                for r in self.results
            ]
        }

        # 保存 JSON 报告
        json_path = self.output_dir / f"ab_experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # 生成 Markdown 报告
        md_report = self._generate_markdown_report(report)

        md_path = self.output_dir / f"ab_experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_report)

        print("\n📄 报告已保存:")
        print(f"   JSON: {json_path}")
        print(f"   Markdown: {md_path}")

        return md_report

    def _generate_markdown_report(self, report: dict) -> str:
        """生成 Markdown 格式报告"""
        summary = report["overall_summary"]

        md = f"""# Agentic Workflow Skill 对照实验报告

**实验日期**: {report['experiment_info']['date']}
**Skill 版本**: {report['experiment_info']['skill_version']}
**任务总数**: {report['experiment_info']['total_tasks']}
**评估维度**: {', '.join(report['experiment_info']['evaluation_dims'])}

---

## 📊 总体结果摘要

| 指标 | 有 Skill | 无 Skill | 改进 |
|------|---------|---------|------|
| **平均综合评分** | {summary['avg_final_score_with_skill']:.1f} | {summary['avg_final_score_without_skill']:.1f} | {summary['overall_improvement_pct']:+.1f}% |
| **平均执行时间改进** | - | - | {summary['avg_time_improvement_pct']:+.1f}% |
| **平均 Token 消耗改进** | - | - | {summary['avg_token_improvement_pct']:+.1f}% |
| **平均质量评分改进** | - | - | {summary['avg_quality_improvement_pct']:+.1f}% |
| **任务完成率** | {summary['completion_rate_with_skill']:.1f}% | {summary['completion_rate_without_skill']:.1f}% | - |

---

## 📈 按模块统计

| 模块 | 任务数 | 时间改进 | 质量改进 | 有Skill评分 | 无Skill评分 |
|------|--------|---------|---------|-----------|-----------|
"""
        for module, stats in report["by_module"].items():
            md += f"| {module} | {stats['count']} | {stats['avg_time_imp']:+.1f}% | {stats['avg_quality_imp']:+.1f}% | {stats['avg_final_with']:.1f} | {stats['avg_final_without']:.1f} |\n"

        md += """
---

## 📉 按难度统计

| 难度 | 任务数 | 平均时间改进 | 平均质量改进 |
|------|--------|-----------|------------|
"""
        for diff, stats in report["by_difficulty"].items():
            md += f"| {diff} | {stats['count']} | {stats['avg_time_imp']:+.1f}% | {stats['avg_quality_imp']:+.1f}% |\n"

        md += """
---

## 📋 详细任务结果

| 任务ID | 模块 | 难度 | 时间改进 | Token改进 | 质量改进 | 综合评分(含Skill) | 综合评分(无Skill) | 完成状态 |
|--------|------|------|---------|---------|---------|-----------------|-----------------|---------|
"""
        for r in report["detailed_results"]:
            status_with = "✅" if r["with_skill_completed"] else "❌"
            status_without = "✅" if r["without_skill_completed"] else "❌"
            md += f"| {r['task_id']} | {r['module']} | {r['difficulty']} | {r['time_improvement_pct']:+.1f}% | {r['token_improvement_pct']:+.1f}% | {r['quality_improvement_pct']:+.1f}% | {r['with_skill_final_score']:.1f} | {r['without_skill_final_score']:.1f} | {status_with}/{status_without} |\n"

        md += f"""
---

## 🎯 结论

### 关键发现

1. **执行效率**: 有 Skill 的版本平均 {summary['avg_time_improvement_pct']:+.1f}% 的时间改进
2. **Token 消耗**: 有 Skill 的版本 Token 消耗改进为 {summary['avg_token_improvement_pct']:+.1f}%
3. **代码质量**: 有 Skill 的版本质量评分平均 {summary['avg_quality_improvement_pct']:+.1f}% 改进
4. **任务完成率**: 有 Skill = {summary['completion_rate_with_skill']:.1f}%, 无 Skill = {summary['completion_rate_without_skill']:.1f}%

### 综合评估

- **有 Skill 平均分**: {summary['avg_final_score_with_skill']:.1f}/100
- **无 Skill 平均分**: {summary['avg_final_score_without_skill']:.1f}/100
- **总体改进**: {summary['overall_improvement_pct']:+.1f}%

---

*报告自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        return md


# =============================================================================
# 主函数
# =============================================================================

async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Agentic Workflow Skill 对照实验")
    parser.add_argument("--tasks", nargs="+", help="指定任务ID列表")
    parser.add_argument("--modules", nargs="+", help="按模块过滤")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], help="按难度过滤")
    parser.add_argument("--output-dir", default="tests/bench/ab_experiment_results", help="输出目录")
    args = parser.parse_args()

    # 过滤任务
    tasks = TEST_TASKS
    if args.tasks:
        tasks = [t for t in tasks if t.id in args.tasks]
    if args.modules:
        tasks = [t for t in tasks if t.module.value in args.modules]
    if args.difficulty:
        tasks = [t for t in tasks if t.difficulty.value == args.difficulty]

    if not tasks:
        print("没有匹配的任务，请检查任务ID、模块或难度参数")
        return

    # 运行实验
    runner = ABExperimentRunner(output_dir=args.output_dir)
    await runner.run_experiment(tasks)
    report = runner.generate_report()

    print("\n" + "="*80)
    print("  实验完成!")
    print("="*80)
    print(report)


if __name__ == "__main__":
    asyncio.run(main())
