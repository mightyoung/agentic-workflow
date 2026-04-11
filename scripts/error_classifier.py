"""
Error classification and failure reflection helpers.

Provides:
- _ERROR_TYPE_PATTERNS: pattern dict for error type detection
- classify_error: classify an error string into (type, confidence)
- _get_error_history: extract error history from state decisions
- _should_escalate_skill_activation: decide if skill activation should escalate
- _extract_quality_gate_details: read latest quality gate report
- _persist_failure_reflection: write Reflexion-style failure note to disk + memory
- _build_debug_summary: build a structured debug summary dict
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from safe_io import safe_write_text_locked
from unified_state import ArtifactType, register_artifact


# Error classification patterns
_ERROR_TYPE_PATTERNS = {
    "test_failure": [
        "FAILED", "pytest", "test fail", "assertion error",
        "AssertionError", "test failed", "tests failed",
    ],
    "type_error": [
        "TypeError", "type error", "typing error",
        "cannot assign", "argument type", "expected ", "got ",
    ],
    "lint_error": [
        "lint", "ruff", "flake8", "pylint", "mypy",
        "unused import", "undefined name", "missing import",
    ],
    "runtime_exception": [
        "Exception", "Error:", "Traceback", "IndexError",
        "KeyError", "ValueError", "AttributeError", "ImportError",
    ],
    "syntax_error": [
        "SyntaxError", "IndentationError", "TabError",
        "unexpected EOF", "invalid syntax",
    ],
    "quality_gate_failed": [
        "quality gate", "gate failed", "gate_check",
    ],
}


def classify_error(error: str) -> tuple[str, float]:
    """
    Classify error type and return (error_type, confidence).

    Args:
        error: Error message string

    Returns:
        Tuple of (error_type, confidence_score)
    """
    error_lower = error.lower()
    scores: dict[str, float] = {}

    for error_type, patterns in _ERROR_TYPE_PATTERNS.items():
        score = sum(1 for p in patterns if p.lower() in error_lower)
        if score > 0:
            scores[error_type] = score / len(patterns)

    if not scores:
        return ("unknown", 1.0)

    # Return highest scoring type
    best_type = max(scores, key=lambda k: scores[k])
    return (best_type, scores[best_type])


def _get_error_history(state) -> list[dict[str, Any]]:
    """Extract error history from state decisions."""
    history = []
    for decision in state.decisions:
        if "error" in decision.metadata:
            history.append({
                "error": decision.metadata.get("error", ""),
                "type": decision.metadata.get("error_type", "unknown"),
                "timestamp": decision.timestamp,
            })
    return history


def _should_escalate_skill_activation(
    error: str,
    error_type: str,
    strategy: str,
    retry_count: int,
    error_history: list[dict[str, Any]],
) -> tuple[bool, str]:
    """
    Decide whether to escalate skill activation based on explicit failure events.

    Escalation is reserved for high-signal failures and repeated test failures.
    Generic recoverable failures should not automatically increase activation.
    """
    if strategy == "abort":
        return False, "abort strategy does not escalate skill activation"

    if error_type in {"syntax_error", "type_error", "quality_gate_failed"}:
        return True, f"high_signal_failure:{error_type}"

    if error_type == "test_failure":
        normalized_error = error[:120].lower()
        repeated_test_failure = any(
            item.get("type") == "test_failure" and item.get("error", "")[:120].lower() == normalized_error
            for item in error_history[-5:]
        )
        if repeated_test_failure or retry_count >= 1:
            return True, "repeated_test_failure"

    return False, "no escalation event"


def _extract_quality_gate_details(workdir: str) -> dict[str, Any] | None:
    """Extract quality gate failure details from latest gate report."""
    gate_files = list(Path(workdir).glob(".quality_gate_*.json"))
    if not gate_files:
        return None

    latest = max(gate_files, key=lambda p: p.stat().st_mtime)
    try:
        data = json.loads(latest.read_text())
        return {
            "gate_file": str(latest.name),
            "passed": data.get("all_passed", False),
            "failed_checks": data.get("failed_checks", []),
        }
    except Exception:
        return None


def _persist_failure_reflection(
    workdir: str,
    state,
    error: str,
    error_type: str,
    confidence: float,
    retry_hint: str,
    strategy: str,
    quality_gate_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist a Reflexion-style failure note into artifacts and long-term memory."""
    from memory_longterm import record_reflection_experience, search_memory

    session_id = state.session_id or "unknown"
    current_phase = state.phase.get("current", "IDLE") if state.phase else "IDLE"
    task_title = state.task.title if state.task else "Unknown task"
    task_desc = state.task.description if state.task else task_title
    memory_path = str(Path(workdir) / "MEMORY.md")
    memory_index_path = str(Path(workdir) / ".memory_index.jsonl")

    try:
        relevant_experiences = search_memory(
            error,
            filepath=memory_path,
            scope="project",
            limit=3,
            intent="debug",
        )
    except Exception:
        relevant_experiences = []

    trigger = f"{current_phase}::{strategy}"
    if quality_gate_details:
        trigger = f"{trigger}::quality_gate"

    signal_parts = [error_type]
    if quality_gate_details and quality_gate_details.get("failed_checks"):
        signal_parts.append(",".join(str(item) for item in quality_gate_details["failed_checks"][:3]))
    signal = " | ".join(signal_parts)

    next_hint = retry_hint or "inspect the failure and retry with tighter scope"
    reflection_path = Path(workdir) / f"reflection_{session_id}.md"
    reflection_content = f"""# Failure Reflection

## Context
- Session: {session_id}
- Phase: {current_phase}
- Strategy: {strategy}
- Error Type: {error_type}
- Confidence: {confidence:.2f}

## Task
{task_desc}

## Reflection
Task: {task_title}
Trigger: {trigger}
Mistake: {error[:500]}
Fix: {next_hint}
Signal: {signal}

## Relevant Experiences
"""
    if relevant_experiences:
        for item in relevant_experiences:
            reflection_content += f"- {item}\n"
    else:
        reflection_content += "- None found\n"

    reflection_content += f"""

## Next Action
{next_hint}
"""

    safe_write_text_locked(reflection_path, reflection_content)
    register_artifact(
        workdir,
        ArtifactType.CUSTOM,
        str(reflection_path),
        current_phase,
        "system",
        metadata={
            "kind": "reflection",
            "error_type": error_type,
            "confidence": confidence,
            "strategy": strategy,
            "relevant_experiences": relevant_experiences,
        },
    )

    try:
        record_reflection_experience(
            task=task_desc,
            trigger=trigger,
            mistake=error[:500],
            fix=next_hint,
            signal=signal,
            filepath=memory_path,
            index_file=memory_index_path,
            confidence=max(0.3, min(0.9, confidence if confidence else 0.7)),
            scope="project",
            tags=[error_type, current_phase.lower()],
        )
    except Exception:
        pass

    return {
        "reflection_path": str(reflection_path),
        "relevant_experiences": relevant_experiences,
    }


def _build_debug_summary(
    *,
    strategy: str,
    error: str,
    error_type: str,
    confidence: float,
    retry_count: int,
    activation_level: int,
    retry_hint: str,
    quality_gate_details: dict[str, Any] | None,
    reflection_artifact: dict[str, Any] | None,
    escalation_reason: str | None,
) -> dict[str, Any]:
    """Build a structured debug summary for state and sidecar persistence."""
    root_cause = retry_hint or error[:240]
    if quality_gate_details and quality_gate_details.get("failed_checks"):
        failed_checks = [str(item) for item in quality_gate_details.get("failed_checks", [])[:3] if str(item).strip()]
        if failed_checks:
            root_cause = " | ".join(failed_checks)

    regression_check = "rerun affected tests and quality gate"
    if quality_gate_details and quality_gate_details.get("gate_file"):
        regression_check = f"rerun {quality_gate_details['gate_file']}"

    minimal_fix = retry_hint or "inspect the failure and retry with tighter scope"
    if error_type in {"syntax_error", "type_error"} and not retry_hint:
        minimal_fix = "fix the syntax or typing issue, then rerun validation"
    elif error_type == "quality_gate_failed" and not retry_hint:
        minimal_fix = "address the failing gate checks, then rerun validation"

    return {
        "debug_found": True,
        "debug_source": strategy,
        "strategy": strategy,
        "error_type": error_type,
        "retry_count": retry_count,
        "activation_level": activation_level,
        "escalation_reason": escalation_reason,
        "root_cause": root_cause,
        "minimal_fix": minimal_fix,
        "regression_check": regression_check,
        "reflection_path": reflection_artifact.get("reflection_path") if reflection_artifact else None,
        "quality_gate_failed": bool(quality_gate_details),
        "confidence": confidence,
    }
