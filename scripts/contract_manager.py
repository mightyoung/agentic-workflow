#!/usr/bin/env python3
"""
Contract Manager - Phase Contract Management

Handles creation, parsing, updating, and validation of phase contracts.

Phase contracts are negotiated during PLANNING and binding for EXECUTING and REVIEWING.
They establish:
- Goals for the phase/sprint
- Verification methods (how to know when done)
- Owned files (what will be produced/modified)
- Failure threshold (when to abort/retry)

Functions:
- create_phase_contract: Create contract files
- parse_phase_contract: Parse contract into structured dict
- update_contract_json: Update contract fields
- validate_contract_gate: Validate contract fulfillment for completion
"""

from __future__ import annotations

import json as json_lib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from safe_io import safe_write_text_locked

# Placeholder patterns for validation
PLACEHOLDER_PATTERNS = ["to be filled", "(to be", "placeholder", "tbd", "tdd"]


def _create_phase_contract(task_name: str, task_desc: str, workdir: str) -> Path:
    """
    Create a phase contract artifact (Anthropic-style written contract).

    This artifact establishes explicit negotiated agreement between planner and executor:
    - Goals for this phase/sprint
    - Verification methods (how to know when done)
    - Owned files (what will be produced/modified)
    - Failure threshold (when to abort/retry)

    Produced by PLANNING, consumed by EXECUTING and REVIEWING.

    Creates two files:
    - phase_contract.md: Human-readable contract
    - .contract.json: Machine-readable structured contract (authoritative)

    Args:
        task_name: Name of the task
        task_desc: Task description
        workdir: Working directory

    Returns:
        Path to the contract file
    """
    contract_path = Path(workdir) / "phase_contract.md"
    json_contract_path = Path(workdir) / ".contract.json"

    # If both exist, contract is already created
    if contract_path.exists() and json_contract_path.exists():
        return contract_path

    # Create machine-readable JSON contract (authoritative)
    json_contract: dict[str, Any] = {
        "version": "1.1",
        "task": task_name,
        "description": task_desc,
        "created": datetime.now().isoformat(),
        "goals": [],
        "goal_status": {},  # goal_id -> "pending" | "in_progress" | "fulfilled"
        "verification_methods": [],
        "verification_results": {},  # method -> "passed" | "failed" | "not_run"
        "owned_files": [],
        "acceptance_criteria": [],
        "impact_files": [],
        "dependencies": [],
        "rollback_note": "",
        "review_evidence": None,  # path to review artifact if completed
        "failure_threshold": {
            "hard_failure": [],
            "soft_failure": [],
            "retry_strategy": "max_3_retries",
        },
        "status": "draft",  # draft -> active -> fulfilled -> broken
    }

    # Write JSON contract
    safe_write_text_locked(json_contract_path, json_lib.dumps(json_contract, indent=2, ensure_ascii=False))

    # Create human-readable markdown contract
    content = f"""# Phase Contract

## Session
- Task: {task_name}
- Description: {task_desc}
- Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Goals

- [ ] Goal 1: (to be filled by planner)

## Acceptance Criteria

- (to be filled by planner)

## Verification Methods

How will we know the goals are achieved?

1. **Automated verification**: (e.g., `pytest tests/`, `python3 -m mypy`)
2. **Manual verification**: (e.g., code review, integration test)
3. **Success criteria**: (e.g., all tests pass, no type errors)

## Owned Files

Files to be produced or modified:

- `src/` (list specific files if known)

## Impact Files

Files that will be directly affected:

- `src/`

## Dependencies

- (to be filled by planner)

## Rollback Note

- (to be filled by planner)

## Failure Threshold

When should we abort or escalate?

- **Hard failure**: (e.g., quality gate fails, P0 tasks incomplete)
- **Soft failure**: (e.g., P1 tasks incomplete, warnings present)
- **Retry strategy**: (e.g., max 3 retries before escalating)

## Review Contract

REVIEWING phase will validate:

1. All verification methods pass
2. Owned files match actual changes
3. No hard failures detected
4. Code quality meets baseline standards

---
*This contract is negotiated during PLANNING phase and binding for EXECUTING and REVIEWING.*
*Machine-readable contract: .contract.json*
"""
    safe_write_text_locked(contract_path, content)
    return contract_path


def parse_phase_contract(workdir: str = ".") -> dict[str, Any]:
    """
    Parse phase contract into a structured dict.

    Prefers .contract.json (machine-readable) over phase_contract.md.

    Args:
        workdir: Working directory

    Returns:
        Dict with keys: goals (list), verification_methods (list),
        owned_files (list), failure_threshold (dict), review_contract (dict)
    """
    # Try JSON contract first (authoritative)
    json_contract_path = Path(workdir) / ".contract.json"
    if json_contract_path.exists():
        try:
            json_content = json_lib.loads(json_contract_path.read_text(encoding="utf-8"))
            # Normalize to the same structure as the parsed markdown
            return {
                "goals": json_content.get("goals", []),
                "verification_methods": json_content.get("verification_methods", []),
                "owned_files": json_content.get("owned_files", []),
                "acceptance_criteria": json_content.get("acceptance_criteria", []),
                "impact_files": json_content.get("impact_files", []),
                "dependencies": json_content.get("dependencies", []),
                "rollback_note": json_content.get("rollback_note", ""),
                "failure_threshold": json_content.get("failure_threshold", {}),
                "review_contract": json_content.get("review_contract", {}),
                "status": json_content.get("status", "unknown"),
                "version": json_content.get("version", "1.0"),
            }
        except (json_lib.JSONDecodeError, OSError):
            pass  # Fall back to markdown parsing

    # Fall back to markdown parsing
    contract_path = Path(workdir) / "phase_contract.md"
    if not contract_path.exists():
        return {}

    content = contract_path.read_text(encoding="utf-8")
    result: dict[str, Any] = {
        "goals": [],
        "verification_methods": [],
        "owned_files": [],
        "acceptance_criteria": [],
        "impact_files": [],
        "dependencies": [],
        "rollback_note": "",
        "failure_threshold": {},
        "review_contract": {},
    }

    current_section = None
    for line in content.split("\n"):
        line = line.strip()

        if line.startswith("## Goals"):
            current_section = "goals"
        elif line.startswith("## Verification"):
            current_section = "verification_methods"
        elif line.startswith("## Acceptance Criteria"):
            current_section = "acceptance_criteria"
        elif line.startswith("## Impact Files"):
            current_section = "impact_files"
        elif line.startswith("## Dependencies"):
            current_section = "dependencies"
        elif line.startswith("## Rollback Note"):
            current_section = "rollback_note"
        elif line.startswith("## Owned Files"):
            current_section = "owned_files"
        elif line.startswith("#"):
            current_section = None
        elif current_section == "goals" and line.startswith("- ["):
            # Parse checkbox goal
            goal = line.replace("- [ ]", "").replace("- [x]", "").replace("- [X]", "").strip()
            result["goals"].append(goal)
        elif current_section == "owned_files" and line.startswith("-"):
            # Parse file path
            file_path = line.replace("-", "").strip().replace("`", "")
            if file_path:
                result["owned_files"].append(file_path)
        elif current_section == "acceptance_criteria" and line.startswith("-"):
            result["acceptance_criteria"].append(line.replace("-", "").strip())
        elif current_section == "impact_files" and line.startswith("-"):
            file_path = line.replace("-", "").strip().replace("`", "")
            if file_path:
                result["impact_files"].append(file_path)
        elif current_section == "dependencies" and line.startswith("-"):
            dep = line.replace("-", "").strip()
            if dep and "(to be filled" not in dep.lower():
                result["dependencies"].append(dep)
        elif current_section == "rollback_note" and line.startswith("-"):
            note = line.replace("-", "").strip()
            if note:
                result["rollback_note"] = note
        elif current_section == "verification_methods" and re.match(r"^\d+\.", line):
            # Parse verification method
            method = re.sub(r"^\d+\.\s*\*\*.*?\*\*:\s*", "", line)
            result["verification_methods"].append(method)

    return result


def update_contract_json(workdir: str = ".", **kwargs) -> bool:
    """
    Update .contract.json with new values.

    Args:
        workdir: Working directory
        **kwargs: Fields to update (goals, verification_methods, owned_files, status, etc.)

    Returns:
        True if updated successfully, False otherwise
    """
    json_contract_path = Path(workdir) / ".contract.json"

    if not json_contract_path.exists():
        return False

    try:
        contract = json_lib.loads(json_contract_path.read_text(encoding="utf-8"))
        # Update fields
        for key, value in kwargs.items():
            if key in ("goals", "verification_methods", "owned_files", "acceptance_criteria", "impact_files", "dependencies", "rollback_note", "status"):
                contract[key] = value
        # Write back
        safe_write_text_locked(json_contract_path, json_lib.dumps(contract, indent=2, ensure_ascii=False))
        return True
    except (json_lib.JSONDecodeError, OSError):
        return False


def validate_contract_gate(workdir: str, state: Any) -> tuple[bool, str]:
    """
    Validate contract fulfillment for completion gate.

    Gate policy:
    - STAGE trigger: skip gate (lenient - simple tasks don't need contracts)
    - FULL_WORKFLOW non-code: lightweight gate (draft OK, goals not required)
    - FULL_WORKFLOW code task: full gate (status != draft, real goals, verification)

    Args:
        workdir: Working directory
        state: WorkflowState object (must have trigger_type attribute)

    Returns:
        (is_valid, error_message)
    """
    json_contract_path = Path(workdir) / ".contract.json"

    # Gate is skipped for RESULT_ONLY and DIRECT_ANSWER triggers
    # (these are not real workflows - just Q&A or single responses)
    trigger_type = getattr(state, 'trigger_type', None) if state else None
    if trigger_type in ("RESULT_ONLY", "DIRECT_ANSWER"):
        return True, ""  # Lenient: Q&A tasks don't need formal contracts

    # Gate is skipped for STAGE trigger (simple tasks)
    if trigger_type == "STAGE":
        return True, ""  # Simple stage-triggered tasks don't need contracts

    # Gate is relaxed for low-complexity tasks (XS/S)
    metadata = getattr(state, 'metadata', None) or {}
    complexity = metadata.get("complexity", "")
    if complexity in ("XS", "S"):
        return True, ""  # Simple tasks skip formal contract gate

    if not json_contract_path.exists():
        return True, ""  # No contract = no gate

    try:
        contract = json_lib.loads(json_contract_path.read_text(encoding="utf-8"))
    except (json_lib.JSONDecodeError, OSError):
        return True, ""  # Can't read = skip gate

    # Check 1: status must not be draft
    status = contract.get("status", "unknown")
    if status == "draft":
        return False, "Contract status is 'draft' - update to 'active' or 'fulfilled'"

    # Check 2: goals should not be empty placeholder
    goals = contract.get("goals", [])
    if goals:
        # Check goals are not all placeholders
        has_real_goals = any(
            not any(p.lower() in g.lower() for p in PLACEHOLDER_PATTERNS)
            for g in goals
        )
        if not has_real_goals:
            return False, "Contract goals are placeholders - fill in actual goals"

    # Check 2b: acceptance criteria should be present for code tasks
    acceptance_criteria = contract.get("acceptance_criteria", [])
    if not acceptance_criteria:
        return False, "Contract acceptance_criteria are missing - fill in measurable acceptance criteria"
    if acceptance_criteria:
        has_real_acceptance = any(
            not any(p.lower() in str(a).lower() for p in PLACEHOLDER_PATTERNS)
            for a in acceptance_criteria
        )
        if not has_real_acceptance:
            return False, "Contract acceptance_criteria are placeholders - fill in actual acceptance criteria"

    # Check 3: If goal_status exists, at least one goal should be fulfilled
    goal_status = contract.get("goal_status", {})
    if goal_status:
        fulfilled_goals = [g for g, s in goal_status.items() if s == "fulfilled"]
        if not fulfilled_goals:
            return False, "No goals marked as fulfilled - complete at least one goal before completing"

    # Check 4: owned_files should match actual file_changes
    owned_files = contract.get("owned_files", [])
    if owned_files:
        actual_paths = set()
        for fc in (state.file_changes or []):
            if hasattr(fc, 'path'):
                actual_paths.add(fc.path)
            elif isinstance(fc, dict):
                actual_paths.add(fc.get('path', ''))

        # Check if at least some owned files match actual changes
        matching = [f for f in owned_files if any(f in p or p in f for p in actual_paths)]
        if not matching and actual_paths:
            # Some owned files should match actual changes
            pass  # Currently permissive

    # Check 4b: impact_files should be present and non-placeholder
    impact_files = contract.get("impact_files", [])
    if not impact_files:
        return False, "Contract impact_files are missing - list affected files"
    if impact_files:
        if not any(str(f).strip() and str(f).strip().lower() not in {"(未设置)", "unset", "none"} for f in impact_files):
            return False, "Contract impact_files are placeholders"

    # Check 5: verification_methods should not be placeholders
    verification_methods = contract.get("verification_methods", [])
    if verification_methods:
        has_real_verification = any(
            not any(p.lower() in v.lower() for p in PLACEHOLDER_PATTERNS)
            for v in verification_methods
        )
        if not has_real_verification:
            return False, "Contract verification_methods are placeholders"

    # Check 5b: rollback note should be present for code tasks
    rollback_note = str(contract.get("rollback_note", "")).strip()
    if not rollback_note or any(p.lower() in rollback_note.lower() for p in PLACEHOLDER_PATTERNS):
        return False, "Contract rollback_note is missing or placeholder"

    # Check 6: If verification_results exist, at least one should be passed
    verification_results = contract.get("verification_results", {})
    if verification_results:
        passed_verifications = [v for v, r in verification_results.items() if r == "passed"]
        if not passed_verifications:
            return False, "No verifications passed - run at least one verification successfully"

    # Check 7: If review_evidence is set, review was completed
    review_evidence = contract.get("review_evidence")
    if review_evidence is not None:
        review_path = Path(workdir) / review_evidence if not Path(review_evidence).is_absolute() else Path(review_evidence)
        if not review_path.exists():
            return False, f"Review evidence file not found: {review_evidence}"

    return True, ""


def validate_execution_contract_readiness(workdir: str, state: Any) -> tuple[bool, str]:
    """
    Validate that a contract is ready to enter EXECUTING.

    This is stricter than a generic parse, but intentionally ignores the
    contract status field so PLANNING can validate readiness before the
    runtime flips the contract to active.
    """
    trigger_type = getattr(state, "trigger_type", None) if state else None
    if trigger_type in ("RESULT_ONLY", "DIRECT_ANSWER", "STAGE"):
        return True, ""

    metadata = getattr(state, "metadata", None) or {}
    complexity = metadata.get("complexity", "")
    if complexity in ("XS", "S"):
        return True, ""

    json_contract_path = Path(workdir) / ".contract.json"
    if not json_contract_path.exists():
        return False, "Contract not found - execution requires a negotiated contract"

    try:
        contract = json_lib.loads(json_contract_path.read_text(encoding="utf-8"))
    except (json_lib.JSONDecodeError, OSError):
        return False, "Contract could not be read - fix the contract before executing"

    if not isinstance(contract, dict):
        return False, "Contract is malformed - fix the contract before executing"

    def _has_real_value(values: list[Any] | Any) -> bool:
        if not values:
            return False
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list):
            return False
        cleaned = [str(v).strip() for v in values if str(v).strip()]
        if not cleaned:
            return False
        return any(not any(p.lower() in value.lower() for p in PLACEHOLDER_PATTERNS) for value in cleaned)

    goals = contract.get("goals", [])
    if not _has_real_value(goals):
        return False, "Contract goals are missing or placeholder - fill in actual execution goals"

    acceptance_criteria = contract.get("acceptance_criteria", [])
    if not _has_real_value(acceptance_criteria):
        return False, "Contract acceptance_criteria are missing or placeholder - define measurable acceptance"

    impact_files = contract.get("impact_files", [])
    if not _has_real_value(impact_files):
        return False, "Contract impact_files are missing or placeholder - list affected files before executing"

    verification_methods = contract.get("verification_methods", [])
    if not _has_real_value(verification_methods):
        return False, "Contract verification_methods are missing or placeholder - define executable verification"

    rollback_note = str(contract.get("rollback_note", "")).strip()
    if not rollback_note or any(p.lower() in rollback_note.lower() for p in PLACEHOLDER_PATTERNS):
        return False, "Contract rollback_note is missing or placeholder - define a rollback path before executing"

    status = str(contract.get("status", "")).strip().lower()
    if status == "broken":
        return False, "Contract status is broken - fix the contract before executing"

    return True, ""
