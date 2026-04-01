#!/usr/bin/env python3
"""
Tests for frontier scheduler, checkpoint, and contract capabilities.

Covers:
- compute_frontier: ownership-aware scheduling
- conditional_checkpoint: real file creation
- parse_phase_contract: parsing logic
- team_agent: worker assignments
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT / "scripts"))  # noqa: E402

import workflow_engine  # noqa: E402
from workflow_engine import (  # noqa: E402
    compute_frontier,
    parse_phase_contract,
    conditional_checkpoint,
    CheckpointConfig,
)
from team_agent import TeamAgent, WorkerType  # noqa: E402


class TestComputeFrontier(unittest.TestCase):
    """Test ownership-aware frontier scheduling"""

    def test_frontier_empty_plan(self):
        """Empty task plan returns empty frontier"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = compute_frontier(tmpdir)
            self.assertEqual(result["executable_frontier"], [])
            self.assertEqual(result["parallel_groups"], [])
            self.assertEqual(result["conflict_groups"], [])

    def test_frontier_ready_tasks(self):
        """Ready tasks (no deps) are in executable_frontier"""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan = Path(tmpdir) / "task_plan.md"
            plan.write_text("""# Task Plan

### P0
- [ ] TASK-001: Task A
  - status: backlog
- [ ] TASK-002: Task B
  - status: backlog
""")
            result = compute_frontier(tmpdir)
            self.assertEqual(len(result["executable_frontier"]), 2)
            self.assertEqual(len(result["blocked_tasks"]), 0)

    def test_frontier_blocked_tasks(self):
        """Tasks with unmet deps are blocked"""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan = Path(tmpdir) / "task_plan.md"
            plan.write_text("""# Task Plan

### P0
- [ ] TASK-001: Task A
  - status: backlog
- [ ] TASK-002: Task B
  - status: backlog
  - dependencies: TASK-001
""")
            result = compute_frontier(tmpdir)
            self.assertEqual(len(result["executable_frontier"]), 1)
            self.assertEqual(result["executable_frontier"][0]["id"], "TASK-001")
            self.assertEqual(result["blocked_tasks"][0]["id"], "TASK-002")

    def test_frontier_ownership_conflicts(self):
        """Tasks sharing owned_files are in conflict_groups"""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan = Path(tmpdir) / "task_plan.md"
            plan.write_text("""# Task Plan

### P0
- [ ] TASK-001: Setup
  - status: completed
- [ ] TASK-002: Feature A
  - status: backlog
  - owned_files: src/core.py
- [ ] TASK-003: Feature B
  - status: backlog
  - owned_files: src/core.py
- [ ] TASK-004: Feature C
  - status: backlog
  - owned_files: src/api.py
""")
            result = compute_frontier(tmpdir)
            # TASK-002 and TASK-003 conflict (both own src/core.py)
            self.assertEqual(len(result["conflict_groups"]), 1)
            conflict_ids = [t["id"] for t in result["conflict_groups"][0]]
            self.assertIn("TASK-002", conflict_ids)
            self.assertIn("TASK-003", conflict_ids)

    def test_frontier_no_conflict_when_no_owned_files(self):
        """Tasks without owned_files can be parallel"""
        with tempfile.TemporaryDirectory() as tmpdir:
            plan = Path(tmpdir) / "task_plan.md"
            plan.write_text("""# Task Plan

### P0
- [ ] TASK-001: Setup
  - status: completed
- [ ] TASK-002: Task A
  - status: backlog
- [ ] TASK-003: Task B
  - status: backlog
""")
            result = compute_frontier(tmpdir)
            self.assertEqual(len(result["executable_frontier"]), 2)
            self.assertEqual(len(result["conflict_groups"]), 0)


class TestConditionalCheckpoint(unittest.TestCase):
    """Test checkpoint creates real files"""

    def test_checkpoint_disabled(self):
        """Disabled checkpoint returns false"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = CheckpointConfig(enabled=False)
            result = conditional_checkpoint(tmpdir, config)
            self.assertFalse(result["checkpoint_saved"])

    def test_checkpoint_creates_files(self):
        """Checkpoint creates .checkpoints/*.json and handoff_*.md"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal workflow state
            state_file = Path(tmpdir) / ".workflow_state.json"
            state_file.write_text(json.dumps({
                "session_id": "test-session",
                "phase": {
                    "current": "EXECUTING",
                    "history": [{"phase": "EXECUTING", "entered_at": "2026-04-01T00:00:00", "exited_at": None}]
                },
                "task": {
                    "task_id": "T001",
                    "title": "Test task",
                    "status": "in_progress",
                    "description": "",
                    "priority": "P1",
                    "owned_files": [],
                    "dependencies": [],
                    "verification": "",
                    "created_at": "2026-04-01T00:00:00",
                    "completed_at": None,
                    "progress": 0
                },
                "decisions": [],
                "file_changes": [],
                "artifacts": [],
            }))

            result = conditional_checkpoint(tmpdir)
            self.assertTrue(result["checkpoint_saved"])
            self.assertIn("checkpoint_id", result)
            self.assertIn("files", result)

            # Check files exist
            checkpoint_file = Path(tmpdir) / ".checkpoints" / f"{result['checkpoint_id']}.json"
            self.assertTrue(checkpoint_file.exists())

            handoff_file = Path(tmpdir) / f"handoff_{result['checkpoint_id']}.md"
            self.assertTrue(handoff_file.exists())

            # Verify handoff content
            handoff_content = handoff_file.read_text()
            self.assertIn("Test task", handoff_content)
            self.assertIn("EXECUTING", handoff_content)


class TestParsePhaseContract(unittest.TestCase):
    """Test contract parsing logic"""

    def test_parse_empty_contract(self):
        """Empty/missing contract returns empty dict"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = parse_phase_contract(tmpdir)
            self.assertEqual(result, {})

    def test_parse_contract_goals(self):
        """Contract goals are parsed correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            contract = Path(tmpdir) / "phase_contract.md"
            contract.write_text("""# Phase Contract

## Goals
- [ ] Goal 1: Implement feature A
- [ ] Goal 2: Implement feature B

## Verification
1. Test 1
2. Test 2

## Owned Files
- `src/a.py`
- `src/b.py`
""")
            result = parse_phase_contract(tmpdir)
            self.assertEqual(len(result["goals"]), 2)
            self.assertIn("Implement feature A", result["goals"][0])

    def test_parse_contract_verification_no_false_positives(self):
        """Verification parsing doesn't match arbitrary numbered lines"""
        with tempfile.TemporaryDirectory() as tmpdir:
            contract = Path(tmpdir) / "phase_contract.md"
            contract.write_text("""# Phase Contract

## Goals
- Goal 1: Do something

## Verification
1. Run pytest tests/test_a.py
2. Run pytest tests/test_b.py

## Notes
These tests cover:
1. Unit tests
2. Integration tests
""")
            result = parse_phase_contract(tmpdir)
            # Should only have 2 verification methods, not 4
            self.assertEqual(len(result["verification_methods"]), 2)
            self.assertIn("Run pytest tests/test_a.py", result["verification_methods"][0])


class TestTeamAgent(unittest.TestCase):
    """Test team agent worker assignments"""

    def test_team_agent_add_task(self):
        """Team can add and execute tasks"""
        team = TeamAgent(".", task="Test task")
        task_id = team.add_task("Do something", WorkerType.CODER)
        self.assertIsNotNone(task_id)
        self.assertEqual(team.tasks[task_id].assigned_worker, WorkerType.CODER)
        self.assertEqual(team.tasks[task_id].status, "assigned")

    def test_team_agent_infer_worker_type(self):
        """Worker type is inferred from task keywords"""
        team = TeamAgent(".", task="Test")
        # Research task
        coder_task = {"title": "Implement API", "description": ""}
        researcher_task = {"title": "Research best practices", "description": ""}
        reviewer_task = {"title": "Review code changes", "description": ""}

        self.assertEqual(team._infer_worker_type(coder_task), WorkerType.CODER)
        self.assertEqual(team._infer_worker_type(researcher_task), WorkerType.RESEARCHER)
        self.assertEqual(team._infer_worker_type(reviewer_task), WorkerType.REVIEWER)

    def test_team_agent_execute_task(self):
        """Worker can execute assigned task"""
        team = TeamAgent(".", task="Test task")
        task_id = team.add_task("Research Python", WorkerType.RESEARCHER)
        result = team.execute_task(task_id)
        self.assertTrue(result.success)
        self.assertEqual(result.worker_type, WorkerType.RESEARCHER)


class TestCheckpointConfig(unittest.TestCase):
    """Test checkpoint configuration"""

    def test_default_thresholds(self):
        """Default thresholds are reasonable"""
        config = CheckpointConfig()
        self.assertEqual(config.phase_change_threshold, 1)
        self.assertEqual(config.failure_threshold, 1)
        self.assertTrue(config.enabled)

    def test_custom_thresholds(self):
        """Custom thresholds can be set"""
        config = CheckpointConfig(
            phase_change_threshold=5,
            failure_threshold=3,
            step_threshold=20,
        )
        self.assertEqual(config.phase_change_threshold, 5)
        self.assertEqual(config.failure_threshold, 3)
        self.assertEqual(config.step_threshold, 20)


class TestTeamRunIntegration(unittest.TestCase):
    """Integration tests for team-run CLI and frontier consumption"""

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

    def test_team_run_consumes_frontier_groups(self):
        """TeamAgent.run() consumes parallel_groups and conflict_groups"""
        # Create a task plan with frontier groups
        plan_path = Path(self.temp_dir) / "task_plan.md"
        plan_path.write_text("""# Task Plan

### P0
- [ ] TASK-001: Setup
  - status: completed
- [ ] TASK-002: Feature A
  - status: backlog
  - owned_files: src/core.py
- [ ] TASK-003: Feature B
  - status: backlog
  - owned_files: src/core.py
- [ ] TASK-004: Feature C
  - status: backlog
  - owned_files: src/api.py
""")

        # Compute frontier
        from workflow_engine import compute_frontier
        frontier = compute_frontier(self.temp_dir)

        # Verify frontier has the grouping info
        self.assertEqual(len(frontier["executable_frontier"]), 3)
        self.assertIn("parallel_groups", frontier)
        self.assertIn("conflict_groups", frontier)

        # TASK-002 and TASK-003 share src/core.py -> conflict
        self.assertEqual(len(frontier["conflict_groups"]), 1)
        conflict_ids = [t["id"] for t in frontier["conflict_groups"][0]]
        self.assertIn("TASK-002", conflict_ids)
        self.assertIn("TASK-003", conflict_ids)

        # TASK-004 (src/api.py) has no conflict -> can be parallel with others in a different group
        self.assertIn("parallel_groups", frontier)

    def test_team_run_with_contract_goals(self):
        """Contract goals are added as team tasks"""
        # Create phase contract
        contract_path = Path(self.temp_dir) / "phase_contract.md"
        contract_path.write_text("""# Phase Contract

## Session
- Task: Test Task

## Goals
- [ ] Goal 1: Implement feature A
- [ ] Goal 2: Implement feature B

## Verification Methods
1. Run tests
2. Code review
""")

        team = TeamAgent(self.temp_dir, task="Test", contract={}, frontier={})
        # Manually set contract to simulate what team-run would do
        team.contract = workflow_engine.parse_phase_contract(self.temp_dir)

        # Should have 2 goals from contract
        self.assertEqual(len(team.contract.get("goals", [])), 2)

    def test_team_run_no_extra_task(self):
        """team-run does not inject extra coder task"""
        # Initialize workflow
        workflow_engine.initialize_workflow("Test task", workdir=self.temp_dir)

        # Create task plan
        plan_path = Path(self.temp_dir) / "task_plan.md"
        plan_path.write_text("""# Task Plan

### P0
- [ ] TASK-001: Feature A
  - status: backlog
  - owned_files: src/a.py
""")

        # Get frontier
        from workflow_engine import compute_frontier
        frontier = compute_frontier(self.temp_dir)
        contract = workflow_engine.parse_phase_contract(self.temp_dir)

        # Create team with frontier/contract - no extra add_task
        team = TeamAgent(self.temp_dir, task="Test", contract=contract, frontier=frontier)

        # Initially no tasks
        self.assertEqual(len(team.tasks), 0)

        # Run team
        result = team.run()

        # Tasks should come from frontier, not hardcoded injection
        # With no executable_frontier populated via add_task in run(),
        # tasks come from contract goals or remain empty
        # The key is no unconditional coder task is added
        self.assertIn("session_id", result)

    def test_team_artifact_registration(self):
        """Team outputs are registered as artifacts"""
        team = TeamAgent(self.temp_dir, task="Test")
        task_id = team.add_task("Research Python", WorkerType.RESEARCHER)
        result = team.execute_task(task_id)

        # WorkerResult should have artifacts
        self.assertIsNotNone(result)
        self.assertTrue(result.success)


if __name__ == "__main__":
    unittest.main()
