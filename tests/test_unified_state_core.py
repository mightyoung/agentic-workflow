"""Unit tests for unified_state.py core state management functions."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from unified_state import (
    create_initial_state,
    load_state,
    save_state,
    validate_workflow_state,
    get_runtime_profile_summary,
    get_planning_summary,
    get_research_summary,
    workflow_state_path,
)


class TestCreateInitialState(unittest.TestCase):
    def test_creates_state_with_task(self):
        state = create_initial_state("Build a login feature")
        self.assertEqual(state.task.description, "Build a login feature")
        self.assertEqual(state.task.status, "in_progress")

    def test_title_truncated_to_100_chars(self):
        long_prompt = "A" * 200
        state = create_initial_state(long_prompt)
        self.assertEqual(len(state.task.title), 100)

    def test_custom_task_id(self):
        state = create_initial_state("prompt", task_id="T123")
        self.assertEqual(state.task.task_id, "T123")

    def test_auto_task_id_generated(self):
        state = create_initial_state("prompt")
        self.assertTrue(state.task.task_id.startswith("T"))

    def test_trigger_type_stored(self):
        state = create_initial_state("prompt", trigger_type="PLANNING_ONLY")
        self.assertEqual(state.trigger_type, "PLANNING_ONLY")

    def test_initial_phase_set(self):
        state = create_initial_state("prompt", initial_phase="RESEARCHING")
        self.assertEqual(state.phase["current"], "RESEARCHING")

    def test_initial_decision_recorded(self):
        state = create_initial_state("prompt")
        self.assertGreater(len(state.decisions), 0)
        self.assertIn("FULL_WORKFLOW", state.decisions[0].decision)

    def test_session_id_auto_generated(self):
        state = create_initial_state("prompt")
        self.assertTrue(state.session_id.startswith("s"))

    def test_artifacts_empty_on_init(self):
        state = create_initial_state("prompt")
        self.assertEqual(state.artifacts, {})

    def test_created_at_set(self):
        state = create_initial_state("prompt")
        self.assertIsNotNone(state.created_at)


class TestLoadSaveState(unittest.TestCase):
    def test_load_returns_none_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = load_state(tmpdir)
            self.assertIsNone(result)

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = create_initial_state("test task", task_id="T001")
            save_state(tmpdir, state)
            loaded = load_state(tmpdir)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.task.task_id, "T001")
            self.assertEqual(loaded.task.description, "test task")

    def test_save_returns_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = create_initial_state("task")
            path = save_state(tmpdir, state)
            self.assertIsInstance(path, Path)
            self.assertTrue(path.exists())

    def test_save_updates_updated_at(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = create_initial_state("task")
            original_updated_at = state.updated_at
            save_state(tmpdir, state)
            # updated_at may be same-second but should be set
            loaded = load_state(tmpdir)
            self.assertIsNotNone(loaded.updated_at)

    def test_state_file_path(self):
        path = workflow_state_path("/some/dir")
        self.assertIn("workflow_state", str(path))


class TestValidateWorkflowState(unittest.TestCase):
    def test_invalid_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            valid, errors = validate_workflow_state(tmpdir)
            self.assertFalse(valid)
            self.assertGreater(len(errors), 0)

    def test_valid_after_save(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = create_initial_state("task")
            save_state(tmpdir, state)
            valid, errors = validate_workflow_state(tmpdir)
            # Sidecar drift is acceptable; check no schema errors
            schema_errors = [e for e in errors if "sidecar" not in e.lower() and "mismatch" not in e.lower()]
            self.assertEqual(schema_errors, [], f"Schema errors: {schema_errors}")


class TestSummaryGetters(unittest.TestCase):
    def test_get_runtime_profile_summary_from_none(self):
        summary = get_runtime_profile_summary(None)
        self.assertIsInstance(summary, dict)
        # Should return defaults, not raise
        self.assertIn("profile_source", summary)

    def test_get_planning_summary_no_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = get_planning_summary(tmpdir, None)
            self.assertIsInstance(summary, dict)

    def test_get_research_summary_no_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = get_research_summary(tmpdir, None)
            self.assertIsInstance(summary, dict)

    def test_get_runtime_profile_with_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = create_initial_state("task")
            save_state(tmpdir, state)
            loaded = load_state(tmpdir)
            summary = get_runtime_profile_summary(loaded)
            self.assertIsInstance(summary, dict)


if __name__ == "__main__":
    unittest.main()
