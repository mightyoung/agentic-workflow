#!/usr/bin/env python3
"""
Tests for analyze_gate module.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_gate import (  # noqa: E402
    AnalyzeGate,
    check_template_drift,
    generate_spec_checklist,
    validate_analyze_gate,
    validate_constitution,
)


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

    def test_validate_p0_task_with_placeholder_verification_fails(self):
        """Test validation fails when P0 task has placeholder verification."""
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
            + "  **Files:** test.py\n"
            + "  **Verification:** [verification command]\n",
            encoding="utf-8"
        )

        gate = AnalyzeGate(self.temp_dir)
        result = gate.validate()
        self.assertFalse(result.passed)
        self.assertTrue(any("placeholder verification" in e.lower() for e in result.errors))

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


class TestGenerateSpecChecklist(unittest.TestCase):
    """Tests for generate_spec_checklist function."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.specs_dir = Path(self.temp_dir) / ".specs"
        self.specs_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_spec_checklist_returns_dict(self):
        """Test generate_spec_checklist returns expected structure."""
        result = generate_spec_checklist(self.temp_dir)
        self.assertIsInstance(result, dict)
        self.assertIn("spec_checklist", result)
        self.assertIn("plan_checklist", result)
        self.assertIn("overall_score", result)
        self.assertIn("recommendations", result)

    def test_generate_spec_checklist_no_spec(self):
        """Test checklist when no spec exists."""
        result = generate_spec_checklist(self.temp_dir)
        self.assertEqual(result["overall_score"], 0.0)

    def test_generate_spec_checklist_with_spec(self):
        """Test checklist with proper spec."""
        feature_dir = self.specs_dir / "test_feature"
        feature_dir.mkdir()
        spec_file = feature_dir / "spec.md"
        spec_file.write_text(
            "# Spec: Test Feature\n\n"
            + "x" * 200 + "\n\n"
            + "## User Stories\n\n"
            + "### Story 1: Test User\n"
            + "**As a** user\n"
            + "**I want** feature\n"
            + "**So that** value\n\n"
            + "**Acceptance Criteria:**\n"
            + "- Criterion 1: Works correctly\n\n"
            + "## Success Criteria\n\n"
            + "- Criteria 1: Feature works\n\n"
            + "## Constraints\n\n"
            + "- Constraint 1: Must be fast\n",
            encoding="utf-8"
        )
        result = generate_spec_checklist(self.temp_dir)
        self.assertIsInstance(result["spec_checklist"], list)
        self.assertGreater(len(result["spec_checklist"]), 0)


class TestValidateConstitution(unittest.TestCase):
    """Tests for validate_constitution function."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.specs_dir = Path(self.temp_dir) / ".specs"
        self.specs_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_constitution_returns_dict(self):
        """Test validate_constitution returns expected structure."""
        result = validate_constitution(self.temp_dir)
        self.assertIsInstance(result, dict)
        self.assertIn("is_valid", result)
        self.assertIn("violations", result)
        self.assertIn("score", result)
        self.assertIn("suggestions", result)

    def test_validate_constitution_no_plan(self):
        """Test constitution fails when no plan.md exists."""
        result = validate_constitution(self.temp_dir)
        self.assertFalse(result["is_valid"])
        self.assertIn("No plan.md found", result["violations"][0])

    def test_validate_constitution_with_plan(self):
        """Test constitution passes with proper plan."""
        feature_dir = self.specs_dir / "test_feature"
        feature_dir.mkdir()
        plan_file = feature_dir / "plan.md"
        plan_file.write_text(
            "# Plan: Test Feature\n\n"
            + "## Goals\n\n"
            + "- Goal 1\n\n"
            + "## Technical Context\n\n"
            + "- Context 1\n\n"
            + "## Structure Decisions\n\n"
            + "- Decision 1\n\n"
            + "## Constraints\n\n"
            + "- Constraint 1\n\n"
            + "## Tech Stack\n\n"
            + "- Python\n\n"
            + "## Output Artifacts\n\n"
            + "- artifact1.py\n",
            encoding="utf-8"
        )
        result = validate_constitution(self.temp_dir)
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["score"], 1.0)


class TestCheckTemplateDrift(unittest.TestCase):
    """Tests for check_template_drift function."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_check_template_drift_returns_dict(self):
        """Test check_template_drift returns expected structure."""
        result = check_template_drift(
            str(Path(self.temp_dir) / "repo_skill.md"),
            str(Path(self.temp_dir) / "installed_skill.md")
        )
        self.assertIsInstance(result, dict)
        self.assertIn("has_drift", result)
        self.assertIn("drift_details", result)
        self.assertIn("repo_hash", result)
        self.assertIn("installed_hash", result)

    def test_check_template_drift_no_drift(self):
        """Test no drift when files are identical."""
        skill_file = Path(self.temp_dir) / "skill.md"
        skill_file.write_text("# Skill\n\ncontent", encoding="utf-8")
        result = check_template_drift(str(skill_file), str(skill_file))
        self.assertFalse(result["has_drift"])

    def test_check_template_drift_with_drift(self):
        """Test drift detection when files differ."""
        repo_file = Path(self.temp_dir) / "repo.md"
        repo_file.write_text("# Repo Skill\n\nversion: 1.0.0", encoding="utf-8")
        installed_file = Path(self.temp_dir) / "installed.md"
        installed_file.write_text("# Installed Skill\n\nversion: 2.0.0", encoding="utf-8")
        result = check_template_drift(str(repo_file), str(installed_file))
        self.assertTrue(result["has_drift"])
        self.assertGreater(len(result["drift_details"]), 0)

    def test_check_template_drift_missing_file(self):
        """Test handling of missing files."""
        result = check_template_drift(
            str(Path(self.temp_dir) / "nonexistent.md"),
            str(Path(self.temp_dir) / "also_nonexistent.md")
        )
        self.assertFalse(result["has_drift"])  # No content to compare
        self.assertEqual(result["repo_hash"], "not-found")
        self.assertEqual(result["installed_hash"], "not-found")


if __name__ == "__main__":
    unittest.main()
