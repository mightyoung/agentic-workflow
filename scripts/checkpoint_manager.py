#!/usr/bin/env python3
"""
Checkpoint Manager - Workflow State Persistence

Provides conditional checkpoint functionality for workflow recovery.
Creates snapshots and handoff documents at strategic points.

Functions:
- CheckpointConfig: Configuration for checkpoint triggers
- should_checkpoint: Determines if conditions warrant a checkpoint
- conditional_checkpoint: Creates checkpoint files if conditions met

Usage:
    from checkpoint_manager import conditional_checkpoint, CheckpointConfig

    config = CheckpointConfig(phase_change_threshold=2, failure_threshold=1)
    result = conditional_checkpoint(".", config)
    if result["checkpoint_saved"]:
        print(f"Saved: {result['checkpoint_id']}")
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from safe_io import safe_write_text_locked
from unified_state import load_state

# Import from workflow_engine (local imports to avoid circular dependency at runtime)
_imported_fns: dict[str, Any] = {}


def _lazy_import_workflow_engine():
    """Lazily import functions from workflow_engine to avoid circular imports."""
    if not _imported_fns:
        import workflow_engine
        from safe_io import safe_write_json
        _imported_fns["parse_task_plan"] = workflow_engine.parse_task_plan
        _imported_fns["next_plan_tasks"] = workflow_engine.next_plan_tasks
        _imported_fns["safe_write_json"] = safe_write_json
        _imported_fns["parse_phase_contract"] = workflow_engine.parse_phase_contract
        _imported_fns["compute_frontier"] = workflow_engine.compute_frontier
    return _imported_fns


@dataclass
class CheckpointConfig:
    """
    Conditional checkpoint configuration.

    Attributes:
        phase_change_threshold: Trigger after N phase transitions (default 1)
        resume_threshold: Trigger after N resume attempts
        failure_threshold: Trigger after N failures
        step_threshold: Trigger after N workflow steps
        enabled: Whether auto-checkpoint is enabled
    """
    phase_change_threshold: int = 1
    resume_threshold: int = 2
    failure_threshold: int = 1
    step_threshold: int = 5
    enabled: bool = True


def should_checkpoint(
    workdir: str,
    config: CheckpointConfig | None = None,
) -> tuple[bool, str]:
    """
    Determine if a checkpoint should be triggered based on conditions.

    Conditions evaluated:
    - Phase changes since last checkpoint
    - Resume attempts
    - Failure count
    - Total workflow steps

    Args:
        workdir: Working directory
        config: Checkpoint configuration (uses defaults if None)

    Returns:
        (should_checkpoint, reason) tuple
    """
    if config is None:
        config = CheckpointConfig()

    if not config.enabled:
        return False, "checkpoint disabled"

    state = load_state(workdir)
    if state is None:
        return False, "no state"

    # Count phase transitions from workflow state
    if hasattr(state.phase, "get"):
        phase_history = state.phase.get("history", [])
    else:
        phase_history = getattr(state.phase, "history", []) if hasattr(state.phase, "history") else []
    phase_changes = len(phase_history)

    # Get counters from state attributes
    resume_count = getattr(state, "resume_count", 0)
    failure_count = getattr(state, "failure_count", 0)
    step_count = getattr(state, "step_count", 0)

    # Check each condition
    if phase_changes >= config.phase_change_threshold:
        return True, f"phase_change({phase_changes}) >= {config.phase_change_threshold}"
    if resume_count >= config.resume_threshold:
        return True, f"resume_count({resume_count}) >= {config.resume_threshold}"
    if failure_count >= config.failure_threshold:
        return True, f"failure_count({failure_count}) >= {config.failure_threshold}"
    if step_count >= config.step_threshold:
        return True, f"step_count({step_count}) >= {config.step_threshold}"

    return False, "no condition met"


def conditional_checkpoint(
    workdir: str,
    config: CheckpointConfig | None = None,
) -> dict[str, Any]:
    """
    Save a checkpoint if conditions are met.

    Creates:
    - .checkpoints/<checkpoint_id>.json: Full state snapshot
    - handoff_<checkpoint_id>.md: Human-readable handoff document

    Args:
        workdir: Working directory
        config: Checkpoint configuration (uses defaults if None)

    Returns:
        dict with keys:
            checkpoint_saved: bool
            reason: str
            checkpoint_id: str
            session_id: str
            files: list of created file paths
            error: str or None (present when checkpoint_saved is False)
            partial: bool (True if only JSON was saved, not handoff)
    """
    should_save, reason = should_checkpoint(workdir, config)

    if not should_save:
        return {"checkpoint_saved": False, "reason": reason, "error": None}

    fns = _lazy_import_workflow_engine()

    state = load_state(workdir)
    if state is None:
        return {"checkpoint_saved": False, "reason": "no state", "error": "workflow state not found"}

    session_id = state.session_id

    # Flush trajectory logger if active (lazy import to avoid circular dependency)
    try:
        import workflow_engine as _wf
        if session_id in _wf._active_loggers:
            _wf._active_loggers[session_id].flush()
    except (ImportError, AttributeError):
        pass  # Logger flush is best-effort; checkpoint proceeds regardless
    workdir_path = Path(workdir)

    # Generate checkpoint ID
    checkpoint_id = f"cp-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8]}"

    # Create checkpoints directory
    checkpoints_dir = workdir_path / ".checkpoints"
    checkpoints_dir.mkdir(exist_ok=True)

    # Snapshot current phase
    current_phase = state.phase.get("current", "UNKNOWN") if hasattr(state.phase, "get") else "UNKNOWN"

    # Load task plan if exists
    try:
        plan_tasks = fns["parse_task_plan"](workdir)
        next_tasks = fns["next_plan_tasks"](workdir)
    except Exception:
        plan_tasks = []
        next_tasks = []

    # Create checkpoint JSON
    checkpoint_data = {
        "checkpoint_id": checkpoint_id,
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
        "reason": reason,
        "phase": current_phase,
        "task": state.task.to_dict() if state.task else None,
        "plan_tasks": plan_tasks,
        "next_tasks": next_tasks,
        "artifacts": state.artifacts if hasattr(state, "artifacts") else [],
        "decisions": [d.to_dict() if hasattr(d, "to_dict") else d for d in state.decisions] if hasattr(state, "decisions") else [],
        "file_changes": state.file_changes if hasattr(state, "file_changes") else [],
    }

    # Write checkpoint JSON
    checkpoint_file = checkpoints_dir / f"{checkpoint_id}.json"
    handoff_file = workdir_path / f"handoff_{checkpoint_id}.md"

    try:
        fns["safe_write_json"](checkpoint_file, checkpoint_data)
    except Exception as e:
        return {
            "checkpoint_saved": False,
            "reason": reason,
            "checkpoint_id": checkpoint_id,
            "session_id": session_id,
            "files": [],
            "error": f"checkpoint JSON write failed: {e}",
        }

    # Parse contract and frontier state (optional - don't fail if these fail)
    try:
        contract_state = fns["parse_phase_contract"](workdir)
        frontier_state = fns["compute_frontier"](workdir)
    except Exception:
        contract_state = {}
        frontier_state = {"executable_frontier": [], "blocked_tasks": [], "conflict_groups": []}

    # Parse recent decisions (last 3)
    recent_decisions = []
    if hasattr(state, "decisions") and state.decisions:
        for d in state.decisions[-3:]:
            if hasattr(d, "to_dict"):
                recent_decisions.append(d.to_dict().get("decision", str(d)))
            elif isinstance(d, dict):
                recent_decisions.append(d.get("decision", str(d)))

    # Build handoff content
    handoff_content = f"""# Checkpoint Handoff: {checkpoint_id}

**Created**: {datetime.now().isoformat()}
**Reason**: {reason}
**Session**: {session_id}
**Phase**: {current_phase}

## Task
{state.task.title if state.task else "Unknown task"}

## Contract Status
"""
    if contract_state.get("goals"):
        handoff_content += f"- Goals: {len(contract_state['goals'])} defined\n"
        handoff_content += f"- Verification methods: {len(contract_state.get('verification_methods', []))} defined\n"
        handoff_content += f"- Owned files: {len(contract_state.get('owned_files', []))} tracked\n"
    else:
        handoff_content += "- No contract or contract not yet negotiated\n"

    handoff_content += f"""
## Current State
- Phase: {current_phase}
- Plan Tasks: {len(plan_tasks)} total, {len(next_tasks)} next
- Frontier: {len(frontier_state.get('executable_frontier', []))} ready, {len(frontier_state.get('blocked_tasks', []))} blocked, {len(frontier_state.get('conflict_groups', []))} conflict groups

## Next Tasks
"""
    for t in next_tasks[:5]:
        handoff_content += f"- [{t.get('id', '?')}] {t.get('title', 'Untitled')}\n"

    if recent_decisions:
        handoff_content += "\n## Recent Decisions\n"
        for d in recent_decisions:
            handoff_content += f"- {d}\n"

    # List key artifacts
    artifacts = list(state.artifacts) if hasattr(state, "artifacts") and state.artifacts else []
    if artifacts:
        handoff_content += "\n## Key Artifacts\n"
        for art in artifacts[:5]:
            if isinstance(art, dict):
                handoff_content += f"- {art.get('name', str(art))}\n"
            else:
                handoff_content += f"- {art}\n"

    handoff_content += f"""
## How to Resume
```bash
python3 scripts/workflow_engine.py --op resume --session-id {session_id} --workdir {workdir}
```

---
*This is an auto-generated handoff document. See .checkpoints/{checkpoint_id}.json for full state.*
"""

    # Write handoff file
    try:
        safe_write_text_locked(handoff_file, handoff_content)
    except Exception as e:
        # Handoff write failed but checkpoint JSON was saved
        return {
            "checkpoint_saved": True,
            "reason": reason,
            "checkpoint_id": checkpoint_id,
            "session_id": session_id,
            "files": [str(checkpoint_file)],
            "error": f"handoff write failed (checkpoint JSON saved): {e}",
            "partial": True,
        }

    return {
        "checkpoint_saved": True,
        "reason": reason,
        "checkpoint_id": checkpoint_id,
        "session_id": session_id,
        "files": [str(checkpoint_file), str(handoff_file)],
        "error": None,
    }
