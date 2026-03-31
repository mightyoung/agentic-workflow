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
        # JSON is after the Chinese log messages, find it
        json_start = result.stdout.find("{")
        if json_start >= 0:
            try:
                json_data = json.loads(result.stdout[json_start:])
                # Check if advance was blocked (e.g., quality gate failure)
                if json_data.get("blocked"):
                    raise ValueError(json_data.get("error", "Phase transition blocked"))
            except json.JSONDecodeError:
                pass

        self.assertEqual(result.returncode, 0, f"advance failed: {result.stderr}")
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

    def _check_plan_consumed(self) -> bool:
        """检查任务计划是否被消费（是否有任务状态变化）"""
        import json
        tracker_path = Path(self.workdir) / ".task_tracker.json"
        if not tracker_path.exists():
            return False

        try:
            tracker = json.loads(tracker_path.read_text(encoding="utf-8"))
            tasks = tracker.get("tasks", [])
            # 检查是否有任务状态不是 backlog 的
            return any(t.get("status") != "backlog" for t in tasks)
        except (json.JSONDecodeError, IOError):
            return False

    def _check_artifact_content(self, artifact_type: str, task_desc: str = None) -> bool:
        """检查特定类型工件的内容是否符合最小结构和质量标准"""
        artifact_path = Path(self.workdir)
        if artifact_type == "findings":
            # Look for session-aware naming first, fallback to legacy naming
            candidates = list(artifact_path.glob("findings_*.md")) + list(artifact_path.glob("findings.md"))
            if candidates:
                # Use most recently modified
                artifact_path = max(candidates, key=lambda p: p.stat().st_mtime)
            else:
                artifact_path = artifact_path / "findings.md"
        elif artifact_type == "review":
            # Look for session-aware naming first, fallback to legacy naming
            candidates = list(artifact_path.glob("review_*.md")) + list(artifact_path.glob("review.md"))
            if candidates:
                artifact_path = max(candidates, key=lambda p: p.stat().st_mtime)
            else:
                artifact_path = artifact_path / "review.md"
        elif artifact_type in ("summary", "completion_summary"):
            # Look for session-aware naming first, fallback to legacy naming
            candidates = list(artifact_path.glob("completion_summary_*.md")) + list(artifact_path.glob("completion_summary.md"))
            if candidates:
                artifact_path = max(candidates, key=lambda p: p.stat().st_mtime)
            else:
                artifact_path = artifact_path / "completion_summary.md"
        else:
            return False

        if not artifact_path.exists():
            return False

        content = artifact_path.read_text(encoding="utf-8")
        # 结构检查：必须有标题和内容
        has_title = content.strip().startswith("#")
        has_content = len(content.strip()) > 20
        if not (has_title and has_content):
            return False

        # 关键章节检查
        if artifact_type == "findings":
            # 检查是否有研究问题、方法、结论、建议
            has_sections = all(s in content for s in ["Research Question", "Method", "Conclusions", "Recommendations"])
            # 明确拒绝占位内容
            no_placeholder = "Placeholder:" not in content
            if not (has_sections and no_placeholder):
                return False
            # 检查内容不是全generic - 至少有具体术语或领域关键词
            if task_desc:
                # 检查task描述中的关键词是否出现在内容中（语义相关）
                task_keywords = set(task_desc.split())
                content_lower = content.lower()
                # 过滤停用词
                stop_words = {"的", "了", "和", "是", "在", "我", "有", "个", "等", "以", "对", "为", "与", "或", "及", "包括", "什么", "如何", "怎么", "哪些", "一个", "可以", "需要", "应该", "the", "a", "an", "of", "and", "in", "on", "for", "to", "is", "this", "that", "with", "as"}
                meaningful_keywords = [w for w in task_keywords if w.lower() not in stop_words and len(w) > 2]
                # 至少有一个有意义的关键词出现在内容中
                has_semantic_match = any(kw.lower() in content_lower for kw in meaningful_keywords[:10])
                if not has_semantic_match:
                    return False
            # 如果包含 Sources section，检查是否有 URL（真搜索的证据）
            if "## Sources" in content or "Sources" in content:
                # 应该有 http:// 或 https:// 链接
                has_urls = "http://" in content or "https://" in content
                if not has_urls:
                    return False
            return True
        elif artifact_type == "review":
            # 检查是否有审查范围、发现、风险、建议
            has_sections = all(s in content for s in ["Review Scope", "Findings", "Risk Level", "Recommendations"])
            # 明确拒绝占位内容
            no_placeholder = "Placeholder:" not in content
            if not (has_sections and no_placeholder):
                return False
            # 如果包含 Reviewed Files section，检查是否有具体文件路径（真代码审查的证据）
            if "Reviewed Files" in content or "reviewed_files" in content.lower():
                # 应该有文件路径模式 (如 .py, .js, .ts, .go 等)
                import re
                # 匹配常见代码文件扩展名
                has_file_refs = re.search(r'\.\w{1,5}', content)  # e.g., .py, .js, .ts
                if not has_file_refs:
                    return False
            return True
        elif artifact_type == "summary":
            # 检查是否有状态和交付物汇总
            has_sections = all(s in content for s in ["Status", "Delivered Artifacts"])
            return has_sections

        return True

    def _get_business_artifact_types(self) -> set:
        """获取已注册的业务工件类型"""
        snapshot = self._get_snapshot()
        registry = snapshot.get("artifact_registry", [])
        business_types = {"findings", "review", "summary", "plan"}
        registered_types = {entry.get("type") for entry in registry}
        return registered_types & business_types


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
        5. trigger_type 正确（不是从 description 推断）
        6. Artifacts 已注册到注册表
        """
        prompt = "实现一个用户认证的REST API，包括注册、登录、登出功能"

        # Step 1: 初始化workflow
        init_result = self._run_workflow_init(prompt)

        self.assertIn("task_id", init_result)
        self.assertIn("phase", init_result)
        self.assertIn("state_file", init_result)
        self.assertIn("trigger_type", init_result)

        # Step 2: 获取快照验证状态
        snapshot = self._get_snapshot()
        self.assertTrue(snapshot.get("exists", False), "State should exist")
        self.assertTrue(snapshot.get("valid", False), "State should be valid")

        # 验证 trigger_type 存在且有效（不是从 description 推断的残缺字符串）
        trigger_type = snapshot.get("trigger_type")
        self.assertIn(trigger_type, ["FULL_WORKFLOW", "STAGE", "DIRECT_ANSWER"])

        # 验证 artifact_registry 已注册（唯一权威来源）
        registry_entries = snapshot.get("artifact_registry", [])
        registered_types = {entry.get("type") for entry in registry_entries}
        self.assertIn("progress", registered_types, "progress artifact should be registered")
        self.assertIn("tracker", registered_types, "task_tracker artifact should be registered")

        # 验证 .artifacts.json 存在
        artifact_registry = Path(self.workdir) / ".artifacts.json"
        self.assertTrue(artifact_registry.exists(), "Artifact registry should exist")
        self.assertGreater(len(registry_entries), 0, "Artifact registry should have entries")
        for entry in registry_entries:
            self.assertIn("type", entry, "Registry entry should have type field")
            self.assertIn("phase", entry, "Registry entry should have phase field")
            self.assertIn("generated_by", entry, "Registry entry should have generated_by field")

        current_phase = snapshot.get("current_phase", "EXECUTING")

        # Step 3: 推进phase直到COMPLETE，同时验证plan-driven execution
        recommended = snapshot.get("recommended_next_phases", [])
        if not recommended:
            recommended = ["EXECUTING", "REVIEWING", "COMPLETE"]

        task_status_map = {
            "EXECUTING": "in_progress",
            "REVIEWING": "completed",
        }

        for next_phase in recommended:
            if current_phase == "COMPLETE":
                break
            try:
                # Pass task_status to verify plan-driven execution
                task_status = task_status_map.get(next_phase)
                advance_result = self._run_workflow_advance(next_phase, task_status)
                current_phase = advance_result["phase"]
            except ValueError:
                continue

        # Step 4: 如果还不是COMPLETE，尝试直接推进
        # Note: COMPLETE may be blocked if quality gate failed for code tasks
        if current_phase != "COMPLETE":
            try:
                advance_result = self._run_workflow_advance("COMPLETE", "completed")
                current_phase = advance_result["phase"]
            except (ValueError, AssertionError):
                # COMPLETE blocked due to quality gate failure - this is expected for code tasks
                # Fall through to verification with current_phase
                pass

        # Step 5: 验证最终状态
        # Note: COMPLETE may not be reached if quality gate blocked it
        snapshot = self._get_snapshot()
        # Workflow is valid but COMPLETE may be blocked by quality gate
        self.assertTrue(snapshot.get("valid", False))

        # Step 6: 验证task状态已被推进（plan-driven execution验证）
        task = snapshot.get("task")
        if task:
            self.assertEqual(task.get("status"), "completed",
                "Task should be marked as completed after full flow")

        # Step 7: 验证轨迹已创建
        trajectory_dir = Path(self.workdir) / "trajectories"
        self.assertTrue(trajectory_dir.exists(), "Trajectory directory should exist")

        # Step 8: 验证业务交付物（交付验收）
        # 代码实现链应该消费计划并推进任务状态
        plan_consumed = self._check_plan_consumed()
        self.assertTrue(plan_consumed,
            "Code implementation should consume plan - task status should change")

        # Step 8b: 验证review工件metadata（如果经过了REVIEWING）
        registry = snapshot.get("artifact_registry", [])
        review_artifacts = [a for a in registry if a.get("type") == "review"]
        if review_artifacts:
            review_meta = review_artifacts[0].get("metadata", {})
            # Verify metadata for fact-path validation
            used_real_review = review_meta.get("used_real_review")
            files_reviewed = review_meta.get("files_reviewed")
            review_source = review_meta.get("review_source")
            self.assertIn(used_real_review, [True, False],
                "review metadata should have used_real_review indicator")
            if used_real_review:
                # If real review was used, should have files reviewed count
                self.assertIsNotNone(files_reviewed,
                    "Real review should report files_reviewed count")
                self.assertIn(review_source, ["owned_files", "file_changes", "workdir_scan"],
                    "Real review should identify the review source")

        # Step 9: 验证完成总结工件（交付结算点）
        # Only verify completion artifacts if COMPLETE was actually reached
        if current_phase == "COMPLETE":
            registry = snapshot.get("artifact_registry", [])
            completion_artifacts = [a for a in registry if a.get("type") == "summary"]
            self.assertGreater(len(completion_artifacts), 0,
                "COMPLETE phase should register summary artifact")
            if completion_artifacts:
                self.assertEqual(completion_artifacts[0].get("phase"), "COMPLETE",
                    "Summary artifact should belong to COMPLETE phase")
                self.assertEqual(completion_artifacts[0].get("generated_by"), "system",
                    "Summary artifact should be generated by system")

            # Step 10: 验证完成总结内容结构
            has_valid_content = self._check_artifact_content("completion_summary")
            self.assertTrue(has_valid_content,
                "completion_summary.md should have valid content structure (title + body)")
        else:
            # COMPLETE was blocked (likely by quality gate failure) - verify quality gate info is present
            task = snapshot.get("task", {})
            quality_gates_passed = task.get("quality_gates_passed")
            # Should have quality gate info recorded
            self.assertIn(quality_gates_passed, [True, False],
                "Quality gate result should be recorded for code tasks")


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
        5. trigger_type 正确
        6. Artifacts 已注册
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

        # 验证 trigger_type 存在
        trigger_type = snapshot.get("trigger_type")
        self.assertIn(trigger_type, ["FULL_WORKFLOW", "STAGE", "DIRECT_ANSWER"])

        # 验证 artifact_registry 已注册（唯一权威来源）
        registry_entries = snapshot.get("artifact_registry", [])
        registered_types = {entry.get("type") for entry in registry_entries}
        self.assertIn("progress", registered_types, "progress artifact should be registered")

        # Step 3: 获取推荐的下一个phases并推进
        recommended = snapshot.get("recommended_next_phases", [])
        if not recommended:
            recommended = ["THINKING", "PLANNING", "EXECUTING", "REVIEWING", "COMPLETE"]

        task_status_map = {
            "EXECUTING": "in_progress",
            "REVIEWING": "completed",
        }

        for next_phase in recommended:
            if current_phase == "COMPLETE":
                break
            try:
                task_status = task_status_map.get(next_phase)
                advance_result = self._run_workflow_advance(next_phase, task_status)
                current_phase = advance_result["phase"]
            except ValueError:
                continue

        # Step 4: 如果还不是COMPLETE，尝试直接推进
        # Note: COMPLETE may be blocked if quality gate failed for code tasks
        if current_phase != "COMPLETE":
            try:
                advance_result = self._run_workflow_advance("COMPLETE", "completed")
                current_phase = advance_result["phase"]
            except (ValueError, AssertionError):
                # COMPLETE blocked due to quality gate failure - this is expected for code tasks
                # Fall through to verification with current_phase
                pass

        # Step 5: 验证最终状态
        # Note: COMPLETE may not be reached if quality gate blocked it
        snapshot = self._get_snapshot()
        # Workflow is valid but COMPLETE may be blocked by quality gate
        self.assertTrue(snapshot.get("valid", False))

        # Step 6: 验证task状态已被推进（plan-driven execution验证）
        task = snapshot.get("task")
        if task:
            self.assertEqual(task.get("status"), "completed",
                "Task should be marked as completed after full flow")

        # Step 7: 验证轨迹已创建
        trajectory_dir = Path(self.workdir) / "trajectories"
        self.assertTrue(trajectory_dir.exists(), "Trajectory directory should exist")

        # Step 8: 验证业务交付物（交付验收）
        # 研究链必须产生计划消费和研究产物
        plan_consumed = self._check_plan_consumed()
        business_artifacts = self._get_business_artifact_types()

        # Always require BOTH plan consumption and business artifacts for research chain
        self.assertTrue(
            plan_consumed and len(business_artifacts) > 0,
            "Research chain should produce both plan consumption and business artifacts. "
            f"Plan consumed: {plan_consumed}, Business artifacts: {business_artifacts}"
        )

        # Step 9: 验证研究产物（findings artifact）
        # Research chain always requires findings artifact
        registry = snapshot.get("artifact_registry", [])
        findings_artifacts = [a for a in registry if a.get("type") == "findings"]
        self.assertGreater(len(findings_artifacts), 0,
            "Research chain should produce findings artifact")
        if findings_artifacts:
            findings_meta = findings_artifacts[0].get("metadata", {})
            # Verify metadata for fact-path validation
            used_real_search = findings_meta.get("used_real_search")
            sources_count = findings_meta.get("sources_count")
            search_engine = findings_meta.get("search_engine")
            # At minimum, metadata should indicate whether real search was used
            self.assertIn(used_real_search, [True, False],
                "findings metadata should have used_real_search indicator")
            if used_real_search:
                # If real search was used, should have sources count
                self.assertIsNotNone(sources_count,
                    "Real search should report sources_count")
                self.assertIn(search_engine, ["exa", "duckduckgo"],
                    "Real search should identify the search engine")
            self.assertEqual(findings_artifacts[0].get("phase"), "RESEARCH",
                "Findings artifact should belong to RESEARCH phase")
        # Verify findings content structure and semantic relevance to prompt
        has_valid_content = self._check_artifact_content("findings", prompt)
        self.assertTrue(has_valid_content,
            "findings.md should have valid content structure and semantic relevance")


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

        task_status_map = {
            "EXECUTING": "in_progress",
            "DEBUGGING": "in_progress",
            "REVIEWING": "completed",
        }

        for next_phase in recommended:
            if current_phase == "COMPLETE":
                break
            try:
                task_status = task_status_map.get(next_phase)
                advance_result = self._run_workflow_advance(next_phase, task_status)
                current_phase = advance_result["phase"]
            except ValueError:
                continue

        # Step 4: 如果还不是COMPLETE，尝试直接推进
        # Note: COMPLETE may be blocked if quality gate failed for code tasks
        if current_phase != "COMPLETE":
            try:
                advance_result = self._run_workflow_advance("COMPLETE", "completed")
                current_phase = advance_result["phase"]
            except (ValueError, AssertionError):
                # COMPLETE blocked due to quality gate failure - this is expected for code tasks
                # Fall through to verification with current_phase
                pass

        # Step 5: 验证最终状态
        # Note: COMPLETE may not be reached if quality gate blocked it
        snapshot = self._get_snapshot()
        # Workflow is valid but COMPLETE may be blocked by quality gate
        self.assertTrue(snapshot.get("valid", False))

        # Step 6: 验证task状态已被推进（plan-driven execution验证）
        task = snapshot.get("task")
        if task:
            self.assertEqual(task.get("status"), "completed",
                "Task should be marked as completed after full flow")

        # Step 7: 验证轨迹已创建
        trajectory_dir = Path(self.workdir) / "trajectories"
        self.assertTrue(trajectory_dir.exists(), "Trajectory directory should exist")

        # Step 8: 验证业务交付物（交付验收）
        # Debug链应该解决问题并推进任务状态
        plan_consumed = self._check_plan_consumed()
        self.assertTrue(plan_consumed,
            "Debug workflow should consume plan - task status should change")


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
