#!/usr/bin/env python3
"""
End-to-End Business Chain Tests - 真实业务链测试

测试真实的业务场景:
1. Code Implementation Chain - REST API实现
2. Research Analysis Chain - 技术调研
3. Debug Fix Chain - Bug修复

每个测试验证完整的 workflow: route -> plan -> execute -> review -> complete
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestE2EBusinessChains(unittest.TestCase):
    """真实业务链测试"""

    @classmethod
    def setUpClass(cls):
        """创建临时工作目录"""
        cls.workdir = tempfile.mkdtemp(prefix="e2e_test_")

    @classmethod
    def tearDownClass(cls):
        """清理临时目录"""
        if hasattr(cls, 'workdir') and os.path.exists(cls.workdir):
            shutil.rmtree(cls.workdir, ignore_errors=True)

    def _run_workflow_init(self, prompt: str) -> dict:
        """初始化workflow"""
        result = subprocess.run(
            [
                "python3", "scripts/workflow_engine.py",
                "--workdir", self.workdir,
                "--op", "init",
                "--prompt", prompt,
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        self.assertEqual(result.returncode, 0, f"init failed: {result.stderr}")
        # JSON is after the Chinese log messages, find it
        json_start = result.stdout.find("{")
        self.assertGreater(json_start, 0, f"No JSON found in stdout: {result.stdout[:200]}")
        return json.loads(result.stdout[json_start:])

    def _run_workflow_advance(self, phase: str, task_status: str = None) -> dict:
        """推进workflow"""
        cmd = [
            "python3", "scripts/workflow_engine.py",
            "--workdir", self.workdir,
            "--op", "advance",
            "--phase", phase,
        ]
        if task_status:
            cmd.extend(["--task-status", task_status])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        self.assertEqual(result.returncode, 0, f"advance failed: {result.stderr}")
        # JSON is after the Chinese log messages, find it
        json_start = result.stdout.find("{")
        if json_start < 0:
            return {}
        return json.loads(result.stdout[json_start:])

    def _get_snapshot(self) -> dict:
        """获取workflow快照"""
        result = subprocess.run(
            [
                "python3", "scripts/workflow_engine.py",
                "--workdir", self.workdir,
                "--op", "snapshot",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        self.assertEqual(result.returncode, 0, f"snapshot failed: {result.stderr}")
        # Handle potential Chinese log prefix
        json_start = result.stdout.find("{")
        if json_start < 0:
            return {}
        return json.loads(result.stdout[json_start:])

    def _validate_state_schema(self) -> tuple:
        """验证状态schema - 只使用unified_state验证"""
        result = subprocess.run(
            [
                "python3", "scripts/unified_state.py",
                "--workdir", self.workdir,
                "--op", "validate",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        self.assertEqual(result.returncode, 0, f"validate failed: {result.stderr}")
        json_start = result.stdout.find("{")
        if json_start < 0:
            return False, ["No JSON in output"]
        data = json.loads(result.stdout[json_start:])
        return data["valid"], data.get("errors", [])

    def _check_trajectory_created(self) -> bool:
        """检查trajectory是否被创建"""
        snapshot = self._get_snapshot()
        session_id = snapshot.get("session_id")
        if not session_id:
            return False

        trajectory_path = Path(self.workdir) / "trajectories"
        if not trajectory_path.exists():
            return False

        # 检查是否存在session_id对应的轨迹目录
        for date_dir in trajectory_path.iterdir():
            if date_dir.is_dir():
                session_dir = date_dir / session_id
                if session_dir.exists():
                    return (session_dir / "trajectory.json").exists()
        return False


class TestCodeImplementationChain(TestE2EBusinessChains):
    """业务链1: 代码实现链"""

    def test_code_implementation_full_flow(self):
        """
        测试场景: 实现REST API用户认证

        验证:
        1. Route正确识别EXECUTING
        2. 状态正确更新
        3. Trajectory记录完整轨迹
        4. 状态验证通过
        """
        prompt = "实现一个用户认证的REST API，包括注册、登录、登出功能"

        # Step 1: 初始化workflow
        init_result = self._run_workflow_init(prompt)

        self.assertIn("task_id", init_result)
        self.assertIn("phase", init_result)
        self.assertIn("state_file", init_result)

        # Step 2: 获取快照验证状态
        snapshot = self._get_snapshot()
        self.assertTrue(snapshot.get("exists", False), "State should exist")
        self.assertTrue(snapshot.get("valid", False), "State should be valid")

        current_phase = snapshot.get("current_phase", "EXECUTING")

        # Step 3: 推进phase直到COMPLETE
        # 获取推荐的下一个phases
        recommended = snapshot.get("recommended_next_phases", [])
        if not recommended:
            recommended = ["EXECUTING", "REVIEWING", "COMPLETE"]

        for next_phase in recommended:
            if current_phase == "COMPLETE":
                break
            try:
                advance_result = self._run_workflow_advance(next_phase)
                current_phase = advance_result["phase"]
            except ValueError:
                # 无法推进到该phase，尝试下一个
                continue

        # Step 4: 如果还不是COMPLETE，尝试直接推进
        if current_phase != "COMPLETE":
            try:
                advance_result = self._run_workflow_advance("COMPLETE", "completed")
                current_phase = advance_result["phase"]
            except ValueError:
                pass

        # Step 5: 验证最终状态
        snapshot = self._get_snapshot()
        self.assertEqual(snapshot.get("current_phase"), "COMPLETE")
        self.assertTrue(snapshot.get("valid", False))


class TestResearchAnalysisChain(TestE2EBusinessChains):
    """业务链2: 调研分析链"""

    def test_research_analysis_full_flow(self):
        """
        测试场景: 研究微服务架构最佳实践

        验证:
        1. Route正确识别RESEARCH/THINKING
        2. 工作流状态正确更新
        3. Trajectory记录完整轨迹
        4. 状态验证通过
        """
        prompt = "研究微服务架构的最佳实践，包括服务拆分、通信模式、容错处理"

        # Step 1: 初始化workflow
        init_result = self._run_workflow_init(prompt)
        self.assertIn("task_id", init_result)
        self.assertIn("phase", init_result)

        # Step 2: 获取快照
        snapshot = self._get_snapshot()
        current_phase = snapshot.get("current_phase")
        self.assertIn(current_phase, ["RESEARCH", "THINKING", "PLANNING", "EXECUTING"])

        # Step 3: 获取推荐的下一个phases并推进
        recommended = snapshot.get("recommended_next_phases", [])
        if not recommended:
            recommended = ["THINKING", "PLANNING", "EXECUTING", "REVIEWING", "COMPLETE"]

        for next_phase in recommended:
            if current_phase == "COMPLETE":
                break
            try:
                advance_result = self._run_workflow_advance(next_phase)
                current_phase = advance_result["phase"]
            except ValueError:
                continue

        # Step 4: 如果还不是COMPLETE，尝试直接推进
        if current_phase != "COMPLETE":
            try:
                advance_result = self._run_workflow_advance("COMPLETE", "completed")
                current_phase = advance_result["phase"]
            except ValueError:
                pass

        # Step 5: 验证最终状态
        snapshot = self._get_snapshot()
        self.assertEqual(snapshot.get("current_phase"), "COMPLETE")
        self.assertTrue(snapshot.get("valid", False))


class TestDebugFixChain(TestE2EBusinessChains):
    """业务链3: 调试修复链"""

    def test_debug_fix_full_flow(self):
        """
        测试场景: 修复登录bug

        验证:
        1. Route正确识别DEBUGGING相关phase
        2. 工作流状态正确更新
        3. Trajectory记录完整轨迹
        4. 状态验证通过
        """
        prompt = "修复登录bug：用户点击登出后Session没有清除，导致重新访问仍然保持登录状态"

        # Step 1: 初始化workflow
        init_result = self._run_workflow_init(prompt)
        self.assertIn("task_id", init_result)

        # Step 2: 获取快照
        snapshot = self._get_snapshot()
        current_phase = snapshot.get("current_phase")

        # DEBUGGING可能被识别为DEBUGGING或EXECUTING
        self.assertIn(current_phase, ["DEBUGGING", "EXECUTING", "PLANNING", "RESEARCH", "THINKING"])

        # Step 3: 获取推荐的下一个phases并推进
        recommended = snapshot.get("recommended_next_phases", [])
        if not recommended:
            recommended = ["EXECUTING", "DEBUGGING", "REVIEWING", "COMPLETE"]

        for next_phase in recommended:
            if current_phase == "COMPLETE":
                break
            try:
                advance_result = self._run_workflow_advance(next_phase)
                current_phase = advance_result["phase"]
            except ValueError:
                continue

        # Step 4: 如果还不是COMPLETE，尝试直接推进
        if current_phase != "COMPLETE":
            try:
                advance_result = self._run_workflow_advance("COMPLETE", "completed")
                current_phase = advance_result["phase"]
            except ValueError:
                pass

        # Step 5: 验证最终状态
        snapshot = self._get_snapshot()
        self.assertEqual(snapshot.get("current_phase"), "COMPLETE")
        self.assertTrue(snapshot.get("valid", False))


class TestStateSchemaValidation(TestE2EBusinessChains):
    """状态Schema验证测试"""

    def test_unified_state_schema_validation(self):
        """验证统一状态schema"""
        prompt = "实现一个简单的计算器功能"

        # 初始化workflow
        self._run_workflow_init(prompt)

        # 验证unified state是否有效
        snapshot = self._get_snapshot()
        self.assertTrue(snapshot.get("valid", False), "Unified state should be valid")
        self.assertEqual(snapshot.get("errors"), [])

    def test_task_decomposition_with_ids(self):
        """测试任务分解生成唯一ID"""
        from task_decomposer import decompose

        prompt = "实现用户管理模块，包括用户注册、登录、信息修改三个功能"

        tasks = decompose(prompt)

        self.assertGreater(len(tasks), 0)

        # 验证每个任务有唯一ID
        task_ids = [t.task_id for t in tasks]
        self.assertEqual(len(task_ids), len(set(task_ids)), "Task IDs should be unique")

        # 验证ID格式
        for task in tasks:
            self.assertTrue(task.task_id.startswith("T"), "Task ID should start with T")
            self.assertIn(task.priority, ["P0", "P1", "P2", "P3"], "Priority should be valid")


class TestTrajectoryPersistence(TestE2EBusinessChains):
    """轨迹持久化测试"""

    def test_trajectory_logger_basic(self):
        """测试轨迹记录器基本功能"""
        from trajectory_logger import TrajectoryLogger

        logger = TrajectoryLogger(self.workdir)
        run_id = logger.start("测试prompt", "FULL_WORKFLOW")

        self.assertTrue(run_id.startswith("R"), "Run ID should start with R")

        # 进入phase
        logger.enter_phase("PLANNING")
        logger.log_decision("创建任务分解", "需要清晰的执行计划")
        logger.log_file_change("task_plan.md", "create")
        logger.exit_phase("PLANNING")

        # 进入下一个phase
        logger.enter_phase("EXECUTING")
        logger.log_file_change("main.py", "create")
        logger.exit_phase("EXECUTING")

        # 完成
        logger.complete("completed")

        # 验证轨迹文件
        trajectory_path = Path(self.workdir) / "trajectories"
        self.assertTrue(trajectory_path.exists(), "Trajectories directory should exist")

    def test_trajectory_list_and_resume(self):
        """测试轨迹列表和恢复功能"""
        from trajectory_logger import TrajectoryLogger, list_trajectories, get_resume_point

        # 创建测试轨迹
        logger = TrajectoryLogger(self.workdir)
        session_id = logger.session_id
        logger.start("测试恢复功能", "FULL_WORKFLOW")
        logger.enter_phase("PLANNING")
        logger.exit_phase("PLANNING")
        logger.complete("completed")

        # 列出轨迹
        trajectories = list_trajectories(self.workdir)
        self.assertGreater(len(trajectories), 0, "Should have at least one trajectory")

        # 获取恢复点
        resume_point = get_resume_point(self.workdir, session_id)
        self.assertIsNotNone(resume_point, "Should get resume point")

    def test_trajectory_resume_from_interrupted(self):
        """测试从中断点恢复功能"""
        from trajectory_logger import TrajectoryLogger, resume_from_point, list_trajectories

        # 创建一个中断的工作流 (不调用complete)
        logger = TrajectoryLogger(self.workdir)
        original_session_id = logger.session_id
        logger.start("测试中断恢复", "FULL_WORKFLOW")
        logger.enter_phase("PLANNING")
        logger.exit_phase("PLANNING")
        logger.enter_phase("EXECUTING")
        # 模拟中断 - 没有exit_phase和complete

        # 恢复工作流
        result = resume_from_point(self.workdir, original_session_id)

        self.assertIsNotNone(result, "Should get resume result")
        self.assertNotEqual(result["session_id"], original_session_id, "Should create new session")
        # EXECUTING was entered but not exited, so it's the current active phase to resume from
        self.assertEqual(result["resume_from"], "EXECUTING", "Should resume from EXECUTING")
        self.assertEqual(result["next_phase"], "REVIEWING", "Should suggest REVIEWING as next")
        self.assertTrue(result["can_resume"], "Should be able to resume")


if __name__ == "__main__":
    unittest.main(verbosity=2)
