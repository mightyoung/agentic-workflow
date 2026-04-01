#!/usr/bin/env python3
"""
Failure Handling Tests - 失败处理专项测试

测试失败处理的核心功能：
1. retry 计数正确累计
2. retry 超过阈值转 DEBUGGING
3. abort 终止工作流
4. state 和 trajectory 同步更新
"""

import os
import shutil
import tempfile
import unittest
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from workflow_engine import (
    initialize_workflow,
    handle_workflow_failure,
    load_state,
)
from state_schema import Decision


class TestFailureHandling(unittest.TestCase):
    """失败处理测试"""

    def setUp(self):
        """每个测试使用独立的工作目录"""
        self.workdir = tempfile.mkdtemp(prefix="failure_test_")

    def tearDown(self):
        """清理临时目录"""
        if os.path.exists(self.workdir):
            shutil.rmtree(self.workdir, ignore_errors=True)

    def test_retry_count_starts_at_zero(self):
        """测试首次失败重试计数从0开始"""
        # 初始化工作流
        _ = initialize_workflow("测试工作流", self.workdir)

        # 处理失败 - 首次重试
        result = handle_workflow_failure(self.workdir, "测试错误", strategy="retry", max_retries=3)

        self.assertTrue(result["success"])
        self.assertEqual(result["action"], "retry")
        self.assertEqual(result["retry_count"], 1)

        # 验证 state 中的 retry_count
        state = load_state(self.workdir)
        last_decision = state.decisions[-1]
        self.assertEqual(last_decision.metadata.get("retry_count"), 1)

    def test_retry_count_increments(self):
        """测试重试计数递增"""
        # 初始化工作流
        _ = initialize_workflow("测试工作流", self.workdir)

        # 第一次重试
        result1 = handle_workflow_failure(self.workdir, "错误1", strategy="retry", max_retries=3)
        self.assertEqual(result1["retry_count"], 1)

        # 第二次重试
        result2 = handle_workflow_failure(self.workdir, "错误2", strategy="retry", max_retries=3)
        self.assertEqual(result2["retry_count"], 2)

        # 第三次重试
        result3 = handle_workflow_failure(self.workdir, "错误3", strategy="retry", max_retries=3)
        self.assertEqual(result3["retry_count"], 3)

    def test_retry_exceeds_threshold_transitions_to_debugging(self):
        """测试重试超过阈值后转为DEBUGGING"""
        # 初始化工作流
        _ = initialize_workflow("测试工作流", self.workdir)

        # 第一次重试 (retry_count=1)
        result1 = handle_workflow_failure(self.workdir, "错误", strategy="retry", max_retries=2)
        self.assertEqual(result1["retry_count"], 1)
        self.assertEqual(result1["action"], "retry")

        # 第二次重试 (retry_count=2, 达到阈值)
        result2 = handle_workflow_failure(self.workdir, "错误", strategy="retry", max_retries=2)
        self.assertEqual(result2["retry_count"], 2)
        self.assertEqual(result2["action"], "retry")

        # 第三次应该转为DEBUGGING (retry_count=3 > max_retries=2)
        result3 = handle_workflow_failure(self.workdir, "错误", strategy="retry", max_retries=2)
        self.assertEqual(result3["action"], "debugging")
        self.assertEqual(result3["new_phase"], "DEBUGGING")

        # 验证 state 已更新
        state = load_state(self.workdir)
        self.assertEqual(state.phase.get("current"), "DEBUGGING")

    def test_abort_terminates_workflow(self):
        """测试abort终止工作流"""
        # 初始化工作流
        _ = initialize_workflow("测试工作流", self.workdir)

        # Abort
        result = handle_workflow_failure(self.workdir, "严重错误", strategy="abort")

        self.assertTrue(result["success"])
        self.assertEqual(result["action"], "aborted")
        self.assertEqual(result["final_state"], "failed")

        # 验证 state 已更新
        state = load_state(self.workdir)
        self.assertEqual(state.phase.get("current"), "COMPLETE")

    def test_retry_persists_retry_count_in_state(self):
        """测试重试计数持久化到state"""
        # 初始化工作流
        _ = initialize_workflow("测试工作流", self.workdir)

        # 执行多次重试
        handle_workflow_failure(self.workdir, "错误1", strategy="retry", max_retries=5)
        handle_workflow_failure(self.workdir, "错误2", strategy="retry", max_retries=5)
        handle_workflow_failure(self.workdir, "错误3", strategy="retry", max_retries=5)

        # 重新加载state验证
        state = load_state(self.workdir)
        retry_decisions = [d for d in state.decisions if d.metadata.get("retry_count")]
        self.assertGreaterEqual(len(retry_decisions), 3)

        # 最后一个决策的retry_count应该是3
        last_retry = retry_decisions[-1]
        self.assertEqual(last_retry.metadata.get("retry_count"), 3)

    def test_debugging_transition_updates_phase(self):
        """测试DEBUGGING转换更新phase"""
        # 初始化工作流
        _ = initialize_workflow("测试工作流", self.workdir)

        # 强制转为DEBUGGING
        result = handle_workflow_failure(self.workdir, "需要调试", strategy="debugging")

        self.assertTrue(result["success"])
        self.assertEqual(result["action"], "debugging")
        self.assertEqual(result["new_phase"], "DEBUGGING")

        # 验证state
        state = load_state(self.workdir)
        self.assertEqual(state.phase.get("current"), "DEBUGGING")

        # 验证phase history有记录
        history = state.phase.get("history", [])
        phase_names = [h.get("phase") for h in history]
        self.assertIn("DEBUGGING", phase_names)


class TestStateSchemaDecision(unittest.TestCase):
    """Decision schema测试"""

    def test_decision_has_metadata_field(self):
        """测试Decision有metadata字段"""
        decision = Decision(
            timestamp="2024-01-01T00:00:00",
            decision="测试决策",
            reason="测试原因",
            metadata={"retry_count": 1},
        )
        self.assertEqual(decision.metadata.get("retry_count"), 1)

    def test_decision_metadata_defaults_to_empty_dict(self):
        """测试Decision metadata默认为空字典"""
        decision = Decision(
            timestamp="2024-01-01T00:00:00",
            decision="测试决策",
        )
        self.assertEqual(decision.metadata, {})

    def test_decision_to_dict_includes_metadata(self):
        """测试Decision序列化包含metadata"""
        decision = Decision(
            timestamp="2024-01-01T00:00:00",
            decision="测试决策",
            metadata={"key": "value"},
        )
        d = decision.to_dict()
        self.assertIn("metadata", d)
        self.assertEqual(d["metadata"]["key"], "value")


if __name__ == "__main__":
    unittest.main(verbosity=2)
