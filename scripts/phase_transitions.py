"""
Phase transition helpers for the workflow state machine.

Provides:
- allowed_next_phases: list valid transitions from a phase
- recommend_next_phases: ordered recommendation of next phases
- validate_transition: raise ValueError if transition is illegal
"""

from __future__ import annotations

from unified_state import can_transition, get_allowed_transitions


def allowed_next_phases(phase: str) -> list[str]:
    return sorted(get_allowed_transitions(phase))


def recommend_next_phases(current_phase: str, trigger_type: str | None = None) -> list[str]:
    """
    Recommend the next phases reachable from the current phase.

    Args:
        current_phase: The current workflow phase
        trigger_type: Optional trigger type (FULL_WORKFLOW, STAGE, DIRECT_ANSWER)

    Returns:
        List of phase names that are valid next steps, ordered by recommendation priority
    """
    if current_phase == "DIRECT_ANSWER":
        return ["COMPLETE"]
    if current_phase == "PLANNING":
        return ["ANALYZING", "EXECUTING", "RESEARCH", "THINKING"]
    if current_phase == "ANALYZING":
        return ["EXECUTING", "PLANNING"]
    if current_phase == "RESEARCH":
        return ["THINKING", "PLANNING"]
    if current_phase == "THINKING":
        return ["PLANNING", "EXECUTING"]
    if current_phase == "EXECUTING":
        return ["REVIEWING", "COMPLETE", "DEBUGGING"]
    if current_phase == "REVIEWING":
        return ["COMPLETE", "DEBUGGING"]
    if current_phase == "DEBUGGING":
        return ["EXECUTING", "REVIEWING"]
    if current_phase == "COMPLETE":
        return []
    if trigger_type == "FULL_WORKFLOW":
        return ["PLANNING"]
    return allowed_next_phases(current_phase)


def validate_transition(current_phase: str, next_phase: str) -> None:
    """
    Validate that a phase transition is allowed by the state machine.

    Args:
        current_phase: Current phase
        next_phase: Desired next phase

    Raises:
        ValueError: If the transition is not allowed
    """
    if not can_transition(current_phase, next_phase):
        raise ValueError(f"illegal phase transition: {current_phase} -> {next_phase}")
