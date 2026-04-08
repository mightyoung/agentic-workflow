#!/usr/bin/env python3
"""
Trajectory Tests - 轨迹持久化专项测试

测试轨迹记录和恢复的核心功能：
1. 轨迹创建
2. Phase记录
3. 决策记录
4. 文件变更记录
5. 恢复点计算
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from memory_ops import update_planning_summary, update_review_summary, update_thinking_summary  # noqa: E402
from trajectory_logger import (
    PhaseRecord,
    TrajectoryLogger,
    _get_next_phase_after,
    get_resume_point,
    list_trajectories,
    load_trajectory,
    resume_from_point,
    trajectory_base_path,
    trajectory_date_dir,
)


class TestTrajectoryLogger(unittest.TestCase):
    """轨迹记录器测试"""

    @classmethod
    def setUpClass(cls):
        """创建临时工作目录"""
        cls.workdir = tempfile.mkdtemp(prefix="trajectory_test_")

    @classmethod
    def tearDownClass(cls):
        """清理临时目录"""
        if hasattr(cls, 'workdir') and os.path.exists(cls.workdir):
            shutil.rmtree(cls.workdir, ignore_errors=True)

    def test_trajectory_base_path(self):
        """测试轨迹基础路径"""
        base = trajectory_base_path(self.workdir)
        self.assertEqual(base.name, "trajectories")

    def test_trajectory_date_dir(self):
        """测试轨迹日期目录"""
        session_id = "s20240101120000"
        date_dir = trajectory_date_dir(self.workdir, session_id)
        self.assertEqual(date_dir.name, session_id)

    def test_logger_start(self):
        """测试轨迹记录器启动"""
        logger = TrajectoryLogger(self.workdir)
        run_id = logger.start("测试prompt", "FULL_WORKFLOW")
        self.assertTrue(run_id.startswith("R"))
        self.assertEqual(logger._trigger_type, "FULL_WORKFLOW")

    def test_logger_enter_exit_phase(self):
        """测试进入退出phase"""
        logger = TrajectoryLogger(self.workdir)
        logger.start("测试", "FULL_WORKFLOW")
        logger.enter_phase("PLANNING")
        self.assertEqual(logger._current_phase, "PLANNING")
        logger.exit_phase("PLANNING")
        self.assertIsNone(logger._current_phase)

    def test_logger_log_decision(self):
        """测试记录决策"""
        logger = TrajectoryLogger(self.workdir)
        logger.start("测试", "FULL_WORKFLOW")
        logger.enter_phase("PLANNING")
        logger.log_decision("创建任务分解", "需要清晰的执行计划")
        self.assertEqual(len(logger._current_decisions), 1)

    def test_logger_log_file_change(self):
        """测试记录文件变更"""
        logger = TrajectoryLogger(self.workdir)
        logger.start("测试", "FULL_WORKFLOW")
        logger.enter_phase("EXECUTING")
        logger.log_file_change("main.py", "create")
        self.assertEqual(len(logger._current_file_changes), 1)

    def test_logger_complete(self):
        """测试完成轨迹"""
        logger = TrajectoryLogger(self.workdir)
        logger.start("测试", "FULL_WORKFLOW")
        logger.enter_phase("PLANNING")
        logger.exit_phase("PLANNING")
        logger.enter_phase("EXECUTING")
        logger.exit_phase("EXECUTING")
        logger.complete("completed")

        # 验证轨迹文件存在
        trajectory_file = logger.base_dir / "trajectory.json"
        self.assertTrue(trajectory_file.exists())

        # 验证轨迹内容
        with trajectory_file.open() as f:
            data = json.load(f)
            self.assertEqual(data["final_state"], "completed")

    def test_logger_session_id(self):
        """测试session_id生成"""
        logger = TrajectoryLogger(self.workdir)
        self.assertTrue(logger.session_id.startswith("s"))


class TestTrajectoryPersistence(unittest.TestCase):
    """轨迹持久化测试"""

    def setUp(self):
        """每个测试使用独立的工作目录"""
        self.workdir = tempfile.mkdtemp(prefix="trajectory_persist_")

    def tearDown(self):
        """清理临时目录"""
        if os.path.exists(self.workdir):
            shutil.rmtree(self.workdir, ignore_errors=True)

    def test_save_and_load_trajectory(self):
        """测试保存和加载轨迹"""
        logger = TrajectoryLogger(self.workdir)
        logger.start("测试轨迹", "FULL_WORKFLOW")
        logger.enter_phase("PLANNING")
        logger.exit_phase("PLANNING")
        logger.complete("completed")

        # 加载轨迹
        loaded = load_trajectory(self.workdir, logger.session_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["prompt"], "测试轨迹")
        self.assertEqual(loaded["final_state"], "completed")

    def test_list_trajectories(self):
        """测试列出轨迹"""
        # 创建轨迹
        logger1 = TrajectoryLogger(self.workdir)
        logger1.start("轨迹1", "FULL_WORKFLOW")
        logger1.enter_phase("PLANNING")
        logger1.exit_phase("PLANNING")
        logger1.complete("completed")

        # 使用不同的session_id（通过显式传入）
        logger2 = TrajectoryLogger(self.workdir, session_id=f"s{int(datetime.now().timestamp()*1000)}")
        logger2.start("轨迹2", "FULL_WORKFLOW")
        logger2.enter_phase("EXECUTING")
        logger2.exit_phase("EXECUTING")
        logger2.complete("completed")

        trajectories = list_trajectories(self.workdir)
        # 应该有至少2个轨迹
        self.assertGreaterEqual(len(trajectories), 2)


class TestResumePoint(unittest.TestCase):
    """恢复点测试"""

    def setUp(self):
        """每个测试使用独立的工作目录"""
        self.workdir = tempfile.mkdtemp(prefix="resume_test_")

    def tearDown(self):
        """清理临时目录"""
        if os.path.exists(self.workdir):
            shutil.rmtree(self.workdir, ignore_errors=True)

    def test_get_resume_point_completed(self):
        """测试获取已完成轨迹的恢复点"""
        logger = TrajectoryLogger(self.workdir)
        logger.start("测试恢复", "FULL_WORKFLOW")
        logger.enter_phase("PLANNING")
        logger.exit_phase("PLANNING")
        logger.enter_phase("EXECUTING")
        logger.exit_phase("EXECUTING")
        logger.complete("completed")

        resume_point = get_resume_point(self.workdir, logger.session_id)
        self.assertIsNotNone(resume_point)
        self.assertEqual(resume_point["session_id"], logger.session_id)
        # 已完成的轨迹不应该能恢复
        self.assertFalse(resume_point["can_resume"])

    def test_resume_from_interrupted(self):
        """测试从中断点恢复"""
        # 创建一个中断的工作流（不调用complete）
        logger = TrajectoryLogger(self.workdir)
        original_session_id = logger.session_id
        logger.start("测试中断", "FULL_WORKFLOW")
        logger.enter_phase("PLANNING")
        logger.exit_phase("PLANNING")
        logger.enter_phase("EXECUTING")
        # 模拟中断 - 没有exit_phase和complete

        update_thinking_summary(
            str(Path(self.workdir) / "SESSION-STATE.md"),
            {
                "workflow_label": "复杂问题攻坚",
                "workflow": "workflow_2_complex_problem",
                "major_contradiction": "目标完整性 vs 交付节奏",
                "stage_judgment": "战略相持",
                "local_attack_point": "最小可验证切口",
                "recommendation": "先做事实收集",
                "memory_hints_count": 1,
            },
        )
        update_planning_summary(
            str(Path(self.workdir) / "SESSION-STATE.md"),
            {
                "plan_source": "tasks.md",
                "plan_task_count": 3,
                "completed_task_count": 1,
                "in_progress_task_count": 1,
                "blocked_task_count": 0,
                "ready_task_count": 1,
                "parallel_candidate_group_count": 1,
                "parallel_ready_task_count": 1,
                "conflict_group_count": 0,
                "worktree_recommended": True,
                "worktree_reason": "multi-step plan detected",
                "plan_digest": "tasks.md: 3 task(s), 1 done, 1 in progress, 0 blocked, 1 ready; next=TASK-002; worktree=yes",
            },
        )
        update_review_summary(
            str(Path(self.workdir) / "SESSION-STATE.md"),
            {
                "review_found": True,
                "review_source": "review_latest",
                "review_status": "reviewed",
                "stage_1_status": "reviewed",
                "stage_2_status": "reviewed",
                "risk_level": "low",
                "verdict": "approved",
                "degraded_mode": False,
                "files_reviewed": 2,
            },
        )

        # 恢复工作流
        result = resume_from_point(self.workdir, original_session_id)
        self.assertIsNotNone(result)
        # 由于EXECUTING没有exited_at，resume_from应该是EXECUTING
        self.assertEqual(result["resume_from"], "EXECUTING")
        self.assertEqual(result["resume_summary"]["resume_from"], "EXECUTING")
        self.assertEqual(result["resume_summary"]["original_session_id"], original_session_id)
        self.assertEqual(result["resume_summary"]["phase_count"], 1)
        self.assertEqual(result["resume_summary"]["planning_summary"]["plan_source"], "tasks.md")
        self.assertEqual(result["resume_summary"]["review_summary"]["review_source"], "review_latest")
        self.assertEqual(result["resume_summary"]["thinking_summary"]["workflow_label"], "复杂问题攻坚")

        resumed_trajectory = result["resumed_trajectory"]
        self.assertEqual(resumed_trajectory["resume_summary"]["resume_from"], "EXECUTING")
        self.assertEqual(resumed_trajectory["resume_summary"]["next_phase"], "REVIEWING")
        self.assertEqual(resumed_trajectory["resume_summary"]["planning_summary"]["plan_source"], "tasks.md")
        self.assertEqual(resumed_trajectory["resume_summary"]["review_summary"]["review_source"], "review_latest")
        self.assertEqual(resumed_trajectory["resume_summary"]["thinking_summary"]["workflow_label"], "复杂问题攻坚")
        self.assertEqual(resumed_trajectory["phases"][0]["notes"][0], f"Resumed from {original_session_id} at EXECUTING")

    def test_resume_from_init_no_advance(self):
        """测试从初始化后未推进的session恢复"""
        # 创建一个只初始化的工作流
        logger = TrajectoryLogger(self.workdir)
        original_session_id = logger.session_id
        logger.start("测试未推进", "FULL_WORKFLOW")
        logger.enter_phase("PLANNING")
        # 从未退出PLANNING，直接中断

        # 恢复工作流 - 应该能处理这种"未完成首phase"的情况
        result = resume_from_point(self.workdir, original_session_id)
        self.assertIsNotNone(result)
        # resume_from 应该是 PLANNING（因为它还没有exited_at）
        self.assertEqual(result["resume_from"], "PLANNING")
        self.assertEqual(result["resume_summary"]["resume_from"], "PLANNING")
        self.assertEqual(result["resume_summary"]["original_session_id"], original_session_id)


class TestGetNextPhase(unittest.TestCase):
    """获取下一个phase测试"""

    def test_next_phase_after_planning(self):
        """测试PLANNING之后的phase"""
        next_phase = _get_next_phase_after("PLANNING", "EXECUTING")
        self.assertEqual(next_phase, "EXECUTING")

    def test_next_phase_after_executing(self):
        """测试EXECUTING之后的phase"""
        next_phase = _get_next_phase_after("EXECUTING", "REVIEWING")
        self.assertEqual(next_phase, "REVIEWING")

    def test_next_phase_cannot_resume_from_complete(self):
        """测试从COMPLETE无法恢复"""
        next_phase = _get_next_phase_after("COMPLETE", "COMPLETE")
        self.assertIsNone(next_phase)

    def test_next_phase_cannot_resume_from_failed(self):
        """测试从failed无法恢复"""
        next_phase = _get_next_phase_after("EXECUTING", "failed")
        self.assertIsNone(next_phase)


class TestPhaseRecord(unittest.TestCase):
    """Phase记录测试"""

    def test_phase_record_to_dict(self):
        """测试PhaseRecord序列化"""
        record = PhaseRecord(
            phase="PLANNING",
            entered_at="2024-01-01T00:00:00",
            exited_at="2024-01-01T00:01:00",
        )
        d = record.to_dict()
        self.assertEqual(d["phase"], "PLANNING")
        self.assertEqual(d["entered_at"], "2024-01-01T00:00:00")


if __name__ == "__main__":
    unittest.main(verbosity=2)
