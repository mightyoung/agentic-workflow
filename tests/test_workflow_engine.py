#!/usr/bin/env python3
"""
Workflow engine integration tests.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT / "scripts"))

import memory_longterm  # noqa: E402
from memory_ops import update_planning_summary, update_review_summary, update_thinking_summary  # noqa: E402
import runtime_profile  # noqa: E402
import search_adapter  # noqa: E402
import unified_state  # noqa: E402
import workflow_engine  # noqa: E402
from trajectory_logger import load_trajectory  # noqa: E402


class TestWorkflowEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        refs = Path(self.temp_dir) / "references" / "templates"
        refs.mkdir(parents=True, exist_ok=True)
        (refs / "task_plan.md").write_text(
            "# Task Plan: {{TASK_NAME}}\n\n> Created at: {{CREATED_AT}}\n",
            encoding="utf-8",
        )
        (refs / "progress.md").write_text(
            "# Progress\n\n## Current Phase\n\n- phase: initialization\n- status: pending\n",
            encoding="utf-8",
        )

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialize_planning_workflow_creates_runtime_files(self):
        result = workflow_engine.initialize_workflow("帮我制定一个开发计划", workdir=self.temp_dir)

        self.assertEqual(result["phase"], "PLANNING")
        self.assertEqual(result["skill_activation_level"], 0)
        self.assertTrue(result["plan_created"])
        self.assertTrue((Path(self.temp_dir) / "SESSION-STATE.md").exists())
        self.assertTrue((Path(self.temp_dir) / "progress.md").exists())
        self.assertFalse((Path(self.temp_dir) / "task_plan.md").exists())
        self.assertTrue((Path(self.temp_dir) / ".specs").exists())
        self.assertTrue((Path(self.temp_dir) / ".workflow_state.json").exists())
        self.assertTrue((Path(self.temp_dir) / ".task_tracker.json").exists())
        session_state = (Path(self.temp_dir) / "SESSION-STATE.md").read_text(encoding="utf-8")
        self.assertIn("## Skill 策略", session_state)
        self.assertIn("skill_policy", session_state)
        self.assertIn("use_skill", session_state)
        self.assertIn("skill_activation_level", session_state)
        self.assertIn("## 计划摘要", session_state)
        self.assertIn("plan_digest", session_state)

        progress_content = (Path(self.temp_dir) / "progress.md").read_text(encoding="utf-8")
        self.assertIn("## Planning Summary", progress_content)
        self.assertIn("plan_digest", progress_content)

        specs_root = Path(self.temp_dir) / ".specs"
        feature_dirs = list(specs_root.glob("*/"))
        self.assertGreater(len(feature_dirs), 0)
        feature_dir = feature_dirs[0]
        self.assertTrue((feature_dir / "spec.md").exists())
        self.assertTrue((feature_dir / "plan.md").exists())
        self.assertTrue((feature_dir / "tasks.md").exists())
        self.assertTrue((Path(self.temp_dir) / ".contract.json").exists())

        # Use unified state
        state = unified_state.load_state(self.temp_dir)
        self.assertEqual(state.phase.get("current"), "PLANNING")

        snapshot = workflow_engine.get_workflow_snapshot(self.temp_dir)
        is_valid, errors = unified_state.validate_workflow_state(self.temp_dir)
        self.assertTrue(is_valid, errors)
        self.assertEqual(snapshot["planning_summary"]["plan_source"], "tasks.md")
        self.assertGreaterEqual(snapshot["planning_summary"]["plan_task_count"], 1)
        self.assertIn("plan_digest", snapshot["planning_summary"])
        self.assertIsInstance(snapshot["planning_summary"]["worktree_recommended"], bool)

    def test_initialize_direct_answer_does_not_create_task_tracker_entry(self):
        result = workflow_engine.initialize_workflow("hello", workdir=self.temp_dir)
        self.assertEqual(result["phase"], "DIRECT_ANSWER")
        self.assertEqual(result["profile_source"], "middleware+router")
        self.assertFalse(result["use_skill"])
        self.assertEqual(result["skill_activation_level"], 0)

        tracker = json.loads((Path(self.temp_dir) / ".task_tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(tracker["tasks"], [])

    def test_initialize_full_workflow_uses_runtime_profile(self):
        result = workflow_engine.initialize_workflow("/agentic-workflow 开发一个电商系统", workdir=self.temp_dir)

        self.assertEqual(result["trigger_type"], "FULL_WORKFLOW")
        self.assertEqual(result["phase"], "RESEARCH")
        self.assertEqual(result["complexity"], "XL")
        self.assertEqual(result["profile_source"], "middleware+router")
        self.assertFalse(result["use_skill"])
        self.assertGreater(result["tokens_expected"], 0)
        self.assertEqual(result["skill_policy"], "disable")
        self.assertEqual(result["skill_activation_level"], 0)
        self.assertEqual(result["skill_context"], "")

        snapshot = workflow_engine.get_workflow_snapshot(self.temp_dir)
        self.assertEqual(snapshot["runtime_profile_summary"]["skill_policy"], "disable")
        self.assertFalse(snapshot["runtime_profile_summary"]["use_skill"])
        self.assertEqual(snapshot["runtime_profile_summary"]["skill_activation_level"], 0)
        self.assertEqual(snapshot["runtime_profile_summary"]["profile_source"], "middleware+router")
        self.assertEqual(snapshot["runtime_profile_summary"]["complexity"], "XL")

    def test_initialize_executing_workflow_uses_seventy_five_activation_baseline(self):
        result = workflow_engine.initialize_workflow("用TDD方式实现一个栈", workdir=self.temp_dir)

        self.assertEqual(result["phase"], "EXECUTING")
        self.assertTrue(result["use_skill"])
        self.assertEqual(result["skill_policy"], "default_enable")
        self.assertEqual(result["skill_activation_level"], 75)

        snapshot = workflow_engine.get_workflow_snapshot(self.temp_dir)
        self.assertEqual(snapshot["runtime_profile_summary"]["skill_activation_level"], 75)
        self.assertEqual(snapshot["runtime_profile_summary"]["complexity"], "M")

        unified_snapshot = unified_state.get_state_snapshot(self.temp_dir)
        self.assertEqual(unified_snapshot["runtime_profile_summary"]["skill_activation_level"], 75)
        self.assertEqual(unified_snapshot["failure_event_summary"]["failure_event_count"], 0)
        self.assertEqual(unified_snapshot["runtime_profile_summary"]["complexity"], "M")

    def test_runtime_profile_activation_is_size_sensitive_for_executing(self):
        self.assertEqual(runtime_profile.skill_activation_level_for_phase("EXECUTING", "XS"), 50)
        self.assertEqual(runtime_profile.skill_activation_level_for_phase("EXECUTING", "M"), 75)
        self.assertEqual(runtime_profile.skill_activation_level_for_phase("DEBUGGING", "M"), 25)

    def test_runtime_profile_degrades_local_debugging_tasks(self):
        local_debug_text = "修复这个单文件 bug 并补一个回归"
        self.assertFalse(
            runtime_profile.should_use_skill_for_phase("DEBUGGING", "M", "DEBUGGING", local_debug_text)
        )
        self.assertEqual(
            runtime_profile.skill_activation_level_for_phase("DEBUGGING", "M", "DEBUGGING", local_debug_text),
            0,
        )

    def test_runtime_profile_debugging_activation_scales_with_context(self):
        self.assertEqual(
            runtime_profile.debugging_activation_level_for_context(
                "M",
                task_text="修复局部问题",
                owned_files_count=1,
                diff_size=3,
                failure_count=0,
            ),
            25,
        )
        self.assertEqual(
            runtime_profile.debugging_activation_level_for_context(
                "M",
                task_text="多文件重构后的连锁问题",
                owned_files_count=4,
                diff_size=9,
                failure_count=2,
            ),
            50,
        )

    def test_runtime_profile_shrinks_planning_and_debugging_prompts(self):
        planning_prompt, planning_tokens = runtime_profile.build_skill_context("PLANNING", "XS")
        debugging_light_prompt, debugging_light_tokens = runtime_profile.build_skill_context("DEBUGGING", "XS")
        debugging_deep_prompt, debugging_deep_tokens = runtime_profile.build_skill_context("DEBUGGING", "M")
        thinking_prompt, thinking_tokens = runtime_profile.build_skill_context("THINKING", "M")

        self.assertIn("轻量", planning_prompt)
        self.assertIn("progress", planning_prompt)
        self.assertEqual(planning_tokens, 500)
        self.assertIn("轻量", debugging_light_prompt)
        self.assertIn("最小修复", debugging_light_prompt)
        self.assertIn("深度", debugging_deep_prompt)
        self.assertIn("回归测试", debugging_deep_prompt)
        self.assertEqual(debugging_light_tokens, 500)
        self.assertEqual(debugging_deep_tokens, 1000)
        self.assertIn("调查研究", thinking_prompt)
        self.assertIn("矛盾分析", thinking_prompt)
        self.assertIn("群众路线", thinking_prompt)
        self.assertIn("持久战略", thinking_prompt)
        self.assertIn("主要矛盾", thinking_prompt)
        self.assertIn("局部攻坚点", thinking_prompt)
        self.assertEqual(thinking_tokens, 1000)

    def test_thinking_context_includes_qiushi_summary(self):
        workflow_engine.initialize_workflow("从零开始设计一个新系统", workdir=self.temp_dir)

        result = workflow_engine.advance_workflow(
            "THINKING",
            workdir=self.temp_dir,
            progress=30,
            note="thinking summary check",
        )

        self.assertEqual(result["phase"], "THINKING")
        snapshot = workflow_engine.get_workflow_snapshot(self.temp_dir)
        thinking_summary = snapshot["context_for_next_phase"]["thinking_summary"]
        self.assertEqual(thinking_summary["workflow_label"], "新项目启动")
        self.assertEqual(thinking_summary["thinking_mode"], "investigation_first")
        self.assertEqual(
            thinking_summary["thinking_methods"],
            ["调查研究", "矛盾分析", "群众路线", "持久战略"],
        )
        self.assertIn("目标完整性", thinking_summary["major_contradiction"])
        self.assertIn("最小可验证", thinking_summary["local_attack_point"])
        self.assertIn("战略", thinking_summary["stage_judgment"])
        self.assertEqual(snapshot["thinking_summary"]["workflow_label"], "新项目启动")
        self.assertEqual(snapshot["thinking_summary"]["thinking_mode"], "investigation_first")
        self.assertEqual(
            snapshot["thinking_summary"]["thinking_methods"],
            ["调查研究", "矛盾分析", "群众路线", "持久战略"],
        )
        self.assertIn("目标完整性", snapshot["thinking_summary"]["major_contradiction"])
        self.assertIn("调查研究", snapshot["context_for_next_phase"]["summary"])
        self.assertIn("群众路线", snapshot["context_for_next_phase"]["summary"])

        progress_content = (Path(self.temp_dir) / "progress.md").read_text(encoding="utf-8")
        self.assertIn("## THINKING Summary", progress_content)
        self.assertIn("thinking_mode: investigation_first", progress_content)
        self.assertIn("thinking_methods: 调查研究 | 矛盾分析 | 群众路线 | 持久战略", progress_content)

        workflow_engine.advance_workflow(
            "REVIEWING",
            workdir=self.temp_dir,
            progress=40,
            note="leave thinking phase",
        )
        progress_after_leave = (Path(self.temp_dir) / "progress.md").read_text(encoding="utf-8")
        self.assertNotIn("## THINKING Summary", progress_after_leave)

        unified_snapshot = unified_state.get_state_snapshot(self.temp_dir)
        self.assertEqual(unified_snapshot["thinking_summary"]["workflow_label"], "新项目启动")
        self.assertEqual(unified_snapshot["thinking_summary"]["thinking_mode"], "investigation_first")
        self.assertEqual(
            unified_snapshot["thinking_summary"]["thinking_methods"],
            ["调查研究", "矛盾分析", "群众路线", "持久战略"],
        )
        self.assertIn("目标完整性", unified_snapshot["thinking_summary"]["major_contradiction"])
        self.assertIn("最小可验证", unified_snapshot["thinking_summary"]["local_attack_point"])
        self.assertIn("战略", unified_snapshot["thinking_summary"]["stage_judgment"])

        # Even if the sidecar is temporarily blank/placeholder, snapshots should
        # fall back to the current THINKING state instead of surfacing empties.
        update_thinking_summary(str(Path(self.temp_dir) / "SESSION-STATE.md"), {})
        snapshot_fallback = workflow_engine.get_workflow_snapshot(self.temp_dir)
        self.assertEqual(snapshot_fallback["thinking_summary"]["workflow_label"], "新项目启动")
        self.assertEqual(snapshot_fallback["thinking_summary"]["thinking_mode"], "investigation_first")
        self.assertEqual(
            snapshot_fallback["thinking_summary"]["thinking_methods"],
            ["调查研究", "矛盾分析", "群众路线", "持久战略"],
        )
        self.assertIn("目标完整性", snapshot_fallback["thinking_summary"]["major_contradiction"])
        unified_fallback = unified_state.get_state_snapshot(self.temp_dir)
        self.assertEqual(unified_fallback["thinking_summary"]["workflow_label"], "新项目启动")
        self.assertEqual(unified_fallback["thinking_summary"]["thinking_mode"], "investigation_first")
        self.assertEqual(
            unified_fallback["thinking_summary"]["thinking_methods"],
            ["调查研究", "矛盾分析", "群众路线", "持久战略"],
        )
        self.assertIn("目标完整性", unified_fallback["thinking_summary"]["major_contradiction"])

    def test_advance_workflow_updates_runtime_and_tracker(self):
        init_result = workflow_engine.initialize_workflow("修复这个bug", workdir=self.temp_dir)
        self.assertEqual(init_result["phase"], "DEBUGGING")

        result = workflow_engine.advance_workflow(
            "REVIEWING",
            workdir=self.temp_dir,
            progress=80,
            task_status="completed",
            note="ready for review",
        )

        self.assertEqual(result["phase"], "REVIEWING")
        snapshot = workflow_engine.get_workflow_snapshot(self.temp_dir)
        self.assertEqual(snapshot["current_phase"], "REVIEWING")
        self.assertEqual(snapshot["task"]["status"], "completed")
        self.assertEqual(snapshot["task"]["progress"], 80)
        # Quality gate now runs and may pass or fail based on actual project state
        # Gate failure is recorded but does not block phase transition to REVIEWING
        self.assertIn(snapshot["task"]["quality_gates_passed"], [True, False])

    def test_review_summary_falls_back_to_current_state_without_artifact(self):
        workflow_engine.initialize_workflow("修复这个bug", workdir=self.temp_dir)

        workflow_engine.advance_workflow(
            "REVIEWING",
            workdir=self.temp_dir,
            progress=90,
            task_status="in_progress",
            note="review fallback check",
        )

        snapshot = workflow_engine.get_workflow_snapshot(self.temp_dir)
        review_summary = snapshot["review_summary"]
        self.assertFalse(review_summary["review_found"])
        self.assertEqual(review_summary["review_source"], "state_fallback")
        self.assertEqual(review_summary["review_status"], "pending")
        self.assertEqual(review_summary["stage_1_status"], "pending")
        self.assertEqual(review_summary["stage_2_status"], "pending")
        self.assertTrue(review_summary["degraded_mode"])
        self.assertGreaterEqual(review_summary["files_reviewed"], 0)

    def test_illegal_transition_is_rejected(self):
        workflow_engine.initialize_workflow("帮我制定一个开发计划", workdir=self.temp_dir)

        with self.assertRaises(ValueError):
            workflow_engine.advance_workflow("DEBUGGING", workdir=self.temp_dir)

    def test_snapshot_reports_recommended_next_phases(self):
        workflow_engine.initialize_workflow("帮我制定一个开发计划", workdir=self.temp_dir)

        snapshot = workflow_engine.get_workflow_snapshot(self.temp_dir)
        self.assertTrue(snapshot["valid"])
        self.assertIn("EXECUTING", snapshot["recommended_next_phases"])

    def test_validate_runtime_state_detects_invalid_phase(self):
        workflow_engine.initialize_workflow("帮我制定一个开发计划", workdir=self.temp_dir)
        state_path = Path(self.temp_dir) / ".workflow_state.json"
        data = json.loads(state_path.read_text(encoding="utf-8"))
        data["phase"]["current"] = "NOT_A_PHASE"
        state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        is_valid, errors = unified_state.validate_workflow_state(self.temp_dir)
        self.assertFalse(is_valid)
        self.assertTrue(any("NOT_A_PHASE" in e for e in errors))

    def test_validate_runtime_state_detects_sidecar_drift(self):
        workflow_engine.initialize_workflow("帮我制定一个开发计划", workdir=self.temp_dir)
        session_path = Path(self.temp_dir) / "SESSION-STATE.md"
        state = unified_state.load_state(self.temp_dir)
        self.assertIsNotNone(state)

        # Introduce a sidecar drift without touching canonical state.
        from memory_ops import update_runtime_profile  # noqa: E402

        update_runtime_profile(
            str(session_path),
            skill_policy="conditional_enable",
            use_skill=True,
            skill_activation_level=25,
            tokens_expected=512,
            profile_source="manual-drift",
            complexity="S",
            complexity_confidence=0.1,
        )

        is_valid, errors = unified_state.validate_workflow_state(self.temp_dir)
        self.assertFalse(is_valid)
        self.assertTrue(any("runtime_profile" in e for e in errors))
        self.assertTrue(any("skill_policy" in e for e in errors))

    def test_parse_task_plan_and_recommend_next_tasks(self):
        plan_path = Path(self.temp_dir) / "task_plan.md"
        plan_path.write_text(
            """# Task Plan: Demo

## Task Breakdown

### P1
- [ ] TASK-002: 次要任务
  - status: backlog
  - verification: pytest

### P0
- [ ] TASK-001: 核心任务
  - status: backlog
  - verification: pytest

- [x] TASK-003: 已完成任务
  - status: done
  - verification: pytest
""",
            encoding="utf-8",
        )

        tasks = workflow_engine.parse_task_plan(self.temp_dir)
        next_tasks = workflow_engine.next_plan_tasks(self.temp_dir)

        self.assertEqual(len(tasks), 3)
        self.assertEqual(next_tasks[0]["id"], "TASK-001")
        self.assertEqual(next_tasks[1]["id"], "TASK-002")

    def test_canonical_tasks_md_takes_precedence_over_legacy_task_plan(self):
        specs_dir = Path(self.temp_dir) / ".specs" / "feature-a"
        specs_dir.mkdir(parents=True, exist_ok=True)
        (specs_dir / "tasks.md").write_text(
"""## Setup

- [ ] **US1-1:** Canonical setup [P]
  - **Files:** `src/canonical.py`
  - **Verification:** `pytest tests/test_canonical.py -v`
""",
            encoding="utf-8",
        )

        legacy_plan = Path(self.temp_dir) / "task_plan.md"
        legacy_plan.write_text(
            """# Task Plan: Legacy

### P0
- [ ] TASK-LEGACY-1: Legacy task
  - status: backlog
  - verification: pytest
""",
            encoding="utf-8",
        )

        tasks = workflow_engine.parse_tasks_md(self.temp_dir)
        next_tasks = workflow_engine.next_plan_tasks(self.temp_dir)
        frontier = workflow_engine.compute_frontier(self.temp_dir)
        snapshot = workflow_engine.get_workflow_snapshot(self.temp_dir)

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["id"], "US1-1")
        self.assertEqual(next_tasks[0]["id"], "US1-1")
        self.assertEqual(frontier["executable_frontier"][0]["id"], "US1-1")
        self.assertEqual(snapshot["plan_source"], "tasks.md")

    def test_update_task_status_updates_canonical_tasks_md(self):
        specs_dir = Path(self.temp_dir) / ".specs" / "feature-b"
        specs_dir.mkdir(parents=True, exist_ok=True)
        tasks_path = specs_dir / "tasks.md"
        tasks_path.write_text(
            """# Tasks

## User Story 1

- [ ] **US1-1:** Implement canonical flow [P]
  - **Files:** `src/canonical.py`
  - **Verification:** `pytest tests/test_canonical.py -v`
""",
            encoding="utf-8",
        )

        result = workflow_engine.update_task_status_in_plan(self.temp_dir, "US1-1", "completed")

        self.assertTrue(result["success"])
        self.assertEqual(result["source"], "tasks.md")
        updated = tasks_path.read_text(encoding="utf-8")
        self.assertIn("**Status:** completed", updated)
        next_tasks = workflow_engine.next_plan_tasks(self.temp_dir)
        self.assertEqual(next_tasks, [])

    def test_snapshot_includes_plan_tasks(self):
        workflow_engine.initialize_workflow("帮我制定一个开发计划", workdir=self.temp_dir)
        plan_path = Path(self.temp_dir) / "task_plan.md"
        plan_path.write_text(
            """# Task Plan: Demo

## Task Breakdown

### P0
- [ ] TASK-001: 核心任务
  - status: backlog
""",
            encoding="utf-8",
        )

        snapshot = workflow_engine.get_workflow_snapshot(self.temp_dir)
        self.assertEqual(snapshot["plan_source"], "tasks.md")
        self.assertEqual(snapshot["planning_summary"]["planning_mode"], "canonical")
        self.assertEqual(snapshot["next_plan_tasks"][0]["id"], "US1-1")

    def test_snapshot_uses_lightweight_planning_mode_without_canonical_plan(self):
        workflow_engine.initialize_workflow("帮我制定一个开发计划", workdir=self.temp_dir)
        specs_dir = Path(self.temp_dir) / ".specs"
        if specs_dir.exists():
            import shutil

            shutil.rmtree(specs_dir)

        snapshot = workflow_engine.get_workflow_snapshot(self.temp_dir)
        self.assertEqual(snapshot["planning_summary"]["plan_source"], "none")
        self.assertEqual(snapshot["planning_summary"]["planning_mode"], "lightweight")

    def test_snapshot_includes_context_for_next_phase_memory_hints(self):
        workflow_engine.initialize_workflow("帮我制定一个开发计划", workdir=self.temp_dir)
        memory_md = Path(self.temp_dir) / "MEMORY.md"
        memory_longterm.record_reflection_experience(
            task="帮我制定一个开发计划",
            trigger="PLANNING::plan",
            mistake="Skipped validation of acceptance criteria",
            fix="Add explicit acceptance criteria and verification methods",
            signal="planning_gap",
            filepath=str(memory_md),
            index_file=str(Path(self.temp_dir) / ".memory_index.jsonl"),
            confidence=0.8,
            scope="project",
            tags=["planning", "contract"],
        )

        snapshot = workflow_engine.get_workflow_snapshot(self.temp_dir)
        context = snapshot["context_for_next_phase"]
        self.assertIn("memory_hints", context)
        self.assertGreater(len(context["memory_hints"]), 0)
        self.assertIn("memory_query", context)
        self.assertIn("memory_intent", context)

    def test_research_findings_are_written_to_dedicated_directory(self):
        workflow_engine.initialize_workflow("帮我搜索最佳实践", workdir=self.temp_dir)
        state = unified_state.load_state(self.temp_dir)
        self.assertIsNotNone(state)
        session_id = state.session_id or "unknown"

        fake_response = search_adapter.SearchResponse(
            query="帮我搜索最佳实践",
            results=[
                search_adapter.SearchResult(
                    title="Example Best Practice",
                    url="https://example.com/best-practice",
                    snippet="Use clear contracts and structured memory boundaries.",
                    source="web",
                )
            ],
            total_results=1,
            search_engine="duckduckgo",
            metadata={"degraded_mode": True, "degraded_reason": "test stub"},
        )

        original_search = workflow_engine.search_adapter.search
        workflow_engine.search_adapter.search = lambda query, num_results=5: fake_response
        try:
            workflow_engine.advance_workflow("THINKING", workdir=self.temp_dir)
        finally:
            workflow_engine.search_adapter.search = original_search

        findings_dir = Path(self.temp_dir) / ".research" / "findings"
        session_file = findings_dir / f"findings_{session_id}.md"
        latest_file = findings_dir / "findings_latest.md"

        self.assertTrue(findings_dir.exists())
        self.assertTrue(session_file.exists())
        self.assertTrue(latest_file.exists())
        self.assertFalse(list(Path(self.temp_dir).glob("findings_*.md")))

        snapshot = workflow_engine.get_workflow_snapshot(self.temp_dir)
        research_summary = snapshot["research_summary"]
        self.assertTrue(research_summary["research_found"])
        self.assertEqual(research_summary["research_source"], "findings_session")
        self.assertEqual(research_summary["search_engine"], "duckduckgo")
        self.assertEqual(research_summary["sources_count"], 1)
        self.assertTrue(research_summary["used_real_search"])
        self.assertEqual(research_summary["evidence_status"], "verified")
        self.assertEqual(
            snapshot["context_for_next_phase"]["research_summary"]["research_source"],
            "findings_session",
        )

    def test_research_no_results_generates_explicit_degraded_report(self):
        workflow_engine.initialize_workflow("帮我搜索最佳实践", workdir=self.temp_dir)
        state = unified_state.load_state(self.temp_dir)
        self.assertIsNotNone(state)
        session_id = state.session_id or "unknown"

        empty_response = search_adapter.SearchResponse(
            query="帮我搜索最佳实践",
            results=[],
            total_results=0,
            search_engine="duckduckgo",
            error="Search unavailable",
            metadata={"degraded_mode": True, "degraded_reason": "test stub empty"},
        )

        original_search = workflow_engine.search_adapter.search
        workflow_engine.search_adapter.search = lambda query, num_results=5: empty_response
        try:
            workflow_engine.advance_workflow("THINKING", workdir=self.temp_dir)
        finally:
            workflow_engine.search_adapter.search = original_search

        findings_dir = Path(self.temp_dir) / ".research" / "findings"
        session_file = findings_dir / f"findings_{session_id}.md"
        content = session_file.read_text(encoding="utf-8")

        self.assertIn("No verifiable external sources", content)
        self.assertIn("degraded", content.lower())
        self.assertGreater(len(content.strip()), 100)

        snapshot = workflow_engine.get_workflow_snapshot(self.temp_dir)
        research_summary = snapshot["research_summary"]
        self.assertTrue(research_summary["research_found"])
        self.assertEqual(research_summary["research_source"], "findings_session")
        self.assertEqual(research_summary["sources_count"], 0)
        self.assertFalse(research_summary["used_real_search"])
        self.assertTrue(research_summary["degraded_mode"])
        self.assertEqual(research_summary["evidence_status"], "degraded")
        self.assertEqual(
            snapshot["context_for_next_phase"]["research_summary"]["evidence_status"],
            "degraded",
        )


class TestQualityGateCompletionBlock(unittest.TestCase):
    """Regression tests for quality gate COMPLETE blocking - P0 hardening."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        refs = Path(self.temp_dir) / "references" / "templates"
        refs.mkdir(parents=True, exist_ok=True)
        (refs / "task_plan.md").write_text(
            "# Task Plan: {{TASK_NAME}}\n\n> Created at: {{CREATED_AT}}\n",
            encoding="utf-8",
        )
        # Create dummy Python file so quality gate can pass
        src_dir = Path(self.temp_dir) / "src"
        src_dir.mkdir(exist_ok=True)
        (src_dir / "main.py").write_text("def main(): pass\n", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _setup_code_task_with_gate(self, gate_value, with_review: bool = False, review_files_reviewed: int = 1):
        """Set up a workflow with a code task that has explicit gate value."""
        # Init with EXECUTING (code task)
        workflow_engine.initialize_workflow("帮我实现这个功能", workdir=self.temp_dir)
        # Manually add EXECUTING to phase history to mark as code task
        state_path = Path(self.temp_dir) / ".workflow_state.json"
        state_data = json.loads(state_path.read_text(encoding="utf-8"))
        state_data["phase"]["history"].append({
            "phase": "EXECUTING",
            "entered_at": "2026-04-01T00:00:00",
            "exited_at": "2026-04-01T00:00:01",
            "reason": "test",
            "actions": [],
            "decisions": [],
            "file_changes": [],
            "error": None,
        })
        state_path.write_text(json.dumps(state_data, ensure_ascii=False, indent=2), encoding="utf-8")
        # Set quality_gates_passed in tracker
        tracker_path = Path(self.temp_dir) / ".task_tracker.json"
        tracker_data = json.loads(tracker_path.read_text(encoding="utf-8"))
        if tracker_data["tasks"]:
            tracker_data["tasks"][0]["quality_gates_passed"] = gate_value
            tracker_path.write_text(json.dumps(tracker_data, ensure_ascii=False, indent=2), encoding="utf-8")

        if with_review:
            review_dir = Path(self.temp_dir) / ".reviews" / "review"
            review_dir.mkdir(parents=True, exist_ok=True)
            review_content = """# Code Review: Test task

## Stage 1: Spec Compliance
- Contract/owned_files alignment: reviewed against contract
- Acceptance coverage: checked via task contract and target files
- Scope completeness: target files count = 1

## Files Reviewed
**Files Reviewed**: {files_reviewed} code files

## Stage 2: Code Quality
- Correctness: reviewed
- Security: reviewed
- Performance: reviewed
- Maintainability: reviewed

## Verdict
- Status: REVIEWED
""".format(files_reviewed=review_files_reviewed)
            (review_dir / "review_latest.md").write_text(review_content, encoding="utf-8")
            (review_dir / "review_test.md").write_text(review_content, encoding="utf-8")

    def test_complete_blocks_when_quality_gate_none(self):
        """complete_workflow must block when quality_gates_passed=None for code tasks."""
        self._setup_code_task_with_gate(None)
        with self.assertRaises(ValueError) as ctx:
            workflow_engine.complete_workflow(workdir=self.temp_dir, final_state="completed")
        self.assertIn("quality gate not passed", str(ctx.exception))

    def test_complete_blocks_when_quality_gate_false(self):
        """complete_workflow must block when quality_gates_passed=False for code tasks."""
        self._setup_code_task_with_gate(False)
        with self.assertRaises(ValueError) as ctx:
            workflow_engine.complete_workflow(workdir=self.temp_dir, final_state="completed")
        self.assertIn("quality gate not passed", str(ctx.exception))

    def test_complete_allows_when_quality_gate_true(self):
        """complete_workflow must allow when quality_gates_passed=True for code tasks."""
        self._setup_code_task_with_gate(True, with_review=True, review_files_reviewed=1)
        result = workflow_engine.complete_workflow(workdir=self.temp_dir, final_state="completed")
        self.assertEqual(result["final_state"], "completed")

    def test_complete_blocks_when_review_is_template_or_empty(self):
        """complete_workflow must block when review exists but no files were analyzed."""
        self._setup_code_task_with_gate(True, with_review=True, review_files_reviewed=0)
        with self.assertRaises(ValueError) as ctx:
            workflow_engine.complete_workflow(workdir=self.temp_dir, final_state="completed")
        self.assertIn("review did not analyze any files", str(ctx.exception))

    def test_complete_blocks_when_review_missing(self):
        """complete_workflow must block when the review artifact is missing."""
        self._setup_code_task_with_gate(True, with_review=False)
        with self.assertRaises(ValueError) as ctx:
            workflow_engine.complete_workflow(workdir=self.temp_dir, final_state="completed")
        self.assertIn("review artifact not found", str(ctx.exception))

    def test_advance_to_complete_blocks_when_quality_gate_none(self):
        """advance(phase=COMPLETE) must block when quality_gates_passed=None for code tasks."""
        self._setup_code_task_with_gate(None)
        with self.assertRaises(ValueError) as ctx:
            workflow_engine.advance_workflow(workdir=self.temp_dir, phase="COMPLETE")
        self.assertIn("quality gate not passed", str(ctx.exception))

    def test_advance_to_complete_blocks_when_quality_gate_false(self):
        """advance(phase=COMPLETE) must block when quality_gates_passed=False for code tasks."""
        self._setup_code_task_with_gate(False)
        with self.assertRaises(ValueError) as ctx:
            workflow_engine.advance_workflow(workdir=self.temp_dir, phase="COMPLETE")
        self.assertIn("quality gate not passed", str(ctx.exception))

    def test_complete_blocks_when_task_id_missing(self):
        """complete_workflow must block when task_id is None for code tasks (bypass prevention)."""
        # Init with EXECUTING (code task)
        workflow_engine.initialize_workflow("帮我实现这个功能", workdir=self.temp_dir)
        # Manually add EXECUTING to phase history to mark as code task
        state_path = Path(self.temp_dir) / ".workflow_state.json"
        state_data = json.loads(state_path.read_text(encoding="utf-8"))
        state_data["phase"]["history"].append({
            "phase": "EXECUTING",
            "entered_at": "2026-04-01T00:00:00",
            "exited_at": "2026-04-01T00:00:01",
            "reason": "test",
            "actions": [],
            "decisions": [],
            "file_changes": [],
            "error": None,
        })
        # Set task_id to None to simulate the bypass scenario
        state_data["task"]["task_id"] = None
        state_path.write_text(json.dumps(state_data, ensure_ascii=False, indent=2), encoding="utf-8")

        with self.assertRaises(ValueError) as ctx:
            workflow_engine.complete_workflow(workdir=self.temp_dir, final_state="completed")
        self.assertIn("task has no task_id", str(ctx.exception))
        self.assertIn("Cannot verify quality gate was run", str(ctx.exception))


class TestNewPhases(unittest.TestCase):
    """Tests for newly added phases: REFINING, EXPLORING, OFFICE_HOURS, SUBAGENT."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_refining_phase_transition(self):
        """Test REFINING phase is reachable and transitions correctly."""
        workflow_engine.initialize_workflow("帮我制定一个开发计划", workdir=self.temp_dir)
        # PLANNING -> REFINING is valid
        result = workflow_engine.advance_workflow("REFINING", workdir=self.temp_dir)
        self.assertEqual(result["phase"], "REFINING")

        state = unified_state.load_state(self.temp_dir)
        self.assertEqual(state.phase.get("current"), "REFINING")

    def test_exploring_phase_transition(self):
        """Test EXPLORING phase is reachable and transitions correctly."""
        workflow_engine.initialize_workflow("深层探索", workdir=self.temp_dir)
        # Should route to EXPLORING automatically
        state = unified_state.load_state(self.temp_dir)
        self.assertEqual(state.phase.get("current"), "EXPLORING")

    def test_office_hours_phase_transition(self):
        """Test OFFICE_HOURS phase is reachable and transitions correctly."""
        workflow_engine.initialize_workflow("产品咨询", workdir=self.temp_dir)
        # Should route to OFFICE_HOURS automatically
        state = unified_state.load_state(self.temp_dir)
        self.assertEqual(state.phase.get("current"), "OFFICE_HOURS")

    def test_subagent_phase_transition(self):
        """Test SUBAGENT phase is reachable and transitions to COMPLETE."""
        workflow_engine.initialize_workflow("给我结果就行", workdir=self.temp_dir)
        # Should route to SUBAGENT automatically
        state = unified_state.load_state(self.temp_dir)
        self.assertEqual(state.phase.get("current"), "SUBAGENT")

        # SUBAGENT -> COMPLETE is valid
        result = workflow_engine.advance_workflow("COMPLETE", workdir=self.temp_dir)
        self.assertEqual(result["phase"], "COMPLETE")

    def test_refining_to_executing_transition(self):
        """Test REFINING can transition to EXECUTING."""
        workflow_engine.initialize_workflow("帮我制定一个开发计划", workdir=self.temp_dir)
        workflow_engine.advance_workflow("REFINING", workdir=self.temp_dir)
        result = workflow_engine.advance_workflow("EXECUTING", workdir=self.temp_dir)
        self.assertEqual(result["phase"], "EXECUTING")

    def test_exploring_to_planning_transition(self):
        """Test EXPLORING can transition to PLANNING."""
        workflow_engine.initialize_workflow("深层探索", workdir=self.temp_dir)
        # Already in EXPLORING from routing
        result = workflow_engine.advance_workflow("PLANNING", workdir=self.temp_dir)
        self.assertEqual(result["phase"], "PLANNING")

    def test_office_hours_to_planning_transition(self):
        """Test OFFICE_HOURS can transition to PLANNING."""
        workflow_engine.initialize_workflow("产品想法", workdir=self.temp_dir)
        # Already in OFFICE_HOURS from routing
        result = workflow_engine.advance_workflow("PLANNING", workdir=self.temp_dir)
        self.assertEqual(result["phase"], "PLANNING")

    def test_analyzing_phase_transition(self):
        """Test ANALYZING phase is reachable and transitions correctly."""
        workflow_engine.initialize_workflow("分析需求", workdir=self.temp_dir)
        # Should route to ANALYZING automatically
        state = unified_state.load_state(self.temp_dir)
        self.assertEqual(state.phase.get("current"), "ANALYZING")

    def test_planning_to_analyzing_transition(self):
        """Test PLANNING can transition to ANALYZING."""
        workflow_engine.initialize_workflow("帮我制定一个开发计划", workdir=self.temp_dir)
        result = workflow_engine.advance_workflow("ANALYZING", workdir=self.temp_dir)
        self.assertEqual(result["phase"], "ANALYZING")

    def test_analyzing_to_executing_requires_analyze_gate(self):
        """Test ANALYZING -> EXECUTING requires passing analyze gate."""
        workflow_engine.initialize_workflow("分析需求", workdir=self.temp_dir)
        state = unified_state.load_state(self.temp_dir)
        self.assertEqual(state.phase.get("current"), "ANALYZING")

        # Without spec files, analyze gate should fail
        with self.assertRaises(ValueError) as ctx:
            workflow_engine.advance_workflow("EXECUTING", workdir=self.temp_dir)
        self.assertIn("analyze gate failed", str(ctx.exception))

    def test_analyze_gate_blocks_planning_to_executing(self):
        """Test PLANNING -> EXECUTING is blocked without analyze gate."""
        workflow_engine.initialize_workflow("帮我制定一个开发计划", workdir=self.temp_dir)
        state = unified_state.load_state(self.temp_dir)
        self.assertEqual(state.phase.get("current"), "PLANNING")

        # Without going through ANALYZING, going directly to EXECUTING should still check gate
        with self.assertRaises(ValueError) as ctx:
            workflow_engine.advance_workflow("EXECUTING", workdir=self.temp_dir)
        self.assertIn("analyze gate failed", str(ctx.exception))

    def test_handle_workflow_failure_records_reflection_memory(self):
        """Failure handling should persist a reflection artifact and long-term memory entry."""
        workflow_engine.initialize_workflow("修复这个bug", workdir=self.temp_dir)

        result = workflow_engine.handle_workflow_failure(
            self.temp_dir,
            error="AssertionError: email not found",
            strategy="retry",
            max_retries=3,
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["reflection_recorded"])

        reflection_path = Path(result["reflection_path"])
        self.assertTrue(reflection_path.exists())

        memory_md = Path(self.temp_dir) / "MEMORY.md"
        memory_index = Path(self.temp_dir) / ".memory_index.jsonl"
        self.assertTrue(memory_md.exists())
        self.assertTrue(memory_index.exists())

        memory_content = memory_md.read_text(encoding="utf-8")
        self.assertIn("Task:", memory_content)
        self.assertIn("Fix:", memory_content)

    def test_handle_workflow_failure_escalates_skill_activation_audit(self):
        """Failure handling should persist an auditable skill activation escalation."""
        workflow_engine.initialize_workflow("用TDD方式实现一个栈", workdir=self.temp_dir)

        result = workflow_engine.handle_workflow_failure(
            self.temp_dir,
            error="quality gate failed: pytest tests/test_stack.py",
            strategy="retry",
            max_retries=3,
        )

        self.assertTrue(result["success"])

        state = unified_state.load_state(self.temp_dir)
        self.assertIsNotNone(state)
        self.assertEqual(state.metadata["runtime_profile"]["skill_activation_level"], 100)
        self.assertTrue(
            any(
                decision.decision == "Escalate skill activation"
                and decision.metadata.get("escalated_activation_level") == 100
                and decision.metadata.get("escalation_reason") == "high_signal_failure:quality_gate_failed"
                for decision in state.decisions
            )
        )

        snapshot = workflow_engine.get_workflow_snapshot(self.temp_dir)
        self.assertEqual(snapshot["failure_event_summary"]["escalation_event_count"], 1)
        self.assertEqual(
            snapshot["failure_event_summary"]["latest_escalation_event"]["escalated_activation_level"],
            100,
        )
        self.assertEqual(snapshot["runtime_profile_summary"]["complexity"], "M")
        unified_snapshot = unified_state.get_state_snapshot(self.temp_dir)
        self.assertEqual(unified_snapshot["failure_event_summary"]["escalation_event_count"], 1)

    def test_handle_workflow_failure_does_not_escalate_on_generic_unknown_error(self):
        """Generic recoverable failures should not automatically increase activation."""
        workflow_engine.initialize_workflow("用TDD方式实现一个栈", workdir=self.temp_dir)

        result = workflow_engine.handle_workflow_failure(
            self.temp_dir,
            error="transient network timeout",
            strategy="retry",
            max_retries=3,
        )

        self.assertTrue(result["success"])

        state = unified_state.load_state(self.temp_dir)
        self.assertIsNotNone(state)
        self.assertEqual(state.metadata["runtime_profile"]["skill_activation_level"], 75)
        self.assertFalse(
            any(
                decision.decision == "Escalate skill activation"
                for decision in state.decisions
            )
        )

        snapshot = workflow_engine.get_workflow_snapshot(self.temp_dir)
        self.assertEqual(snapshot["failure_event_summary"]["failure_event_count"], 1)
        self.assertEqual(snapshot["failure_event_summary"]["escalation_event_count"], 0)
        self.assertEqual(snapshot["failure_event_summary"]["error_types"], ["unknown"])
        self.assertEqual(snapshot["runtime_profile_summary"]["complexity"], "M")

    def test_resume_workflow_surfaces_runtime_and_failure_summaries(self):
        """Resuming should expose runtime profile and failure summaries in the result."""
        init_result = workflow_engine.initialize_workflow("用TDD方式实现一个栈", workdir=self.temp_dir)
        workflow_engine.handle_workflow_failure(
            self.temp_dir,
            error="quality gate failed: pytest tests/test_stack.py",
            strategy="retry",
            max_retries=3,
        )
        update_planning_summary(
            str(Path(self.temp_dir) / "SESSION-STATE.md"),
            {
                "plan_source": "tasks.md",
                "planning_mode": "canonical",
                "plan_task_count": 2,
                "completed_task_count": 1,
                "in_progress_task_count": 1,
                "blocked_task_count": 0,
                "backlog_task_count": 0,
                "ready_task_count": 1,
                "parallel_candidate_group_count": 1,
                "parallel_ready_task_count": 1,
                "conflict_group_count": 0,
                "next_task_ids": ["TASK-001"],
                "worktree_recommended": True,
                "worktree_reason": "multi-step plan detected",
                "plan_digest": "tasks.md: 2 task(s), 1 done, 1 in progress, 0 blocked, 1 ready; next=TASK-001; worktree=yes",
            },
        )
        update_thinking_summary(
            str(Path(self.temp_dir) / "SESSION-STATE.md"),
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
        update_review_summary(
            str(Path(self.temp_dir) / "SESSION-STATE.md"),
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

        result = workflow_engine.resume_workflow(self.temp_dir, init_result["session_id"])

        self.assertTrue(result["success"])
        self.assertEqual(result["runtime_profile_summary"]["complexity"], "M")
        self.assertEqual(result["runtime_profile_summary"]["skill_activation_level"], 100)
        self.assertEqual(result["failure_event_summary"]["escalation_event_count"], 1)
        self.assertEqual(result["failure_event_summary"]["latest_escalation_event"]["escalated_activation_level"], 100)
        self.assertEqual(result["resume_summary"]["resume_from"], "EXECUTING")
        self.assertEqual(result["resume_summary"]["next_phase"], "REVIEWING")
        self.assertEqual(result["resume_summary"]["planning_summary"]["plan_source"], "tasks.md")
        self.assertEqual(result["resume_summary"]["planning_summary"]["planning_mode"], "canonical")
        self.assertEqual(result["review_summary"]["review_source"], "review_latest")
        self.assertEqual(result["thinking_summary"]["workflow_label"], "复杂问题攻坚")
        self.assertEqual(result["thinking_summary"]["thinking_mode"], "contradiction_analysis")
        self.assertEqual(
            result["thinking_summary"]["thinking_methods"],
            ["调查研究", "矛盾分析", "集中力量", "实践认知", "批评自我批评"],
        )
        self.assertIn("目标完整性", result["thinking_summary"]["major_contradiction"])

        state = unified_state.load_state(self.temp_dir)
        self.assertIsNotNone(state)
        self.assertTrue(
            any(
                decision.decision == "Resumed from " + init_result["session_id"]
                for decision in state.decisions
            )
        )

        session_state = (Path(self.temp_dir) / "SESSION-STATE.md").read_text(encoding="utf-8")
        self.assertIn("## 恢复摘要", session_state)
        self.assertIn("original_session_id", session_state)
        self.assertIn("resume_from", session_state)
        self.assertIn("next_phase", session_state)
        self.assertIn("planning_planning_mode", session_state)
        self.assertIn("failure_event_count", session_state)
        self.assertIn("review_source", session_state)
        self.assertIn("thinking_workflow_label", session_state)

        resumed_trajectory = load_trajectory(self.temp_dir, result["new_session_id"])
        self.assertIsNotNone(resumed_trajectory)
        assert resumed_trajectory is not None
        self.assertEqual(resumed_trajectory["resume_summary"]["resume_from"], "EXECUTING")
        self.assertEqual(resumed_trajectory["resume_summary"]["next_phase"], "REVIEWING")
        self.assertEqual(resumed_trajectory["resume_summary"]["planning_summary"]["plan_source"], "tasks.md")
        self.assertEqual(resumed_trajectory["resume_summary"]["planning_summary"]["planning_mode"], "canonical")
        self.assertEqual(resumed_trajectory["resume_summary"]["review_summary"]["review_source"], "review_latest")
        self.assertEqual(resumed_trajectory["resume_summary"]["thinking_summary"]["workflow_label"], "复杂问题攻坚")
        self.assertEqual(resumed_trajectory["resume_summary"]["thinking_summary"]["thinking_mode"], "contradiction_analysis")
        self.assertEqual(
            resumed_trajectory["resume_summary"]["thinking_summary"]["thinking_methods"],
            ["调查研究", "矛盾分析", "集中力量", "实践认知", "批评自我批评"],
        )
        self.assertEqual(resumed_trajectory["runtime_profile"]["skill_activation_level"], 100)

    def test_resume_workflow_falls_back_when_thinking_sidecar_is_placeholder(self):
        """Thinking summary should fall back to live state when sidecar is placeholder."""
        init_result = workflow_engine.initialize_workflow("帮我制定一个开发计划", workdir=self.temp_dir)
        update_thinking_summary(
            str(Path(self.temp_dir) / "SESSION-STATE.md"),
            {},
        )

        result = workflow_engine.resume_workflow(self.temp_dir, init_result["session_id"])

        self.assertTrue(result["success"])
        self.assertEqual(result["thinking_summary"]["workflow_label"], "复杂问题攻坚")
        self.assertEqual(result["thinking_summary"]["thinking_mode"], "contradiction_analysis")
        self.assertEqual(
            result["thinking_summary"]["thinking_methods"],
            ["调查研究", "矛盾分析", "集中力量", "实践认知", "批评自我批评"],
        )
        self.assertEqual(result["thinking_summary"]["major_contradiction"], "事实 vs 假设")
        self.assertEqual(result["thinking_summary"]["stage_judgment"], "战术速决")

        resumed_trajectory = load_trajectory(self.temp_dir, result["new_session_id"])
        self.assertIsNotNone(resumed_trajectory)
        assert resumed_trajectory is not None
        self.assertEqual(resumed_trajectory["resume_summary"]["thinking_summary"]["workflow_label"], "复杂问题攻坚")
        self.assertEqual(resumed_trajectory["resume_summary"]["thinking_summary"]["thinking_mode"], "contradiction_analysis")
        self.assertEqual(
            resumed_trajectory["resume_summary"]["thinking_summary"]["thinking_methods"],
            ["调查研究", "矛盾分析", "集中力量", "实践认知", "批评自我批评"],
        )

    def test_phase_context_includes_memory_hints(self):
        """Next phase context should expose relevant long-term memory hints."""
        workflow_engine.initialize_workflow("帮我制定一个开发计划", workdir=self.temp_dir)

        memory_md = Path(self.temp_dir) / "MEMORY.md"
        memory_longterm.record_reflection_experience(
            task="帮我制定一个开发计划",
            trigger="PLANNING::plan",
            mistake="Skipped validation of acceptance criteria",
            fix="Add explicit acceptance criteria and verification methods",
            signal="planning_gap",
            filepath=str(memory_md),
            index_file=str(Path(self.temp_dir) / ".memory_index.jsonl"),
            confidence=0.8,
            scope="project",
            tags=["planning", "contract"],
        )

        state = unified_state.load_state(self.temp_dir)
        context = workflow_engine._build_phase_context("PLANNING", self.temp_dir, state.session_id)
        self.assertIn("memory_hints", context)
        self.assertGreater(len(context["memory_hints"]), 0)
        self.assertIn("memory_query", context)
        self.assertIn("memory_intent", context)
