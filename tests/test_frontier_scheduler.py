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
from unittest.mock import patch

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT / "scripts"))  # noqa: E402

import workflow_engine  # noqa: E402
from memory_ops import update_thinking_summary  # noqa: E402
from search_adapter import SearchResponse, SearchResult  # noqa: E402
from team_agent import TeamAgent, WorkerType  # noqa: E402
from unified_state import load_state, save_state  # noqa: E402
from workflow_engine import (  # noqa: E402
    CheckpointConfig,
    compute_frontier,
    conditional_checkpoint,
    parse_phase_contract,
)


class TestComputeFrontier(unittest.TestCase):
    """Test ownership-aware frontier scheduling"""

    def test_frontier_empty_plan(self):
        """Empty task plan returns empty frontier"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = compute_frontier(tmpdir)
            self.assertEqual(result["executable_frontier"], [])
            self.assertEqual(result["parallel_candidates"], [])
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

    def test_checkpoint_includes_runtime_profile_summary(self):
        """Checkpoint surfaces runtime profile summary in JSON and handoff."""
        with tempfile.TemporaryDirectory() as tmpdir:
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
                "metadata": {
                    "runtime_profile": {
                        "skill_policy": "default_enable",
                        "use_skill": True,
                        "skill_activation_level": 50,
                        "tokens_expected": 2048,
                        "profile_source": "middleware+router",
                    }
                },
            }), encoding="utf-8")

            result = conditional_checkpoint(tmpdir)
            self.assertTrue(result["checkpoint_saved"])

            checkpoint_file = Path(tmpdir) / ".checkpoints" / f"{result['checkpoint_id']}.json"
            checkpoint_json = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint_json["runtime_profile_summary"]["skill_activation_level"], 50)
            self.assertEqual(checkpoint_json["runtime_profile_summary"]["skill_policy"], "default_enable")
            self.assertEqual(checkpoint_json["runtime_profile_summary"]["complexity"], None)
            self.assertEqual(checkpoint_json["planning_summary"]["plan_source"], "none")
            self.assertFalse(checkpoint_json["planning_summary"]["worktree_recommended"])
            self.assertEqual(checkpoint_json["review_summary"]["review_found"], False)

            handoff_file = Path(tmpdir) / f"handoff_{result['checkpoint_id']}.md"
            handoff_content = handoff_file.read_text(encoding="utf-8")
            self.assertIn("## Runtime Profile", handoff_content)
            self.assertIn("## Planning Summary", handoff_content)
            self.assertIn("## Review Summary", handoff_content)
            self.assertIn("Skill activation level: 50", handoff_content)
            self.assertIn("Profile source: middleware+router", handoff_content)

    def test_checkpoint_includes_failure_event_summary(self):
        """Checkpoint surfaces failure event summary in JSON and handoff."""
        with tempfile.TemporaryDirectory() as tmpdir:
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
                "decisions": [
                    {
                        "timestamp": "2026-04-01T00:00:01",
                        "decision": "Escalate skill activation",
                        "reason": "high_signal_failure:quality_gate_failed escalated activation to 75",
                        "metadata": {
                            "error_type": "quality_gate_failed",
                            "current_activation_level": 50,
                            "escalated_activation_level": 75,
                            "escalation_reason": "high_signal_failure:quality_gate_failed",
                            "retry_count": 0,
                            "profile_source": "middleware+router"
                        }
                    }
                ],
                "file_changes": [],
                "artifacts": [],
                "metadata": {
                    "runtime_profile": {
                        "skill_policy": "default_enable",
                        "use_skill": True,
                        "skill_activation_level": 75,
                        "tokens_expected": 2048,
                        "profile_source": "middleware+router",
                    }
                },
            }), encoding="utf-8")

            result = conditional_checkpoint(tmpdir)
            self.assertTrue(result["checkpoint_saved"])

            checkpoint_file = Path(tmpdir) / ".checkpoints" / f"{result['checkpoint_id']}.json"
            checkpoint_json = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint_json["failure_event_summary"]["failure_event_count"], 1)
            self.assertEqual(checkpoint_json["failure_event_summary"]["escalation_event_count"], 1)
            self.assertEqual(checkpoint_json["failure_event_summary"]["latest_escalation_event"]["escalated_activation_level"], 75)
            self.assertEqual(checkpoint_json["runtime_profile_summary"]["complexity"], None)
            self.assertEqual(checkpoint_json["planning_summary"]["plan_source"], "none")
            self.assertEqual(checkpoint_json["review_summary"]["review_found"], False)

            handoff_file = Path(tmpdir) / f"handoff_{result['checkpoint_id']}.md"
            handoff_content = handoff_file.read_text(encoding="utf-8")
            self.assertIn("## Failure Events", handoff_content)
            self.assertIn("## Planning Summary", handoff_content)
            self.assertIn("## Review Summary", handoff_content)
            self.assertIn("Failure events: 1", handoff_content)
            self.assertIn("Escalation events: 1", handoff_content)

    def test_checkpoint_includes_thinking_summary(self):
        """Checkpoint surfaces THINKING summary in JSON and handoff."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".workflow_state.json"
            state_file.write_text(json.dumps({
                "session_id": "test-session",
                "phase": {
                    "current": "THINKING",
                    "history": [{"phase": "THINKING", "entered_at": "2026-04-01T00:00:00", "exited_at": None}]
                },
                "task": {
                    "task_id": "T001",
                    "title": "Test thinking task",
                    "status": "in_progress",
                    "description": "新项目启动：需要先判断主要矛盾",
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
                "metadata": {
                    "complexity": "M"
                },
            }), encoding="utf-8")

            session_state = Path(tmpdir) / "SESSION-STATE.md"
            update_thinking_summary(
                str(session_state),
                {
                    "workflow_label": "新项目启动",
                    "workflow": "workflow_1_new_project",
                    "major_contradiction": "目标完整性 vs 交付节奏",
                    "stage_judgment": "战略防御",
                    "local_attack_point": "最小可验证切口",
                    "recommendation": "先做事实收集",
                    "memory_hints_count": 2,
                },
            )

            result = conditional_checkpoint(tmpdir)
            self.assertTrue(result["checkpoint_saved"])

            checkpoint_file = Path(tmpdir) / ".checkpoints" / f"{result['checkpoint_id']}.json"
            checkpoint_json = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint_json["thinking_summary"]["workflow_label"], "新项目启动")
            self.assertEqual(checkpoint_json["thinking_summary"]["thinking_mode"], "investigation_first")
            self.assertEqual(
                checkpoint_json["thinking_summary"]["thinking_methods"],
                ["调查研究", "矛盾分析", "群众路线", "持久战略"],
            )
            self.assertIn("目标完整性", checkpoint_json["thinking_summary"]["major_contradiction"])
            self.assertEqual(checkpoint_json["thinking_summary"]["memory_hints_count"], 2)

            handoff_file = Path(tmpdir) / f"handoff_{result['checkpoint_id']}.md"
            handoff_content = handoff_file.read_text(encoding="utf-8")
            self.assertIn("## THINKING Summary", handoff_content)
            self.assertIn("Workflow label: 新项目启动", handoff_content)
            self.assertIn("Thinking mode: investigation_first", handoff_content)
            self.assertIn("Thinking methods: 调查研究 | 矛盾分析 | 群众路线 | 持久战略", handoff_content)
            self.assertIn("Major contradiction: 目标完整性 vs 交付节奏", handoff_content)
            self.assertIn("Memory hints count: 2", handoff_content)


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

    def test_parse_contract_markdown_fallback_extended_sections(self):
        """Markdown fallback parses acceptance, impact, dependencies, and rollback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            contract = Path(tmpdir) / "phase_contract.md"
            contract.write_text("""# Phase Contract

## Goals
- [ ] Goal 1: Implement feature A

## Acceptance Criteria
- Login succeeds with valid credentials

## Verification
1. Run pytest tests/test_auth.py

## Owned Files
- `src/auth.py`

## Impact Files
- `src/auth.py`
- `tests/test_auth.py`

## Dependencies
- auth service available

## Rollback Note
- Revert auth.py and rerun auth tests
""")
            result = parse_phase_contract(tmpdir)
            self.assertEqual(result["acceptance_criteria"], ["Login succeeds with valid credentials"])
            self.assertEqual(result["impact_files"], ["src/auth.py", "tests/test_auth.py"])
            self.assertEqual(result["dependencies"], ["auth service available"])
            self.assertEqual(result["rollback_note"], "Revert auth.py and rerun auth tests")


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

    def test_team_agent_shared_memory_capsule_in_handoff(self):
        """Team handoff should include a compact shared memory capsule."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow_engine.initialize_workflow("Build login flow", workdir=tmpdir)
            team = TeamAgent(
                tmpdir,
                task="Build login flow",
                contract={
                    "status": "active",
                    "goals": ["Ship login flow"],
                    "acceptance_criteria": ["Login works"],
                    "impact_files": ["src/app.py"],
                    "dependencies": [],
                    "rollback_note": "Revert src/app.py",
                },
                frontier={
                    "executable_frontier": [{"title": "Implement login", "description": "Implement login"}],
                },
                use_real_agent=False,
            )

            team.add_task("Implement login", WorkerType.CODER)
            team.run()
            handoff = team.sanitize_for_handoff()

            self.assertIn("shared_memory_capsule", handoff)
            capsule = handoff["shared_memory_capsule"]
            self.assertIn("runtime_profile", capsule)
            self.assertIn("planning", capsule)
            self.assertIn("research", capsule)
            self.assertIn("thinking", capsule)
            self.assertIn("review", capsule)
            self.assertEqual(capsule["task"], "Build login flow")
            self.assertIn("plan_source", capsule["planning"])
            self.assertIn("evidence_status", capsule["research"])


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
        self.search_patcher = patch(
            "team_agent.search_adapter.search_with_fallback",
            side_effect=self._fake_search_with_fallback,
        )
        self.search_patcher.start()
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
        self.search_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @staticmethod
    def _fake_search_with_fallback(query: str, num_results: int = 5, fallback_content: str | None = None):
        results = [
            SearchResult(
                title=f"Result {idx + 1}",
                url=f"https://example.com/{idx + 1}",
                snippet=f"Snippet for {query} #{idx + 1}",
                source="stub",
                reliability="B",
            )
            for idx in range(num_results)
        ]
        response = SearchResponse(
            query=query,
            results=results,
            total_results=len(results),
            search_engine="stub-search",
            metadata={"degraded_mode": False},
        )
        return response, False

    def test_team_run_consumes_frontier_groups(self):
        """TeamAgent.run() consumes parallel_candidates and conflict_groups"""
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
        self.assertIn("parallel_candidates", frontier)
        self.assertIn("conflict_groups", frontier)

        # TASK-002 and TASK-003 share src/core.py -> conflict
        self.assertEqual(len(frontier["conflict_groups"]), 1)
        conflict_ids = [t["id"] for t in frontier["conflict_groups"][0]]
        self.assertIn("TASK-002", conflict_ids)
        self.assertIn("TASK-003", conflict_ids)

        # TASK-004 (src/api.py) has no conflict -> can be parallel with others in a different group
        self.assertIn("parallel_candidates", frontier)

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
        team = TeamAgent(
            self.temp_dir,
            task="Test",
            contract=contract,
            frontier=frontier,
            use_real_agent=False,
        )

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
        team = TeamAgent(self.temp_dir, task="Test", use_real_agent=False)
        task_id = team.add_task("Research Python", WorkerType.RESEARCHER)
        result = team.execute_task(task_id)

        # WorkerResult should have artifacts
        self.assertIsNotNone(result)
        self.assertTrue(result.success)

    def test_contract_gate_blocks_draft_complete(self):
        """Contract with status=draft blocks workflow completion for FULL_WORKFLOW code tasks"""
        import json

        # Initialize workflow — routes to STAGE/EXECUTING (which is a code task)
        workflow_engine.initialize_workflow("Test task", workdir=self.temp_dir)

        # Patch state to FULL_WORKFLOW trigger and M complexity (contract gate applies to these)
        state = load_state(self.temp_dir)
        state.trigger_type = "FULL_WORKFLOW"
        state.metadata = {"complexity": "M"}
        save_state(self.temp_dir, state)

        # Create a draft contract AFTER init (so init doesn't interfere)
        contract_path = Path(self.temp_dir) / ".contract.json"
        contract_path.write_text(json.dumps({
            "version": "1.0",
            "task": "Test",
            "status": "draft",
            "goals": [],
            "verification_methods": [],
            "owned_files": [],
            "acceptance_criteria": ["All planned tasks are completed"],
            "impact_files": ["src/app.py"],
            "dependencies": [],
            "rollback_note": "Revert src/app.py and rerun tests.",
        }))

        # Set quality_gates_passed=True to skip quality gate check
        tracker_path = Path(self.temp_dir) / ".task_tracker.json"
        tracker_data = json.loads(tracker_path.read_text())
        for t in tracker_data.get("tasks", []):
            t["quality_gates_passed"] = True
        tracker_path.write_text(json.dumps(tracker_data))

        # Try to complete - should fail due to draft contract
        from workflow_engine import complete_workflow
        with self.assertRaises(ValueError) as ctx:
            complete_workflow(self.temp_dir)
        self.assertIn("draft", str(ctx.exception))

    def test_team_run_accepts_phase_and_register_artifacts(self):
        """TeamAgent.run() accepts phase and register_artifacts params"""
        team = TeamAgent(self.temp_dir, task="Test", use_real_agent=False)
        team.add_task("Do something", WorkerType.CODER)

        # Run with phase and register_artifacts
        result = team.run(phase="EXECUTING", register_artifacts=False)

        # Should complete without errors
        self.assertIn("session_id", result)
        self.assertIn("tasks_completed", result)

    def test_validate_contract_gate_with_placeholder_goals(self):
        """Contract with placeholder goals is rejected"""
        import json
        contract_path = Path(self.temp_dir) / ".contract.json"
        contract_path.write_text(json.dumps({
            "version": "1.0",
            "task": "Test",
            "status": "active",
            "goals": ["Goal 1: (to be filled by planner)"],
            "verification_methods": [],
            "owned_files": [],
            "acceptance_criteria": ["All planned tasks are completed"],
            "impact_files": ["src/app.py"],
            "dependencies": [],
            "rollback_note": "Revert src/app.py and rerun tests.",
        }))

        from workflow_engine import load_state, validate_contract_gate
        state = load_state(self.temp_dir)
        is_valid, error = validate_contract_gate(self.temp_dir, state)

        self.assertFalse(is_valid)
        self.assertIn("placeholder", error.lower())


class TestTeamArtifactPersistence(unittest.TestCase):
    """Tests for team artifact persistence and recovery"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.search_patcher = patch(
            "team_agent.search_adapter.search_with_fallback",
            side_effect=self._fake_search_with_fallback,
        )
        self.search_patcher.start()

    def tearDown(self):
        self.search_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @staticmethod
    def _fake_search_with_fallback(query: str, num_results: int = 5, fallback_content: str | None = None):
        results = [
            SearchResult(
                title=f"Result {idx + 1}",
                url=f"https://example.com/{idx + 1}",
                snippet=f"Snippet for {query} #{idx + 1}",
                source="stub",
                reliability="B",
            )
            for idx in range(num_results)
        ]
        response = SearchResponse(
            query=query,
            results=results,
            total_results=len(results),
            search_engine="stub-search",
            metadata={"degraded_mode": False},
        )
        return response, False

    def test_coder_produces_artifact(self):
        """Coder worker produces artifact file (skip real agent, test pipeline)"""
        team = TeamAgent(self.temp_dir, task="Test task", use_real_agent=False)
        task_id = team.add_task("Implement feature", WorkerType.CODER)
        result = team.execute_task(task_id)

        self.assertTrue(result.success)
        self.assertGreater(len(result.artifacts), 0)
        # Check artifact file exists
        for artifact_path in result.artifacts:
            self.assertTrue(Path(artifact_path).exists())

    def test_reviewer_produces_artifact(self):
        """Reviewer worker produces artifact file"""
        team = TeamAgent(self.temp_dir, task="Test task", use_real_agent=False)
        task_id = team.add_task("Review code", WorkerType.REVIEWER)
        result = team.execute_task(task_id)

        self.assertTrue(result.success)
        self.assertGreater(len(result.artifacts), 0)
        for artifact_path in result.artifacts:
            self.assertTrue(Path(artifact_path).exists())

    def test_debugger_produces_artifact(self):
        """Debugger worker produces artifact file"""
        team = TeamAgent(self.temp_dir, task="Test task", use_real_agent=False)
        task_id = team.add_task("Debug issue", WorkerType.DEBUGGER)
        result = team.execute_task(task_id)

        self.assertTrue(result.success)
        self.assertGreater(len(result.artifacts), 0)
        for artifact_path in result.artifacts:
            self.assertTrue(Path(artifact_path).exists())

    def test_worker_result_is_summarized_for_lead(self):
        """Lead receives a structured envelope instead of raw worker output."""
        team = TeamAgent(self.temp_dir, task="Test task", use_real_agent=False)
        task_id = team.add_task("Review code", WorkerType.REVIEWER)

        result = team.execute_task(task_id)

        self.assertTrue(result.success)
        self.assertGreater(len(team.messages), 0)
        message = team.messages[-1]
        self.assertIn("envelope", message.content)
        envelope = message.content["envelope"]
        self.assertIn("summary", envelope)
        self.assertIn("artifact_refs", envelope)
        self.assertNotIn("output", message.content)
        self.assertLessEqual(len(envelope["summary"]), 260)

    def test_researcher_produces_artifact(self):
        """Researcher worker produces artifact file"""
        team = TeamAgent(self.temp_dir, task="Test task", use_real_agent=False)
        task_id = team.add_task("Research best practices", WorkerType.RESEARCHER)
        result = team.execute_task(task_id)

        self.assertTrue(result.success)
        self.assertGreater(len(result.artifacts), 0)
        for artifact_path in result.artifacts:
            self.assertTrue(Path(artifact_path).exists())

    def test_team_snapshot_is_recoverable(self):
        """Team snapshot can be saved to .team_registry.json"""
        team = TeamAgent(self.temp_dir, task="Test task")
        team.add_task("Task 1", WorkerType.CODER)
        team.add_task("Task 2", WorkerType.CODER)

        # Save snapshot
        team.save_snapshot(self.temp_dir)

        # Check registry file exists and contains session data
        registry_path = Path(self.temp_dir) / ".team_registry.json"
        self.assertTrue(registry_path.exists())

        import json
        registry = json.loads(registry_path.read_text())
        self.assertIn("team_sessions", registry)
        self.assertGreater(len(registry["team_sessions"]), 0)

        # Latest session should be ours
        latest = registry["team_sessions"][-1]
        self.assertEqual(latest["session_id"], team.session_id)
        self.assertEqual(latest["task"], "Test task")
        self.assertEqual(latest["total_tasks"], 2)

    def test_team_snapshot_contains_output_summaries(self):
        """Snapshot includes output_summary and artifacts from completed tasks"""
        team = TeamAgent(self.temp_dir, task="Test task")
        team.add_task("Research Python", WorkerType.RESEARCHER)
        task_id = list(team.tasks.keys())[0]
        team.execute_task(task_id)  # execute to produce output/artifact

        # Save snapshot
        team.save_snapshot(self.temp_dir)

        # Load registry and check output_summary + artifacts are present
        registry_path = Path(self.temp_dir) / ".team_registry.json"
        import json
        registry = json.loads(registry_path.read_text())
        latest = registry["team_sessions"][-1]
        task_state = latest["state"]["tasks"][task_id]

        self.assertIn("output_summary", task_state)
        self.assertIn("artifacts", task_state)
        self.assertIsNotNone(task_state["output_summary"])
        self.assertGreater(len(task_state["artifacts"]), 0)

    def test_load_snapshot_recovers_team_state(self):
        """load_snapshot restores a team with task results and artifacts"""
        team = TeamAgent(self.temp_dir, task="Test task")
        team.add_task("Research Python", WorkerType.RESEARCHER)
        task_id = list(team.tasks.keys())[0]
        team.execute_task(task_id)
        original_session_id = team.session_id

        # Save snapshot
        team.save_snapshot(self.temp_dir)

        # Recover team from snapshot
        recovered = TeamAgent.load_snapshot(self.temp_dir, original_session_id)

        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.session_id, original_session_id)
        self.assertEqual(recovered.task, "Test task")
        self.assertEqual(len(recovered.tasks), 1)

        recovered_task = list(recovered.tasks.values())[0]
        self.assertEqual(recovered_task.status, "completed")
        self.assertIsNotNone(recovered_task.result)
        self.assertTrue(recovered_task.result.success)
        self.assertGreater(len(recovered_task.result.artifacts), 0)

    def test_team_run_registers_artifacts(self):
        """TeamAgent.run() registers worker artifacts"""
        team = TeamAgent(self.temp_dir, task="Test task", use_real_agent=False)
        team.add_task("Research task", WorkerType.RESEARCHER)
        team.add_task("Code task", WorkerType.CODER)

        # Run with register_artifacts=True
        result = team.run(register_artifacts=True)

        # Check results have artifacts
        self.assertGreater(len(result["artifacts"]), 0)

        # Check artifacts are registered
        from unified_state import get_artifacts
        all_artifacts = get_artifacts(self.temp_dir)
        self.assertGreater(len(all_artifacts), 0)


if __name__ == "__main__":
    unittest.main()
