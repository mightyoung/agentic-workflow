"""Unit tests for team_agent.py core utilities."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from team_agent import (
    _compact_value,
    _compact_list,
    build_shared_memory_capsule,
    WorkerType,
    MessageType,
    WorkerResult,
)


class TestCompactHelpers(unittest.TestCase):
    def test_compact_value_short_string(self):
        self.assertEqual(_compact_value("hello", 20), "hello")

    def test_compact_value_truncates_long_string(self):
        result = _compact_value("A" * 200, 50)
        self.assertLessEqual(len(result), 54)  # 50 + "..."

    def test_compact_value_handles_non_string(self):
        result = _compact_value(42, 10)
        self.assertIsInstance(result, str)

    def test_compact_value_handles_none(self):
        result = _compact_value(None, 10)
        self.assertIsInstance(result, str)

    def test_compact_list_returns_list(self):
        result = _compact_list(["a", "b", "c", "d", "e"], limit=3)
        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), 4)  # limit + truncation indicator

    def test_compact_list_handles_empty(self):
        result = _compact_list([], limit=3)
        self.assertEqual(result, [])

    def test_compact_list_handles_none(self):
        result = _compact_list(None, limit=3)
        self.assertEqual(result, [])

    def test_compact_list_within_limit(self):
        result = _compact_list(["a", "b"], limit=5)
        self.assertEqual(result, ["a", "b"])


class TestWorkerType(unittest.TestCase):
    def test_worker_types_exist(self):
        self.assertIsNotNone(WorkerType.CODER)
        self.assertIsNotNone(WorkerType.REVIEWER)
        self.assertIsNotNone(WorkerType.RESEARCHER)

    def test_worker_type_is_enum(self):
        from enum import Enum
        self.assertIsInstance(WorkerType.CODER, WorkerType)


class TestMessageType(unittest.TestCase):
    def test_message_types_exist(self):
        self.assertIsNotNone(MessageType.TASK_ASSIGN)
        self.assertIsNotNone(MessageType.TASK_RESULT)
        self.assertIsNotNone(MessageType.TASK_ERROR)

    def test_message_type_values(self):
        self.assertEqual(MessageType.TASK_ASSIGN.value, "task_assign")
        self.assertEqual(MessageType.TASK_RESULT.value, "task_result")


class TestWorkerResult(unittest.TestCase):
    def test_create_success_result(self):
        result = WorkerResult(
            worker_type=WorkerType.CODER,
            task="implement login",
            output="def login(): pass",
            success=True,
        )
        self.assertTrue(result.success)
        self.assertEqual(result.worker_type, WorkerType.CODER)

    def test_create_failure_result(self):
        result = WorkerResult(
            worker_type=WorkerType.CODER,
            task="implement login",
            output="",
            success=False,
            error="compilation failed",
        )
        self.assertFalse(result.success)
        self.assertEqual(result.error, "compilation failed")

    def test_default_artifacts_empty(self):
        result = WorkerResult(
            worker_type=WorkerType.REVIEWER,
            task="review",
            output="lgtm",
            success=True,
        )
        self.assertEqual(result.artifacts, [])


class TestBuildSharedMemoryCapsule(unittest.TestCase):
    def test_returns_dict_with_expected_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            capsule = build_shared_memory_capsule(tmpdir, "build auth module")
            self.assertIsInstance(capsule, dict)
            self.assertIn("task", capsule)
            self.assertIn("runtime_profile", capsule)
            self.assertIn("contract", capsule)
            self.assertIn("planning", capsule)
            self.assertIn("research", capsule)
            self.assertIn("thinking", capsule)
            self.assertIn("review", capsule)
            self.assertIn("frontier", capsule)

    def test_task_field_truncated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            long_task = "A" * 300
            capsule = build_shared_memory_capsule(tmpdir, long_task)
            self.assertLessEqual(len(capsule["task"]), 164)  # 160 + "..."

    def test_with_contract(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            contract = {
                "status": "active",
                "goals": ["goal1", "goal2"],
                "acceptance_criteria": ["crit1"],
                "impact_files": ["auth.py"],
                "dependencies": [],
                "rollback_note": "revert commit",
            }
            capsule = build_shared_memory_capsule(tmpdir, "task", contract=contract)
            self.assertEqual(capsule["contract"]["status"], "active")
            self.assertEqual(capsule["contract"]["goal_count"], 2)
            self.assertEqual(capsule["contract"]["acceptance_count"], 1)

    def test_with_frontier(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            frontier = {
                "plan_source": "task_plan.md",
                "executable_frontier": ["T1", "T2"],
                "parallel_candidates": [["T1", "T2"]],
                "conflict_groups": [],
            }
            capsule = build_shared_memory_capsule(tmpdir, "task", frontier=frontier)
            self.assertEqual(capsule["frontier"]["plan_source"], "task_plan.md")
            self.assertEqual(capsule["frontier"]["executable_count"], 2)
            self.assertEqual(capsule["frontier"]["parallel_group_count"], 1)

    def test_empty_contract_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            capsule = build_shared_memory_capsule(tmpdir, "task")
            self.assertIsNone(capsule["contract"]["status"])
            self.assertEqual(capsule["contract"]["goal_count"], 0)


if __name__ == "__main__":
    unittest.main()
