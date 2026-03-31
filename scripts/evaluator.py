#!/usr/bin/env python3
"""
Workflow Evaluator - Generator-Evaluator 模式

借鉴 Anthropic Harness Design 最佳实践:

1. Generator-Evaluator Pattern
   - Generator: 生成输出
   - Evaluator: 严格评估 + 评分

2. Sprint Contracts
   - 预协商的成功标准
   - Generator 和 Evaluator 之间的契约

3. Grading Rubrics
   - 可量化的评分标准
   - 明确的拒绝阈值

用法:
    from evaluator import WorkflowEvaluator, SprintContract, EvaluationResult

    evaluator = WorkflowEvaluator()
    result = evaluator.evaluate(output, contract)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# Grading Criteria
# ============================================================================

class QualityCriteria(Enum):
    """质量评估标准"""
    DESIGN = "design"           # 设计一致性
    ORIGINALITY = "originality" # 原创性
    CRAFT = "craft"           # 技术实现
    FUNCTIONALITY = "functionality"  # 功能性
    COMPLETENESS = "completeness"  # 完整性
    CORRECTNESS = "correctness"  # 正确性


@dataclass
class GradingRubric:
    """评分规则"""
    criteria: QualityCriteria
    weight: float  # 权重 (0-1)
    description: str
    check_questions: List[str]  # 检查问题列表
    penalty_patterns: List[str]  # 扣分模式


# 默认评分规则
DEFAULT_RUBRICS = [
    GradingRubric(
        criteria=QualityCriteria.DESIGN,
        weight=0.2,
        description="架构设计一致性",
        check_questions=[
            "模块划分是否清晰？",
            "接口设计是否一致？",
            "是否有明显的架构异味？",
        ],
        penalty_patterns=[
            "重复代码",
            "上帝类",
            "循环依赖",
        ],
    ),
    GradingRubric(
        criteria=QualityCriteria.ORIGINALITY,
        weight=0.15,
        description="原创性",
        check_questions=[
            "是否使用模板而非定制？",
            "是否有明显的AI生成痕迹？",
        ],
        penalty_patterns=[
            "模板代码",
            "通用占位符",
            "缺乏具体业务逻辑",
        ],
    ),
    GradingRubric(
        criteria=QualityCriteria.CRAFT,
        weight=0.2,
        description="技术实现质量",
        check_questions=[
            "代码格式是否一致？",
            "命名是否规范？",
            "是否有适当的注释？",
        ],
        penalty_patterns=[
            "不一致的格式",
            "无意义的变量名",
            "硬编码",
        ],
    ),
    GradingRubric(
        criteria=QualityCriteria.FUNCTIONALITY,
        weight=0.25,
        description="功能性",
        check_questions=[
            "功能是否完整？",
            "边界条件是否处理？",
            "错误处理是否得当？",
        ],
        penalty_patterns=[
            "功能缺失",
            "崩溃",
            "无限循环",
        ],
    ),
    GradingRubric(
        criteria=QualityCriteria.COMPLETENESS,
        weight=0.1,
        description="完整性",
        check_questions=[
            "所有需求是否覆盖？",
            "文档是否完整？",
        ],
        penalty_patterns=[
            "TODO注释",
            "未完成的功能",
            "缺少文档",
        ],
    ),
    GradingRubric(
        criteria=QualityCriteria.CORRECTNESS,
        weight=0.1,
        description="正确性",
        check_questions=[
            "逻辑是否正确？",
            "测试是否通过？",
        ],
        penalty_patterns=[
            "逻辑错误",
            "测试失败",
            "类型错误",
        ],
    ),
]


# ============================================================================
# Sprint Contract
# ============================================================================

@dataclass
class SprintContract:
    """
    Sprint契约

    Generator 和 Evaluator 之间的预协商协议
    """
    task_id: str
    task_description: str
    generator_commitments: List[str]  # Generator 承诺的实现
    evaluator_criteria: List[str]  # Evaluator 的评估标准
    rejection_threshold: float  # 拒绝阈值 (0-1)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    negotiated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_description": self.task_description,
            "generator_commitments": self.generator_commitments,
            "evaluator_criteria": self.evaluator_criteria,
            "rejection_threshold": self.rejection_threshold,
            "created_at": self.created_at,
            "negotiated": self.negotiated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SprintContract":
        return cls(
            task_id=data["task_id"],
            task_description=data["task_description"],
            generator_commitments=data["generator_commitments"],
            evaluator_criteria=data["evaluator_criteria"],
            rejection_threshold=data["rejection_threshold"],
            created_at=data.get("created_at", datetime.now().isoformat()),
            negotiated=data.get("negotiated", False),
        )


# ============================================================================
# Evaluation Result
# ============================================================================

class EvaluationStatus(Enum):
    """评估状态"""
    PASS = "pass"
    FAIL = "fail"
    NEED_REVISION = "need_revision"
    PARTIAL = "partial"


@dataclass
class CriteriaScore:
    """单标准评分"""
    criteria: QualityCriteria
    score: float  # 0-1
    feedback: List[str]  # 反馈列表
    issues: List[str]  # 问题列表


@dataclass
class EvaluationResult:
    """评估结果"""
    status: EvaluationStatus
    overall_score: float  # 0-1
    criteria_scores: List[CriteriaScore]
    feedback: str  # 总体反馈
    issues: List[str]  # 问题列表
    recommendations: List[str]  # 建议
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "overall_score": self.overall_score,
            "criteria_scores": [
                {
                    "criteria": cs.criteria.value,
                    "score": cs.score,
                    "feedback": cs.feedback,
                    "issues": cs.issues,
                }
                for cs in self.criteria_scores
            ],
            "feedback": self.feedback,
            "issues": self.issues,
            "recommendations": self.recommendations,
            "evaluated_at": self.evaluated_at,
        }

    def is_acceptable(self, threshold: float = 0.7) -> bool:
        """检查是否可接受"""
        return self.overall_score >= threshold and self.status != EvaluationStatus.FAIL


# ============================================================================
# Workflow Evaluator
# ============================================================================

class WorkflowEvaluator:
    """
    工作流评估器

    Generator-Evaluator 模式的核心组件

    功能:
    - 严格评估输出
    - 基于契约的评分
    - 详细的反馈和建议
    """

    def __init__(
        self,
        rubrics: Optional[List[GradingRubric]] = None,
        default_threshold: float = 0.7,
    ):
        self.rubrics = rubrics or DEFAULT_RUBRICS
        self.default_threshold = default_threshold

    def evaluate(
        self,
        output: Dict[str, Any],
        contract: Optional[SprintContract] = None,
    ) -> EvaluationResult:
        """
        评估输出

        Args:
            output: 待评估的输出
            contract: 可选的契约

        Returns:
            EvaluationResult
        """
        criteria_scores = []
        all_issues = []
        all_feedback = []

        for rubric in self.rubrics:
            score, feedback, issues = self._evaluate_criteria(output, rubric)
            criteria_scores.append(CriteriaScore(
                criteria=rubric.criteria,
                score=score,
                feedback=feedback,
                issues=issues,
            ))
            all_issues.extend(issues)
            all_feedback.extend(feedback)

        # 计算加权总分
        overall_score = sum(
            cs.score * r.weight
            for cs, r in zip(criteria_scores, self.rubrics)
        )

        # 判断状态
        threshold = contract.rejection_threshold if contract else self.default_threshold
        if overall_score >= threshold:
            if all_issues:
                status = EvaluationStatus.NEED_REVISION
            else:
                status = EvaluationStatus.PASS
        else:
            status = EvaluationStatus.FAIL

        return EvaluationResult(
            status=status,
            overall_score=overall_score,
            criteria_scores=criteria_scores,
            feedback="\n".join(all_feedback),
            issues=all_issues,
            recommendations=self._generate_recommendations(criteria_scores),
        )

    def _evaluate_criteria(
        self,
        output: Dict[str, Any],
        rubric: GradingRubric,
    ) -> Tuple[float, List[str], List[str]]:
        """
        评估单个标准

        Returns:
            (score, feedback, issues)
        """
        score = 1.0  # 假设完美
        feedback = []
        issues = []

        output_str = json.dumps(output, ensure_ascii=False).lower()

        # 检查惩罚模式
        for pattern in rubric.penalty_patterns:
            if pattern.lower() in output_str:
                score -= 0.2
                issues.append(f"[{rubric.criteria.value}] 发现问题: {pattern}")

        # 确保分数在合理范围
        score = max(0.0, min(1.0, score))

        # 生成反馈
        if issues:
            feedback.append(f"❌ [{rubric.criteria.value}] {rubric.description}: {len(issues)} 个问题")
        else:
            feedback.append(f"✅ [{rubric.criteria.value}] {rubric.description}: 通过")

        return score, feedback, issues

    def _generate_recommendations(self, criteria_scores: List[CriteriaScore]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        for cs in criteria_scores:
            if cs.score < 0.7:
                rec = f"改进 {cs.criteria.value}: "
                rec += "; ".join(f"修复 {issue}" for issue in cs.issues[:2])
                recommendations.append(rec)

        if not recommendations:
            recommendations.append("整体质量良好，继续保持")

        return recommendations

    def evaluate_and_decide(
        self,
        output: Dict[str, Any],
        contract: Optional[SprintContract] = None,
    ) -> Tuple[EvaluationResult, bool]:
        """
        评估并决定是否接受

        Returns:
            (result, should_accept)
        """
        result = self.evaluate(output, contract)
        should_accept = result.is_acceptable(
            contract.rejection_threshold if contract else self.default_threshold
        )
        return result, should_accept


# ============================================================================
# Contract Negotiator
# ============================================================================

class ContractNegotiator:
    """
    契约协商器

    在 Generator 和 Evaluator 之间协商成功标准
    """

    def __init__(self, evaluator: Optional[WorkflowEvaluator] = None):
        self.evaluator = evaluator or WorkflowEvaluator()

    def negotiate(
        self,
        task_description: str,
        generator_spec: str,
        evaluator_spec: Optional[str] = None,
    ) -> SprintContract:
        """
        协商契约

        Args:
            task_description: 任务描述
            generator_spec: Generator 的规格说明
            evaluator_spec: Evaluator 的规格说明 (可选)

        Returns:
            SprintContract
        """
        # 从 Generator spec 提取承诺
        commitments = self._extract_commitments(generator_spec)

        # 从 Evaluator spec 提取标准 (如果提供)
        criteria = self._extract_criteria(evaluator_spec) if evaluator_spec else []

        # 生成标准 (如果未提供)
        if not criteria:
            criteria = self._generate_criteria(task_description)

        return SprintContract(
            task_id=f"contract_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            task_description=task_description,
            generator_commitments=commitments,
            evaluator_criteria=criteria,
            rejection_threshold=0.7,
            negotiated=True,
        )

    def _extract_commitments(self, spec: str) -> List[str]:
        """从规格说明提取承诺"""
        # 简单的行提取
        commitments = []
        for line in spec.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                commitments.append(line.lstrip("-* ").strip())
            elif "：" in line or ":" in line:
                commitments.append(line)
        return commitments if commitments else [spec[:200]]

    def _extract_criteria(self, spec: str) -> List[str]:
        """从 Evaluator 规格提取标准"""
        return self._extract_commitments(spec)

    def _generate_criteria(self, task_description: str) -> List[str]:
        """生成默认标准"""
        return [
            f"功能完整性: 实现 {task_description} 的所有需求",
            "代码质量: 符合 PEP8 和项目规范",
            "测试覆盖: 关键功能有测试",
            "文档完整: 必要的地方有注释和文档",
        ]


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Workflow Evaluator - Generator-Evaluator 模式")
    parser.add_argument("--task-id", help="任务 ID")
    parser.add_argument("--output", help="输出文件 (JSON)")
    parser.add_argument("--threshold", type=float, default=0.7, help="接受阈值")
    parser.add_argument("--negotiate", action="store_true", help="协商契约")
    parser.add_argument("--task-description", help="任务描述")
    parser.add_argument("--generator-spec", help="Generator 规格")
    args = parser.parse_args()

    if args.negotiate:
        if not args.task_description:
            print("错误: --task-description required for negotiation")
            return 1

        negotiator = ContractNegotiator()
        contract = negotiator.negotiate(
            args.task_description,
            args.generator_spec or args.task_description,
        )

        print("协商的契约:")
        print(f"  Task ID: {contract.task_id}")
        print(f"  承诺: {len(contract.generator_commitments)} 项")
        print(f"  标准: {len(contract.evaluator_criteria)} 项")
        print(f"  阈值: {contract.rejection_threshold}")
        print()
        print("承诺:")
        for c in contract.generator_commitments:
            print(f"  - {c}")
        print()
        print("标准:")
        for c in contract.evaluator_criteria:
            print(f"  - {c}")

        return 0

    # 评估模式
    if not args.output:
        print("错误: --output required for evaluation")
        return 1

    output = json.loads(Path(args.output).read_text())

    evaluator = WorkflowEvaluator(default_threshold=args.threshold)
    result = evaluator.evaluate(output)

    print(f"评估结果: {result.status.value}")
    print(f"总分: {result.overall_score:.2f}")
    print()
    print("各项评分:")
    for cs in result.criteria_scores:
        icon = "✅" if cs.score >= 0.7 else "❌"
        print(f"  {icon} {cs.criteria.value}: {cs.score:.2f}")
        for issue in cs.issues:
            print(f"      - {issue}")
    print()
    if result.recommendations:
        print("建议:")
        for rec in result.recommendations:
            print(f"  - {rec}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


from pathlib import Path
