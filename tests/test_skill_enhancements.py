#!/usr/bin/env python3
"""
Tests for P0/P1 skill enhancements:
- P0: THINKING 2-branch evaluation (ToT quantitative scoring + backtrack gate)
- P1: EXECUTING mid-task reflection checkpoint (Reflexion)
- P1: EXECUTING sub-agent output schema validation (AgentSys)
"""

import os
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILLS_DIR = ROOT / "skills"


def _read_skill(name: str) -> str:
    path = SKILLS_DIR / name / "skill.md"
    return path.read_text(encoding="utf-8")


class TestThinkingToTEnhancement(unittest.TestCase):
    """P0: Tree of Thoughts quantitative scoring + backtrack gate."""

    @classmethod
    def setUpClass(cls):
        cls.content = _read_skill("thinking")

    def test_version_bumped(self):
        self.assertIn("version: 1.3.0", self.content)

    def test_has_quantitative_scoring_table(self):
        self.assertIn("量化评分标准", self.content)
        self.assertIn("40%", self.content)
        self.assertIn("30%", self.content)

    def test_has_weighted_score_formula(self):
        self.assertIn("Score(Branch)", self.content)
        self.assertIn("可行性×0.4", self.content)

    def test_has_selection_rule_tie_threshold(self):
        """When two branches score within 1.0, both should be kept."""
        self.assertIn("≤1.0", self.content)
        self.assertIn("两个都保留", self.content)

    def test_has_backtrack_gate_section(self):
        self.assertIn("Step -0.5: 回溯检测", self.content)
        self.assertIn("Backtrack Gate", self.content)

    def test_backtrack_trigger_conditions(self):
        self.assertIn("不可绕过的技术约束", self.content)
        self.assertIn("不可缓解的安全风险", self.content)
        self.assertIn("推翻了 Branch 的核心假设", self.content)

    def test_backtrack_limit(self):
        """Max 2 backtracks before BLOCKED."""
        self.assertIn("最多回溯 2 次", self.content)
        self.assertIn("BLOCKED", self.content)

    def test_backtrack_flow_has_record_step(self):
        self.assertIn("[BACKTRACK]", self.content)

    def test_arxiv_reference(self):
        self.assertIn("2305.10601", self.content)

    def test_tree_of_thoughts_tag(self):
        self.assertIn("tree-of-thoughts", self.content)


class TestExecutingMidTaskReflection(unittest.TestCase):
    """P1: Reflexion mid-task reflection checkpoint."""

    @classmethod
    def setUpClass(cls):
        cls.content = _read_skill("executing")

    def test_version_bumped(self):
        self.assertIn("version: 1.2.0", self.content)

    def test_has_mid_task_reflection_section(self):
        self.assertIn("Mid-Task Reflection Checkpoint", self.content)
        self.assertIn("2303.11366", self.content)

    def test_reflection_uses_causal_search(self):
        self.assertIn("search-causal", self.content)

    def test_reflection_uses_entity_search(self):
        self.assertIn("search-entity", self.content)

    def test_reflection_decision_matrix(self):
        self.assertIn("Signal 精确匹配", self.content)
        self.assertIn("Entity 历史命中", self.content)
        self.assertIn("STOP", self.content)
        self.assertIn("WARNING", self.content)
        self.assertIn("CONTINUE", self.content)

    def test_reflection_output_format(self):
        self.assertIn("因果链匹配", self.content)
        self.assertIn("本次是否已规避", self.content)
        self.assertIn("实体历史", self.content)

    def test_graceful_fallback(self):
        """Memory unavailable should not block execution."""
        self.assertIn("静默跳过", self.content)
        self.assertIn("不阻塞执行流", self.content)

    def test_reflexion_tag(self):
        self.assertIn("reflexion", self.content)


class TestExecutingAgentSysSchemaValidation(unittest.TestCase):
    """P1: AgentSys sub-agent output schema validation."""

    @classmethod
    def setUpClass(cls):
        cls.content = _read_skill("executing")

    def test_has_schema_validation_section(self):
        self.assertIn("子 Agent 输出 Schema 验证", self.content)
        self.assertIn("2602.07398", self.content)

    def test_required_fields(self):
        for field in ["task_id", "status", "files_changed", "test_result"]:
            self.assertIn(f'"{field}"', self.content)

    def test_status_enum_values(self):
        self.assertIn("DONE | DONE_WITH_CONCERNS | FAILED", self.content)

    def test_test_result_enum_values(self):
        self.assertIn("PASS | FAIL | SKIPPED", self.content)

    def test_retry_limit(self):
        """Max 2 retries per sub-task."""
        self.assertIn("最多重派 2 次", self.content)

    def test_raw_data_truncation(self):
        self.assertIn("截断到 500 字符", self.content)

    def test_agentsys_tag(self):
        self.assertIn("agentsys", self.content)


class TestSkillCrossConsistency(unittest.TestCase):
    """Cross-skill consistency checks."""

    def test_thinking_references_tot_paper(self):
        content = _read_skill("thinking")
        self.assertIn("arXiv 2305.10601", content)

    def test_executing_references_reflexion_paper(self):
        content = _read_skill("executing")
        self.assertIn("arXiv 2303.11366", content)

    def test_executing_references_agentsys_paper(self):
        content = _read_skill("executing")
        self.assertIn("arXiv 2602.07398", content)

    def test_thinking_step_order(self):
        """Steps must appear in order: -1 → -0.5 → 0 → 1."""
        content = _read_skill("thinking")
        pos_neg1 = content.index("Step -1:")
        pos_neg05 = content.index("Step -0.5:")
        pos_0 = content.index("Step 0:")
        pos_1 = content.index("Step 1:")
        self.assertLess(pos_neg1, pos_neg05)
        self.assertLess(pos_neg05, pos_0)
        self.assertLess(pos_0, pos_1)

    def test_thinking_borrows_qiushi_methods(self):
        content = _read_skill("thinking")
        for token in ["调查研究", "矛盾分析", "群众路线", "持久战略", "主要矛盾", "局部攻坚点"]:
            self.assertIn(token, content)

    def test_executing_section_order(self):
        """Sections 1.5 → 1.5.1 → 2 → 2.5 → 2.7 → 3."""
        content = _read_skill("executing")
        pos_15 = content.index("1.5. Parallel Agent Dispatch")
        pos_151 = content.index("1.5.1 子 Agent 输出 Schema 验证")
        pos_2 = content.index("2. Prefer TDD")
        pos_25 = content.index("2.5. TASK_NOTES Rolling Update")
        pos_27 = content.index("2.7. Mid-Task Reflection")
        pos_3 = content.index("3. Keep State Local")
        self.assertLess(pos_15, pos_151)
        self.assertLess(pos_151, pos_2)
        self.assertLess(pos_2, pos_25)
        self.assertLess(pos_25, pos_27)
        self.assertLess(pos_27, pos_3)


if __name__ == "__main__":
    unittest.main()
