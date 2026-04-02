#!/usr/bin/env python3
"""
Tests for analyze_gate module.
"""

import json
import os
import sys
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_gate import AnalyzeGate, validate_analyze_gate


class TestAnalyzeGate(unittest.TestCase):
    """Tests for AnalyzeGate class."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.specs_dir = Path(self.temp_dir) / ".specs"
        self.specs_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_empty_dir_fails(self):
        """Test validation fails when no spec exists."""
        gate = AnalyzeGate(self.temp_dir)
        result = gate.validate()
        self.assertFalse(result.passed)
        self.assertTrue(len(result.errors) >= 2)

    def test_validate_spec_too_short(self):
        """Test validation fails when spec.md is too short."""
        feature_dir = self.specs_dir / "test_feature"
        feature_dir.mkdir()
        spec_file = feature_dir / "spec.md"
        spec_file.write_text("[Title]\n\n[Task title]", encoding="utf-8")

        gate = AnalyzeGate(self.temp_dir)
        result = gate.validate()
        self.assertFalse(result.passed)

    def test_validate_spec_with_placeholder_warns(self):
        """Test validation warns when spec has placeholder content."""
        feature_dir = self.specs_dir / "test_feature"
        feature_dir.mkdir()
        spec_file = feature_dir / "spec.md"
        # Must be > 200 chars to pass the length check
        spec_file.write_text(
            "# Spec: [Title]\n\n"
            + "x" * 200
            + "\n\n## User Stories\n\n### Story 1: Test\n**As a** user\n**I want** goal\n",
            encoding="utf-8"
        )

        gate = AnalyzeGate(self.temp_dir)
        result = gate.validate()
        self.assertTrue(any("placeholder" in w.lower() for w in result.warnings))

    def test_validate_tasks_missing_provenance(self):
        """Test validation fails when tasks.md missing provenance headers."""
        feature_dir = self.specs_dir / "test_feature"
        feature_dir.mkdir()
        spec_file = feature_dir / "spec.md"
        spec_file.write_text(
            "# Spec: Test\n\n" + "x" * 300 + "\n\n## User Stories\n\n### Story 1: Title\n",
            encoding="utf-8"
        )
        tasks_file = feature_dir / "tasks.md"
        tasks_file.write_text("# Tasks\n\n- [ ] TASK-1: test\n", encoding="utf-8")

        gate = AnalyzeGate(self.temp_dir)
        result = gate.validate()
        self.assertFalse(result.passed)
        self.assertTrue(any("provenance" in e.lower() for e in result.errors))

    def test_validate_story_task_mapping(self):
        """Test validation detects when user story has no tasks."""
        feature_dir = self.specs_dir / "test_feature"
        feature_dir.mkdir()
        spec_file = feature_dir / "spec.md"
        spec_file.write_text(
            "# Spec: Test\n\n" + "x" * 300 + "\n\n## User Stories\n\n### Story 1: Title\n### Story 2: Another\n",
            encoding="utf-8"
        )
        tasks_file = feature_dir / "tasks.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            + "Generated-By: test\nSession: test\nSource-Spec: test\nTimestamp: test\n\n"
            + "- [ ] **TASK-US1-1:** Test\n  **Files:** test.py\n",
            encoding="utf-8"
        )

        gate = AnalyzeGate(self.temp_dir)
        result = gate.validate()
        self.assertFalse(result.passed)
        self.assertTrue(any("Story 2" in e for e in result.errors))

    def test_validate_p0_task_without_verification_fails(self):
        """Test validation fails when P0 task has no verification."""
        feature_dir = self.specs_dir / "test_feature"
        feature_dir.mkdir()
        spec_file = feature_dir / "spec.md"
        spec_file.write_text(
            "# Spec: Test\n\n" + "x" * 300 + "\n\n## User Stories\n\n### Story 1: Title\n",
            encoding="utf-8"
        )
        tasks_file = feature_dir / "tasks.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            + "Generated-By: test\nSession: test\nSource-Spec: test\nTimestamp: test\n\n"
            + "- [ ] **TASK-US1-1:** P0 Critical Task\n"
            + "  **Files:** test.py\n",
            encoding="utf-8"
        )

        gate = AnalyzeGate(self.temp_dir)
        result = gate.validate()
        self.assertFalse(result.passed)
        self.assertTrue(any("verification" in e.lower() for e in result.errors))

    def test_validate_contract_draft_fails(self):
        """Test validation fails when contract.json status is draft."""
        feature_dir = self.specs_dir / "test_feature"
        feature_dir.mkdir()
        spec_file = feature_dir / "spec.md"
        spec_file.write_text(
            "# Spec: Test\n\n" + "x" * 300 + "\n\n## User Stories\n\n### Story 1: Title\n",
            encoding="utf-8"
        )
        tasks_file = feature_dir / "tasks.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            + "Generated-By: test\nSession: test\nSource-Spec: test\nTimestamp: test\n\n"
            + "- [ ] **TASK-FOUND-1:** P0 Task\n"
            + "  **Files:** test.py\n"
            + "  **Verification:** pytest test.py\n",
            encoding="utf-8"
        )
        contract_file = Path(self.temp_dir) / ".contract.json"
        contract_file.write_text(
            json.dumps({"status": "draft", "goals": ["to be filled"]}),
            encoding="utf-8"
        )

        gate = AnalyzeGate(self.temp_dir)
        result = gate.validate()
        self.assertFalse(result.passed)
        self.assertTrue(any("draft" in e.lower() for e in result.errors))

    def test_validate_success_with_proper_artifacts(self):
        """Test validation passes with proper spec, tasks, and contract."""
        feature_dir = self.specs_dir / "test_feature"
        feature_dir.mkdir()
        spec_file = feature_dir / "spec.md"
        spec_file.write_text(
            "# Spec: Test\n\n" + "x" * 300 + "\n\n## User Stories\n\n### Story 1: Title\n",
            encoding="utf-8"
        )
        tasks_file = feature_dir / "tasks.md"
        tasks_file.write_text(
            "# Tasks\n\n"
            + "Generated-By: agentic-workflow\n"
            + "Session: test-session\n"
            + "Source-Spec: .specs/test_feature/spec.md\n"
            + "Timestamp: 2024-01-01T00:00:00\n\n"
            + "- [ ] **TASK-FOUND-1:** Setup Task\n"
            + "  **Files:** test.py\n"
            + "  **Verification:** pytest test.py -v\n"
            + "- [ ] **TASK-US1-1:** User Story 1 Task\n"
            + "  **Files:** feature.py\n"
            + "  **Verification:** pytest feature.py -v\n",
            encoding="utf-8"
        )
        contract_file = Path(self.temp_dir) / ".contract.json"
        contract_file.write_text(
            json.dumps({
                "status": "active",
                "goals": ["Implement test feature"],
                "verification_methods": ["pytest tests/"],
                "owned_files": ["test.py"]
            }),
            encoding="utf-8"
        )

        gate = AnalyzeGate(self.temp_dir)
        result = gate.validate()
        self.assertTrue(result.passed, f"Errors: {result.errors}, Warnings: {result.warnings}")


class TestValidateAnalyzeGateFunction(unittest.TestCase):
    """Tests for validate_analyze_gate convenience function."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_analyze_gate_returns_result(self):
        """Test convenience function returns AnalyzeResult."""
        result = validate_analyze_gate(self.temp_dir)
        self.assertFalse(result.passed)
        self.assertTrue(hasattr(result, 'errors'))
        self.assertTrue(hasattr(result, 'warnings'))
        self.assertTrue(hasattr(result, 'passed'))


if __name__ == "__main__":
    unittest.main()