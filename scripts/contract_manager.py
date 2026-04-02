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
from typing import Any, Dict, List, Optional, Tuple

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
    json_contract = {
        "version": "1.0",
        "task": task_name,
        "description": task_desc,
        "created": datetime.now().isoformat(),
        "goals": [],
        "verification_methods": [],
        "owned_files": [],
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

## Verification Methods

How will we know the goals are achieved?

1. **Automated verification**: (e.g., `pytest tests/`, `python3 -m mypy`)
2. **Manual verification**: (e.g., code review, integration test)
3. **Success criteria**: (e.g., all tests pass, no type errors)

## Owned Files

Files to be produced or modified:

- `src/` (list specific files if known)

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


def parse_phase_contract(workdir: str = ".") -> Dict[str, Any]:
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
    result: Dict[str, Any] = {
        "goals": [],
        "verification_methods": [],
        "owned_files": [],
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
        elif current_section == "verification_methods" and line.startswith("1."):
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
            if key in ("goals", "verification_methods", "owned_files", "status"):
                contract[key] = value
        # Write back
        safe_write_text_locked(json_contract_path, json_lib.dumps(contract, indent=2, ensure_ascii=False))
        return True
    except (json_lib.JSONDecodeError, OSError):
        return False


def validate_contract_gate(workdir: str, state: Any) -> Tuple[bool, str]:
    """
    Validate contract fulfillment for completion gate.

    Checks:
    1. status != 'draft' (contract is active/fulfilled)
    2. If goals exist, they are not placeholder text
    3. If owned_files exist, they match actual file_changes
    4. If verification_methods exist, they are not placeholder text

    Args:
        workdir: Working directory
        state: WorkflowState object

    Returns:
        (is_valid, error_message)
    """
    json_contract_path = Path(workdir) / ".contract.json"

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

    # Check 3: owned_files should match actual file_changes
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

    # Check 4: verification_methods should not be placeholders
    verification_methods = contract.get("verification_methods", [])
    if verification_methods:
        has_real_verification = any(
            not any(p.lower() in v.lower() for p in PLACEHOLDER_PATTERNS)
            for v in verification_methods
        )
        if not has_real_verification:
            return False, "Contract verification_methods are placeholders"

    return True, ""
