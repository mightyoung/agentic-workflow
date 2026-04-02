#!/usr/bin/env python3
"""
Analyze Gate - Spec/Plan/Tasks Consistency Validator

Validates that spec.md, plan.md, and tasks.md are consistent
before allowing transition from PLANNING to EXECUTING.

Gate checks:
1. Each user story has at least one task
2. Each P0/P1 task has verification and acceptance
3. owned_files have no obvious conflicts or conflicts are explicitly grouped
4. .contract.json is no longer draft/placeholder

Usage:
    from analyze_gate import AnalyzeGate, validate_analyze_gate

    gate = AnalyzeGate(workdir)
    result = gate.validate()
    if not result["passed"]:
        print("Gate failed:", result["errors"])
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict


@dataclass
class AnalyzeResult:
    """Result of analyze gate validation"""
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.passed = False

    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)


class AnalyzeGate:
    """
    Analyze gate for spec/plan/tasks consistency.

    Validates:
    - User stories have corresponding tasks
    - P0/P1 tasks have verification methods
    - No placeholder content in critical fields
    - Task provenance is tracked
    """

    def __init__(self, workdir: str = "."):
        self.workdir = Path(workdir)
        self.specs_dir = self.workdir / ".specs"

    def validate(self) -> AnalyzeResult:
        """
        Run all analyze gate validations.

        Returns:
            AnalyzeResult with passed status and error/warning list
        """
        result = AnalyzeResult(passed=True)

        # Run all validations
        self._check_spec_exists(result)
        self._check_needs_clarification(result)
        self._check_tasks_has_provenance(result)
        self._check_story_task_mapping(result)
        self._check_p0_p1_has_verification(result)
        self._check_contract_not_draft(result)
        self._check_owned_files_consistency(result)

        return result

    def _check_spec_exists(self, result: AnalyzeResult) -> None:
        """Check that spec.md exists in .specs directory."""
        spec_dirs = list(self.specs_dir.glob("*/spec.md"))
        if not spec_dirs:
            result.add_error("No spec.md found in .specs/ directory. Create at least one spec.")
            return

        # Check if spec has content
        spec_file = spec_dirs[0]
        content = spec_file.read_text(encoding="utf-8")

        if len(content) < 200:
            result.add_error(f"spec.md at {spec_file} is too short (< 200 chars). Add user stories and requirements.")
            return

        # Check for placeholder content
        if "[Title]" in content or "[Task title]" in content:
            result.add_warning(f"spec.md at {spec_file} still has placeholder content. Fill in actual details.")

    def _check_needs_clarification(self, result: AnalyzeResult) -> None:
        """Check if spec.md needs clarification (ambiguous or incomplete)."""
        spec_dirs = list(self.specs_dir.glob("*/spec.md"))
        if not spec_dirs:
            return  # Already reported by _check_spec_exists

        spec_file = spec_dirs[0]
        content = spec_file.read_text(encoding="utf-8")

        # Check for explicit NEEDS CLARIFICATION marker
        if "[NEEDS CLARIFICATION]" in content or "[needs clarification]" in content.lower():
            result.add_error("spec.md contains [NEEDS CLARIFICATION] marker. Clarify requirements before proceeding.")

        # Check for empty acceptance criteria (after Story N: but before next section)
        story_blocks = re.split(r"### Story \d+:", content)
        for i, block in enumerate(story_blocks[1:], start=1):  # Skip first (intro content)
            # Find acceptance criteria in this block
            acceptance_match = re.search(r"\*\*Acceptance Criteria:\*\*\s*\n((?:\s*-\s*[^\n]+\n)+)", block)
            if acceptance_match:
                criteria_text = acceptance_match.group(1)
                # Check if all criteria are placeholders
                if all(
                    re.match(r"^\s*-\s*\[?\s*[xX ]?\s*\]?\s*\[?[^\]]*\]?\s*$", line) or
                    re.search(r"\[verifiable outcome\]", line, re.IGNORECASE)
                    for line in criteria_text.split("\n") if line.strip()
                ):
                    result.add_error(f"User Story {i} has only placeholder acceptance criteria. Provide real criteria.")
            else:
                # No acceptance criteria found - check if this looks like a real story
                # (has As a / I want / So that)
                if re.search(r"\*\*As a\*\*", block) and not re.search(r"\*\*Acceptance Criteria:\*\*", block):
                    result.add_error(f"User Story {i} is missing acceptance criteria. Add concrete, testable criteria.")

        # Check for ambiguous phrases
        ambiguous_phrases = ["TBD", "to be determined", "to be decided", "flexible", "optional"]
        for phrase in ambiguous_phrases:
            if phrase.lower() in content.lower():
                # Only error if in critical sections (User Stories, Success Criteria)
                if "user story" in content.lower() or "success criteria" in content.lower():
                    result.add_warning(f"spec.md contains '{phrase}' - clarify for precise requirements.")

    def _check_tasks_has_provenance(self, result: AnalyzeResult) -> None:
        """Check that tasks.md has provenance header."""
        task_files = list(self.specs_dir.glob("*/tasks.md"))

        if not task_files:
            result.add_error("No tasks.md found. Generate tasks.md from spec.")
            return

        task_file = task_files[0]
        content = task_file.read_text(encoding="utf-8")

        # Check for provenance header
        required_headers = ["Generated-By:", "Session:", "Source-Spec:", "Timestamp:"]
        for header in required_headers:
            if header not in content:
                result.add_error(f"tasks.md missing required provenance header: {header}")

    def _check_story_task_mapping(self, result: AnalyzeResult) -> None:
        """Check that each user story has at least one task."""
        spec_files = list(self.specs_dir.glob("*/spec.md"))
        task_files = list(self.specs_dir.glob("*/tasks.md"))

        if not spec_files or not task_files:
            return  # Already reported by other checks

        spec_content = spec_files[0].read_text(encoding="utf-8")
        task_content = task_files[0].read_text(encoding="utf-8")

        # Extract user story IDs from spec
        story_pattern = re.compile(r"### Story (\d+):")
        spec_stories = set(story_pattern.findall(spec_content))

        # Extract task story assignments from tasks
        task_story_pattern = re.compile(r"TASK-US(\d+)-\d+")
        task_stories = set(task_story_pattern.findall(task_content))

        # Check each spec story has tasks
        for story_id in spec_stories:
            if story_id not in task_stories:
                result.add_error(f"User Story {story_id} has no corresponding tasks. Add tasks for US-{story_id}.")

    def _check_p0_p1_has_verification(self, result: AnalyzeResult) -> None:
        """Check that each P0/P1 task has a verification method."""
        task_files = list(self.specs_dir.glob("*/tasks.md"))
        if not task_files:
            return

        task_content = task_files[0].read_text(encoding="utf-8")

        # Pattern to find verification method after task line
        verification_pattern = re.compile(r"\*\*Verification:\*\* (?:\[P\] )?([^\n]+)")

        # Find all task blocks
        task_blocks = re.split(r"- \[ \] \*\*TASK-", task_content)
        for block in task_blocks[1:]:  # Skip first empty split
            task_match = re.match(r"([^-]+-\d+):\*\* ([^\n]+)", block)
            if not task_match:
                continue

            task_id = task_match.group(1)
            task_title = task_match.group(2).strip()

            # Check if P0 or P1
            is_high_priority = "P0" in task_title or "P1" in task_title or task_id.startswith("FOUND")

            # Find verification for this task
            # Look for verification after this task
            verification_match = verification_pattern.search(block)
            if not verification_match:
                if is_high_priority:
                    result.add_error(f"Task {task_id} is high priority but has no verification method.")
            else:
                verification = verification_match.group(1).strip()
                if not verification or verification == "[verification command]":
                    if is_high_priority:
                        result.add_error(f"Task {task_id} has placeholder verification. Provide actual test command.")

    def _check_contract_not_draft(self, result: AnalyzeResult) -> None:
        """Check that .contract.json exists and is not draft."""
        contract_path = self.workdir / ".contract.json"

        if not contract_path.exists():
            result.add_warning(".contract.json does not exist. Will be generated from spec/plan.")
            return

        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            status = contract.get("status", "unknown")

            if status == "draft":
                result.add_error(".contract.json status is 'draft'. Update to 'active' after planning complete.")
                return

            # Check for placeholder content
            goals = contract.get("goals", [])
            if not goals:
                result.add_warning(".contract.json has no goals defined.")
            else:
                placeholder_patterns = ["to be filled", "(to be", "placeholder", "tbd"]
                has_real_goals = any(
                    not any(p.lower() in g.lower() for p in placeholder_patterns)
                    for g in goals
                )
                if not has_real_goals:
                    result.add_error("Contract goals are all placeholders. Fill in actual goals.")

        except (OSError, json.JSONDecodeError) as e:
            result.add_warning(f"Could not read .contract.json: {e}")

    def _check_owned_files_consistency(self, result: AnalyzeResult) -> None:
        """Check that owned_files in tasks don't have obvious conflicts."""
        task_files = list(self.specs_dir.glob("*/tasks.md"))
        if not task_files:
            return

        task_content = task_files[0].read_text(encoding="utf-8")

        # Extract all file paths from tasks
        file_pattern = re.compile(r"\*\*Files:\*\* ([^\n]+)")
        file_paths = set()
        for match in file_pattern.finditer(task_content):
            paths_str = match.group(1)
            # Split by comma and clean
            paths = [p.strip().replace("`", "").replace("*", "") for p in paths_str.split(",")]
            for path in paths:
                if path and not path.startswith("["):
                    file_paths.add(path)

        # Check for common conflicts (same directory claimed by multiple tasks)
        dir_to_files: dict[str, list[str]] = {}
        for fp in file_paths:
            parent = str(Path(fp).parent)
            if parent not in dir_to_files:
                dir_to_files[parent] = []
            dir_to_files[parent].append(fp)

        # A conflict exists if multiple files in same dir are claimed by different tasks
        # This is informational - conflicts are allowed if intentionally grouped
        for dir_path, files in dir_to_files.items():
            if len(files) > 3:
                result.add_warning(f"Directory {dir_path} has {len(files)} files claimed. Ensure conflicts are intentional.")


def generate_spec_checklist(workdir: str = ".") -> Dict[str, Any]:
    """
    Generate a checklist for spec/plan validation.

    Returns a dict with:
    - spec_checklist: list of (criterion, passed, details) tuples
    - plan_checklist: list of (criterion, passed, details) tuples
    - overall_score: float (0.0 to 1.0)
    - recommendations: list of strings
    """
    gate = AnalyzeGate(workdir)
    result = gate.validate()

    checklist = {
        "spec_checklist": [],
        "plan_checklist": [],
        "overall_score": 1.0 if result.passed else 0.0,
        "recommendations": [],
    }

    # Spec quality criteria
    spec_dirs = list(Path(workdir).glob(".specs/*/spec.md"))
    if spec_dirs:
        spec_content = spec_dirs[0].read_text(encoding="utf-8")

        # Check 1: Has user stories
        has_stories = bool(re.search(r"### Story \d+:", spec_content))
        checklist["spec_checklist"].append({
            "criterion": "Has user stories",
            "passed": has_stories,
            "details": f"Found {len(re.findall(r'### Story \d+:', spec_content))} user stories" if has_stories else "No user stories found",
        })

        # Check 2: User stories have acceptance criteria
        story_blocks = re.split(r"### Story \d+:", spec_content)
        stories_with_criteria = 0
        for block in story_blocks[1:]:
            if re.search(r"\*\*Acceptance Criteria:\*\*", block):
                stories_with_criteria += 1
        checklist["spec_checklist"].append({
            "criterion": "Stories have acceptance criteria",
            "passed": stories_with_criteria == len(story_blocks) - 1,
            "details": f"{stories_with_criteria}/{len(story_blocks) - 1} stories have acceptance criteria",
        })

        # Check 3: Has success criteria
        has_sc = bool(re.search(r"## Success Criteria", spec_content, re.IGNORECASE))
        checklist["spec_checklist"].append({
            "criterion": "Has success criteria",
            "passed": has_sc,
            "details": "Has Success Criteria section" if has_sc else "No Success Criteria section found",
        })

        # Check 4: No placeholder titles
        has_placeholders = "[Title]" in spec_content or "[Task title]" in spec_content
        checklist["spec_checklist"].append({
            "criterion": "No placeholder content",
            "passed": not has_placeholders,
            "details": "Contains placeholders" if has_placeholders else "No placeholders found",
        })

        # Check 5: Has constraints or assumptions
        has_constraints = bool(re.search(r"## (Constraints|Assumptions)", spec_content, re.IGNORECASE))
        checklist["spec_checklist"].append({
            "criterion": "Has constraints/assumptions",
            "passed": has_constraints,
            "details": "Has Constraints or Assumptions section" if has_constraints else "No constraints/assumptions found",
        })

    # Calculate score
    if checklist["spec_checklist"]:
        passed = sum(1 for c in checklist["spec_checklist"] if c["passed"])
        total = len(checklist["spec_checklist"])
        checklist["overall_score"] = passed / total if total > 0 else 0.0

    # Generate recommendations based on failures
    for item in checklist["spec_checklist"]:
        if not item["passed"]:
            checklist["recommendations"].append(f"Fix: {item['criterion']} - {item['details']}")

    return checklist


def check_template_drift(repo_skill_path: str, installed_skill_path: str) -> Dict[str, Any]:
    """
    Check for drift between repo SKILL.md and installed SKILL.md.

    Args:
        repo_skill_path: Path to the repo's SKILL.md
        installed_skill_path: Path to the installed skill's SKILL.md

    Returns:
        Dict with:
        - has_drift: bool
        - drift_details: list of (field, repo_value, installed_value) tuples
        - repo_hash: str (hash of repo version)
        - installed_hash: str (hash of installed version)
    """
    import hashlib

    def hash_file(path: str) -> str:
        """Compute SHA256 hash of a file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return hashlib.sha256(content.encode()).hexdigest()[:12]
        except (OSError, IOError):
            return "not-found"

    result = {
        "has_drift": False,
        "drift_details": [],
        "repo_hash": hash_file(repo_skill_path),
        "installed_hash": hash_file(installed_skill_path),
    }

    try:
        with open(repo_skill_path, "r", encoding="utf-8") as f:
            repo_content = f.read()
        with open(installed_skill_path, "r", encoding="utf-8") as f:
            installed_content = f.read()

        if repo_content != installed_content:
            result["has_drift"] = True

            # Compare key sections
            repo_lines = repo_content.split("\n")
            installed_lines = installed_content.split("\n")

            # Check for missing sections
            repo_sections = set()
            installed_sections = set()
            for line in repo_lines:
                if line.startswith("# ") and len(line) > 2:
                    repo_sections.add(line[2:].strip())
            for line in installed_lines:
                if line.startswith("# ") and len(line) > 2:
                    installed_sections.add(line[2:].strip())

            missing_in_installed = repo_sections - installed_sections
            extra_in_installed = installed_sections - repo_sections

            if missing_in_installed:
                result["drift_details"].append({
                    "type": "missing_sections",
                    "details": f"Sections in repo but not installed: {', '.join(missing_in_installed)}",
                })
            if extra_in_installed:
                result["drift_details"].append({
                    "type": "extra_sections",
                    "details": f"Sections in installed but not repo: {', '.join(extra_in_installed)}",
                })

            # Check version field
            repo_version = re.search(r"version:\s*(\d+\.\d+\.\d+)", repo_content)
            installed_version = re.search(r"version:\s*(\d+\.\d+\.\d+)", installed_content)
            if repo_version and installed_version:
                if repo_version.group(1) != installed_version.group(1):
                    result["drift_details"].append({
                        "type": "version_mismatch",
                        "details": f"Repo version {repo_version.group(1)} vs installed {installed_version.group(1)}",
                    })

    except (OSError, IOError) as e:
        result["drift_details"].append({
            "type": "read_error",
            "details": str(e),
        })

    return result


def validate_analyze_gate(workdir: str = ".") -> AnalyzeResult:
    """
    Convenience function to run analyze gate validation.

    Args:
        workdir: Working directory

    Returns:
        AnalyzeResult with passed status and error/warning list
    """
    gate = AnalyzeGate(workdir)
    return gate.validate()


# CLI entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze Gate - Spec/Plan/Tasks Validator")
    parser.add_argument("--workdir", default=".", help="Working directory")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    result = validate_analyze_gate(args.workdir)

    if result.passed:
        print("✅ Analyze gate PASSED")
    else:
        print("❌ Analyze gate FAILED")

    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  - {error}")

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  - {warning}")

    if args.strict and result.warnings:
        print("\n⚠️ Strict mode: Treating warnings as errors")
        raise SystemExit(1)

    raise SystemExit(0 if result.passed else 1)
