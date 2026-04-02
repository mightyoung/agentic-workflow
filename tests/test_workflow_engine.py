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

import workflow_engine  # noqa: E402
import unified_state  # noqa: E402


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
        self.assertTrue(result["plan_created"])
        self.assertTrue((Path(self.temp_dir) / "SESSION-STATE.md").exists())
        self.assertTrue((Path(self.temp_dir) / "progress.md").exists())
        self.assertTrue((Path(self.temp_dir) / "task_plan.md").exists())
        self.assertTrue((Path(self.temp_dir) / ".workflow_state.json").exists())
        self.assertTrue((Path(self.temp_dir) / ".task_tracker.json").exists())

        # Use unified state
        state = unified_state.load_state(self.temp_dir)
        self.assertEqual(state.phase.get("current"), "PLANNING")

    def test_initialize_direct_answer_does_not_create_task_tracker_entry(self):
        result = workflow_engine.initialize_workflow("hello", workdir=self.temp_dir)
        self.assertEqual(result["phase"], "DIRECT_ANSWER")

        tracker = json.loads((Path(self.temp_dir) / ".task_tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(tracker["tasks"], [])

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
        self.assertEqual(snapshot["next_plan_tasks"][0]["id"], "TASK-001")


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

    def _setup_code_task_with_gate(self, gate_value):
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
        self._setup_code_task_with_gate(True)
        result = workflow_engine.complete_workflow(workdir=self.temp_dir, final_state="completed")
        self.assertEqual(result["final_state"], "completed")

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
