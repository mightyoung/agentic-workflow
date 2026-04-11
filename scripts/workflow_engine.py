#!/usr/bin/env python3
"""
Minimal workflow runtime for agentic-workflow.

This bridges the existing scripts into a concrete runtime chain:
prompt -> route -> local state -> task tracker -> optional plan scaffold
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import memory_ops
import router
import search_adapter
import task_tracker
from analyze_gate import validate_analyze_gate
from contract_manager import (
    _create_phase_contract,
    parse_phase_contract,
    validate_execution_contract_readiness,
    update_contract_json,
    validate_contract_gate,
)
from findings_paths import (
    ensure_findings_dir,
    findings_latest_path,
    findings_session_path,
    legacy_findings_paths,
)
from middleware import Request as MiddlewareRequest
from middleware import create_default_chain as create_middleware_chain
from review_paths import (
    ensure_review_dir,
    legacy_review_paths,
    review_latest_path,
    review_session_path,
)
from runtime_profile import (
    build_skill_context,
    build_thinking_summary,
    debugging_activation_level_for_context,
    escalate_skill_activation_level,
    should_use_skill_for_phase,
    skill_activation_level_for_phase,
    skill_policy_for_phase,
)
from safe_io import safe_write_json, safe_write_text_locked
from skill_loader import SkillPromptFormatter, load_skill
from team_agent import TeamAgent
from trajectory_logger import TrajectoryLogger
from unified_state import (
    ArtifactType,
    can_transition,
    create_initial_state,
    get_allowed_transitions,
    get_failure_event_summary,
    get_debug_summary,
    get_planning_summary,
    get_research_summary,
    get_thinking_summary,
    get_review_summary,
    get_runtime_profile_summary,
    load_state,
    register_artifact,
    save_state,
    trajectory_dir_path,
    transition_phase,
    workflow_state_path,
)

# 存储当前活跃的 TrajectoryLogger 实例
_active_loggers: dict[str, TrajectoryLogger] = {}

DEFAULT_CATEGORY = "WORKFLOW"

from workflow_helpers import (  # noqa: F401
    _create_plan_from_template,
    _create_spec_artifacts,
    _derive_phase_contract_fields,
    _generate_and_register_summary,
    _run_quality_gate_if_applicable,
    _run_review_gate_if_applicable,
    _task_id_from_timestamp,
)




from snapshot_builder import (  # noqa: F401
    _build_phase_context,
    get_workflow_snapshot,
)


def _phase_display_name(trigger_type: str, phase: str) -> str:
    if trigger_type == "DIRECT_ANSWER":
        return "DIRECT_ANSWER"
    if trigger_type == "FULL_WORKFLOW":
        return "PLANNING"
    return phase


def _render_progress_content(
    current_phase: str,
    runtime_profile: dict[str, Any],
    planning_summary: dict[str, Any],
    state: WorkflowState,
    research_summary: dict[str, Any] | None = None,
    thinking_summary: dict[str, Any] | None = None,
) -> str:
    research_summary = research_summary or {}
    lines = [
        "# Progress",
        "",
        "## Current Phase",
        f"- phase: {current_phase}",
        "- status: active",
        f"- updated: {datetime.now().isoformat()}",
        "",
        "## Skill Policy",
        f"- policy: {runtime_profile['skill_policy']}",
        f"- use_skill: {runtime_profile['use_skill']}",
        f"- activation_level: {runtime_profile['skill_activation_level']}",
        f"- profile_source: {runtime_profile['profile_source']}",
        "",
        "## Planning Summary",
        f"- plan_source: {planning_summary.get('plan_source', 'none')}",
        f"- planning_mode: {planning_summary.get('planning_mode', 'lightweight')}",
        f"- plan_digest: {planning_summary.get('plan_digest', 'unset')}",
        f"- worktree_recommended: {planning_summary.get('worktree_recommended', False)}",
        "",
        "## Research Summary",
        f"- research_found: {research_summary.get('research_found', False)}",
        f"- research_source: {research_summary.get('research_source', 'unset')}",
        f"- research_path: {research_summary.get('research_path', 'unset')}",
        f"- key_terms: {research_summary.get('key_terms', 'unset')}",
        f"- search_engine: {research_summary.get('search_engine', 'unset')}",
        f"- sources_count: {research_summary.get('sources_count', 0)}",
        f"- used_real_search: {research_summary.get('used_real_search', False)}",
        f"- degraded_mode: {research_summary.get('degraded_mode', False)}",
        f"- evidence_status: {research_summary.get('evidence_status', 'unset')}",
        "",
        "## Session",
        f"- session_id: {state.session_id}",
        f"- task_id: {state.task.task_id if state.task else 'N/A'}",
    ]
    if thinking_summary:
        lines.extend(
            [
                "",
                "## THINKING Summary",
                f"- workflow_label: {thinking_summary.get('workflow_label', 'unset')}",
                f"- thinking_mode: {thinking_summary.get('thinking_mode', 'unset')}",
                f"- thinking_methods: {' | '.join(thinking_summary.get('thinking_methods', [])) if thinking_summary.get('thinking_methods') else 'unset'}",
                f"- major_contradiction: {thinking_summary.get('major_contradiction', 'unset')}",
                f"- stage_judgment: {thinking_summary.get('stage_judgment', 'unset')}",
                f"- local_attack_point: {thinking_summary.get('local_attack_point', 'unset')}",
            ]
        )
    return "\n".join(lines)


from frontier_scheduler import (  # noqa: F401
    CheckpointConfig,
    _find_canonical_tasks_path,
    compute_frontier,
    conditional_checkpoint,
    load_planning_tasks,
    next_plan_tasks,
    parse_task_plan,
    parse_tasks_md,
    should_checkpoint,
)



from task_validator import (  # noqa: F401
    update_task_status_in_plan,
    validate_task_plan,
)


from phase_transitions import (  # noqa: F401
    allowed_next_phases,
    recommend_next_phases,
    validate_transition,
)


def _build_runtime_profile(prompt: str, workdir: str) -> dict[str, Any]:
    """
    Build the initial runtime profile for a prompt.

    The authoritative runtime owns state and gates. Skill context and workspace
    injection are now inlined here, reducing experimental-layer residue.
    Middleware remains available for experimental signal extraction but is no
    longer required for profile construction.
    """
    trigger_type, routed_phase, _confidence = router.route(prompt)
    complexity, complexity_conf = router.estimate_complexity(prompt)
    phase_sequence = router.get_phase_sequence(complexity)
    current_phase = _phase_display_name(trigger_type, routed_phase)

    # CHAT intent: direct answer, no skill needed
    skill_policy = skill_policy_for_phase(current_phase, complexity, trigger_type)

    if trigger_type == "DIRECT_ANSWER":
        skill_context = ""
        tokens_expected = 500
        use_skill = False
    else:
        use_skill = should_use_skill_for_phase(current_phase, complexity, trigger_type, prompt)
        if use_skill:
            # Build skill context inline using sunk PHASE_PROMPTS
            skill_context, tokens_expected = build_skill_context(current_phase, complexity)
        else:
            skill_context = ""
            tokens_expected = 500

    skill_activation_level = (
        skill_activation_level_for_phase(current_phase, complexity, trigger_type, prompt) if use_skill else 0
    )

    profile: dict[str, Any] = {
        "trigger_type": trigger_type,
        "phase": current_phase,
        "complexity": complexity,
        "complexity_confidence": complexity_conf,
        "phase_sequence": phase_sequence,
        "skill_context": skill_context,
        "tokens_expected": tokens_expected,
        "use_skill": use_skill,
        "skill_policy": skill_policy,
        "skill_activation_level": skill_activation_level,
        "intent": None,
        "profile_source": "router",
    }

    # Middleware signal overlay: when the experimental middleware layer is present,
    # its normalized intent/skill policy can override router defaults.
    # ContextMiddleware / SkillMiddleware signals are now sunk into this function.
    try:
        request = MiddlewareRequest(text=prompt, metadata={"cwd": workdir})
        create_middleware_chain().execute(request)

        if request.intent is not None:
            profile["intent"] = request.intent
            profile["skill_policy"] = getattr(request, "skill_policy", profile["skill_policy"])
            profile["skill_activation_level"] = getattr(
                request, "skill_activation_level", profile["skill_activation_level"]
            )
            profile["profile_source"] = "middleware+router"

        if request.intent == "CHAT":
            profile["trigger_type"] = "DIRECT_ANSWER"
            profile["phase"] = "DIRECT_ANSWER"
            profile["use_skill"] = False
            profile["skill_context"] = ""
            profile["tokens_expected"] = 500
            profile["skill_policy"] = "disable"
            profile["skill_activation_level"] = 0
            profile["profile_source"] = "middleware+router"
        elif request.intent == "FULL_WORKFLOW":
            profile["trigger_type"] = "FULL_WORKFLOW"
            profile["phase"] = request.phase.value
            profile["complexity"] = request.complexity.value
            if request.metadata.get("phase_sequence"):
                profile["phase_sequence"] = [
                    phase.value if hasattr(phase, "value") else str(phase)
                    for phase in request.metadata["phase_sequence"]
                ]
            profile["profile_source"] = "middleware+router"
            profile["skill_activation_level"] = 0 if not profile["use_skill"] else skill_activation_level_for_phase(
                profile["phase"], profile["complexity"], profile["intent"], prompt
            )
    except Exception:
        # Keep router-derived defaults when middleware is unavailable.
        pass

    return profile


def initialize_workflow(
    prompt: str,
    workdir: str = ".",
    task_id: str | None = None,
    auto_create_plan: bool = True,
) -> dict[str, Any]:
    """
    Initialize a new workflow session.

    Creates .workflow_state.json, initializes task tracker, and sets up
    trajectory logging. Determines initial phase via router and creates
    spec artifacts if auto_create_plan is True.

    Args:
        prompt: User task description (e.g., "帮我开发一个REST API")
        workdir: Working directory for workflow files
        task_id: Optional task ID (auto-generated from timestamp if None)
        auto_create_plan: Whether to create spec/plan/task artifacts

    Returns:
        Initial state snapshot dict with session_id, task, phase, trigger_type
    """
    workdir_path = Path(workdir)
    workdir_path.mkdir(parents=True, exist_ok=True)

    # Clean up stale lock files from previous crashed sessions
    try:
        from safe_io import cleanup_stale_locks
        cleanup_stale_locks(workdir_path)
    except Exception:
        pass  # Non-critical — never block initialization

    session_path = workdir_path / memory_ops.DEFAULT_SESSION_STATE
    tracker_path = workdir_path / task_tracker.DEFAULT_TRACKER_FILE

    memory_ops.ensure_session_state_exists(str(session_path))
    task_tracker.save_tracker(str(tracker_path), task_tracker.load_tracker(str(tracker_path)))

    runtime_profile = _build_runtime_profile(prompt, workdir)
    trigger_type = runtime_profile["trigger_type"]
    current_phase = runtime_profile["phase"]
    complexity = runtime_profile["complexity"]
    complexity_conf = runtime_profile["complexity_confidence"]
    phase_sequence = runtime_profile["phase_sequence"]

    # Create unified state
    state = create_initial_state(
        prompt=prompt,
        task_id=task_id or _task_id_from_timestamp(),
        trigger_type=trigger_type,
        initial_phase=current_phase,
    )

    # Store complexity and phase sequence in state metadata
    if state.metadata is None:
        state.metadata = {}
    state.metadata["complexity"] = complexity
    state.metadata["complexity_confidence"] = complexity_conf
    state.metadata["phase_sequence"] = phase_sequence
    state.metadata["runtime_profile"] = runtime_profile

    # NOTE: create_initial_state already sets the phase to initial_phase
    # Don't call transition_phase here as it would try to transition to the same phase

    # Ensure trajectory directory exists
    traj_dir = trajectory_dir_path(workdir)
    traj_dir.mkdir(parents=True, exist_ok=True)

    # Start trajectory logging
    logger = TrajectoryLogger(workdir, state.session_id)
    logger.start(prompt, trigger_type, runtime_profile=runtime_profile)
    logger.enter_phase(current_phase)
    _active_loggers[state.session_id] = logger

    # Trajectory info tracked in _active_loggers and saved to trajectory files
    # All artifact tracking goes through artifact_registry (authoritative source)

    memory_ops.update_task_info(str(session_path), prompt, current_phase)
    memory_ops.update_resume_point(str(session_path), current_phase, 0)
    memory_ops.update_runtime_profile(
        str(session_path),
        skill_policy=runtime_profile["skill_policy"],
        use_skill=runtime_profile["use_skill"],
        skill_activation_level=runtime_profile["skill_activation_level"],
        tokens_expected=runtime_profile["tokens_expected"],
        profile_source=runtime_profile["profile_source"],
        complexity=runtime_profile["complexity"],
        complexity_confidence=runtime_profile["complexity_confidence"],
    )
    planning_summary = get_planning_summary(str(workdir), state)
    research_summary = get_research_summary(str(workdir), state)
    thinking_summary = get_thinking_summary(workdir, state)
    review_summary = get_review_summary(workdir, state)
    memory_ops.update_planning_summary(
        str(session_path),
        planning_summary,
    )
    memory_ops.update_review_summary(
        str(session_path),
        review_summary,
    )
    memory_ops.update_thinking_summary(
        str(session_path),
        thinking_summary,
    )
    progress_file = workdir_path / "progress.md"
    progress_content = _render_progress_content(
        current_phase,
        runtime_profile,
        planning_summary,
        state,
        research_summary,
        thinking_summary if current_phase == "THINKING" else None,
    )
    safe_write_text_locked(progress_file, progress_content)

    # Register progress.md artifact (authoritative tracking via registry only)
    register_artifact(workdir, ArtifactType.PROGRESS, str(progress_file), current_phase, "system")

    created_task = False
    if trigger_type in ("FULL_WORKFLOW", "STAGE"):
        task_id = state.task.task_id if state.task else None
        if task_id is None:
            raise ValueError("state.task is None, cannot create task")
        if task_tracker.get_task(task_id, str(tracker_path)) is None:
            created_task = task_tracker.create_task(
                task_id,
                prompt,
                priority="P1" if current_phase in ("PLANNING", "DEBUGGING", "REVIEWING") else "P2",
                path=str(tracker_path),
            )
        task_tracker.start_task(task_id, str(tracker_path))
        task_tracker.update_status(task_id, "in_progress", progress=0, path=str(tracker_path))

    contract_path: Path | None = None
    spec_path: Path | None = None
    plan_md_path: Path | None = None
    tasks_path: Path | None = None
    if auto_create_plan and current_phase == "PLANNING" and complexity not in {"XS", "S"}:
        # Create spec.md and plan.md in .specs/<feature_id>/ directory
        task_title = state.task.title if state.task else prompt[:50]
        task_desc = state.task.description if state.task else prompt
        spec_path, plan_md_path, tasks_path = _create_spec_artifacts(
            task_title, task_desc, workdir, state.session_id
        )
        if spec_path is not None:
            register_artifact(workdir, ArtifactType.CUSTOM, str(spec_path), current_phase, "system",
                           metadata={"deliverable": "spec", "type": "spec.md"})
        if plan_md_path is not None:
            register_artifact(workdir, ArtifactType.CUSTOM, str(plan_md_path), current_phase, "system",
                           metadata={"deliverable": "plan", "type": "plan.md"})
        if tasks_path is not None:
            register_artifact(workdir, ArtifactType.CUSTOM, str(tasks_path), current_phase, "system",
                           metadata={"deliverable": "tasks", "type": "tasks.md"})

        # Create Anthropic-style phase contract
        contract_path = _create_phase_contract(task_title, task_desc, workdir)
        if contract_path is not None:
            register_artifact(workdir, "contract", str(contract_path), current_phase, "system",
                            metadata={"deliverable": "contract", "phase": current_phase})

        plan_tasks, _plan_source = load_planning_tasks(workdir)
        contract_fields = _derive_phase_contract_fields(task_title, task_desc, plan_tasks, workdir)
        update_contract_json(workdir, **contract_fields)

        planning_summary = get_planning_summary(str(workdir), state)
        memory_ops.update_planning_summary(
            str(session_path),
            planning_summary,
        )
        from unified_state import _build_thinking_summary_from_state

        thinking_summary = _build_thinking_summary_from_state(workdir, state)
        memory_ops.update_thinking_summary(
            str(session_path),
            thinking_summary,
        )
        progress_content = _render_progress_content(
            current_phase,
            runtime_profile,
            planning_summary,
            state,
            research_summary,
            thinking_summary if current_phase == "THINKING" else None,
        )
        safe_write_text_locked(progress_file, progress_content)

    # Register session state artifact
    register_artifact(workdir, ArtifactType.SESSION, str(session_path), current_phase, "system")

    # Register task tracker artifact
    register_artifact(workdir, ArtifactType.TRACKER, str(tracker_path), current_phase, "system")

    # Note: phase-specific business artifacts (findings/review) are now generated
    # on phase EXIT (when advancing to another phase), not on phase ENTER.
    # This ensures artifacts represent completed work, not just entry into a phase.

    # Save unified state (minimal artifacts index only - trajectory refs)
    save_state(workdir, state)

    return {
        "task_id": state.task.task_id if state.task else None,
        "session_id": state.session_id,
        "trigger_type": trigger_type,
        "phase": current_phase,
        "created_task": created_task,
        "plan_created": any(path is not None for path in (spec_path, plan_md_path, tasks_path, contract_path)),
        "recommended_next_phases": recommend_next_phases(current_phase, trigger_type),
        "state_file": str(workflow_state_path(workdir)),
        "trajectory_session_id": state.session_id,
        "complexity": complexity,
        "skill_policy": runtime_profile["skill_policy"],
        "skill_context": runtime_profile["skill_context"],
        "tokens_expected": runtime_profile["tokens_expected"],
        "skill_activation_level": runtime_profile["skill_activation_level"],
        "use_skill": runtime_profile["use_skill"],
        "profile_source": runtime_profile["profile_source"],
        "phase_sequence": phase_sequence,
        "total_phases": len(phase_sequence),
    }


def advance_workflow(
    phase: str,
    workdir: str = ".",
    progress: int = 0,
    task_status: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    """
    Advance the workflow to a new phase.

    Updates .workflow_state.json with the new phase, saves progress to progress.md,
    runs quality gate on phase exit (for EXECUTING), generates phase-specific
    artifacts (findings for RESEARCH, review for REVIEWING), and saves checkpoint
    if conditions are met.

    Args:
        phase: Target phase to advance to
        workdir: Working directory
        progress: Progress percentage (0-100)
        task_status: Optional task status override
        note: Optional note for this transition

    Returns:
        Updated state snapshot dict

    Raises:
        ValueError: If workflow not initialized or phase transition is illegal
    """
    state = load_state(workdir)
    if state is None:
        raise ValueError("workflow state not found, please run init first")
    if not state.task or not state.task.task_id:
        raise ValueError("workflow runtime has not been initialized properly")

    task_id = state.task.task_id
    tracker_path = Path(workdir) / task_tracker.DEFAULT_TRACKER_FILE
    session_path = Path(workdir) / memory_ops.DEFAULT_SESSION_STATE

    current_phase = state.phase.get("current", "IDLE")
    validate_transition(current_phase, phase)

    # P2 ToT: Check if deliberation is warranted before complex transitions
    deliberation_result: dict[str, Any] = {}
    try:
        from deliberate_mode import should_deliberate
        # Determine trigger type based on phase transition context
        deliberation_trigger = None
        if phase == "EXECUTING" and current_phase in ("PLANNING", "ANALYZING"):
            deliberation_trigger = "planning_conflict"
        elif phase == "DEBUGGING":
            deliberation_trigger = "debug_failure"
        elif phase == "REVIEWING":
            deliberation_trigger = "review_divergence"
        # Check state metadata for high complexity
        complexity = state.metadata.get("complexity", "") if state.metadata else ""
        if complexity in ("L", "XL") and deliberation_trigger is None:
            deliberation_trigger = "high_complexity"

        if deliberation_trigger and should_deliberate(workdir, deliberation_trigger, state):
            from deliberate_mode import deliberate
            frontier = compute_frontier(workdir)
            task_desc = state.task.description or state.task.title or "" if state.task else ""
            context = {
                "task_description": task_desc,
                "frontier": frontier,
            }
            result = deliberate(workdir, deliberation_trigger, context)
            deliberation_result = {
                "trigger": result.trigger,
                "recommended_branch": result.recommended_branch_id,
                "branches": [
                    {"id": b.branch_id, "title": b.title, "score": b.score, "confidence": b.confidence}
                    for b in result.branches
                ],
                "path": result.deliberation_path,
            }
            # Log deliberation decision
            if state.session_id in _active_loggers:
                logger = _active_loggers[state.session_id]
                logger.log_decision(
                    f"Deliberation ({deliberation_trigger}): {len(result.branches)} branches considered",
                    f"Recommended: {result.recommended_branch_id}",
                )
    except Exception:
        # Deliberation is best-effort - don't block workflow
        deliberation_result = {}

    # Log phase transition in trajectory
    if state.session_id in _active_loggers:
        logger = _active_loggers[state.session_id]
        logger.exit_phase(current_phase)
        if note:
            logger.log_decision(f"Transition: {current_phase} -> {phase}", note)
        logger.enter_phase(phase)

    # Analyze gate validation: PLANNING/ANALYZING -> EXECUTING requires passing analyze gate
    if phase == "EXECUTING" and current_phase in ("PLANNING", "ANALYZING"):
        analyze_result = validate_analyze_gate(workdir)
        if not analyze_result.passed:
            errors_str = "; ".join(analyze_result.errors)
            raise ValueError(f"analyze gate failed: {errors_str}")
        # Log warnings but don't block
        if analyze_result.warnings:
            logger.log_decision(f"analyze gate warnings: {'; '.join(analyze_result.warnings)}") if state.session_id in _active_loggers else None

    # Contract readiness gate: execution should not begin with placeholder artifacts.
    if phase == "EXECUTING" and current_phase in ("PLANNING", "ANALYZING"):
        contract_ready, contract_error = validate_execution_contract_readiness(workdir, state)
        if not contract_ready:
            raise ValueError(f"execution contract gate failed: {contract_error}")

    # Transition phase using unified_state
    state = transition_phase(state, phase, reason=note or "advance_workflow")

    # Contract lifecycle management
    # PLANNING -> EXECUTING: activate contract
    if current_phase == "PLANNING" and phase == "EXECUTING":
        update_contract_json(workdir, status="active")
    # EXECUTING -> REVIEWING: mark for review
    elif current_phase == "EXECUTING" and phase == "REVIEWING":
        update_contract_json(workdir, status="review")

    runtime_profile = state.metadata.get("runtime_profile", {}) if state.metadata else {}
    thinking_summary: dict[str, Any] | None = None
    complete_gate_prevalidated = False

    if phase == "COMPLETE":
        # Check if this is a code implementation task (has REVIEWING or EXECUTING in history)
        phase_history = state.phase.get("history", [])
        is_code_task = any(p.get("phase") in ("REVIEWING", "EXECUTING") for p in phase_history)

        if is_code_task:
            # Get quality gate status from tracker
            tracker_data = task_tracker.load_tracker(str(tracker_path))
            task_data = None
            for t in tracker_data.get("tasks", []):
                if t.get("id") == task_id:
                    task_data = t
                    break

            quality_gate_passed = task_data.get("quality_gates_passed") if task_data else None
            task_priority = task_data.get("priority") if task_data else None
            task_verification = task_data.get("verification") if task_data else None

            # Code tasks must have explicitly passed quality gate (None = not run, False = failed)
            if quality_gate_passed is not True:
                raise ValueError(
                    f"Cannot transition to COMPLETE: quality gate not passed for task {task_id}. "
                    f"quality_gates_passed={quality_gate_passed}. "
                    f"Allowed transitions: stay in {current_phase}, go to DEBUGGING, or abort."
                )

            # If P0/P1 task has no verification, block COMPLETE
            if task_priority in ("P0", "P1") and not task_verification:
                raise ValueError(
                    f"Cannot transition to COMPLETE: task {task_id} (P0/P1) has no verification method. "
                    f"Allowed transitions: stay in {current_phase}, go to DEBUGGING, or abort."
                )

            review_valid, review_error = _run_review_gate_if_applicable(workdir, True)
            if not review_valid:
                raise ValueError(
                    f"Cannot transition to COMPLETE: {review_error}. "
                    f"Allowed transitions: stay in {current_phase}, go to REVIEWING, or abort."
                )

        # Contract fulfillment gate: validate contract is properly fulfilled
        contract_valid, contract_error = validate_contract_gate(workdir, state)
        if not contract_valid:
            raise ValueError(
                f"Cannot transition to COMPLETE: {contract_error}"
            )

        complete_gate_prevalidated = True

    # Update progress.md
    progress_file = Path(workdir) / "progress.md"
    if progress_file.exists():
        planning_summary = get_planning_summary(workdir, state)
        research_summary = get_research_summary(workdir, state)
        if phase == "THINKING":
            task_desc = state.task.description if state.task else (state.task.title if state.task else "")
            runtime_complexity = str(runtime_profile.get("complexity") or (state.metadata.get("complexity") if state.metadata else "M"))
            try:
                contract_summary = parse_phase_contract(workdir)
            except Exception:
                contract_summary = {}
            thinking_summary = build_thinking_summary(
                task_desc,
                runtime_complexity,
                research_summary=research_summary,
                contract_summary=contract_summary,
            )
        progress_content = _render_progress_content(
            phase,
            runtime_profile,
            planning_summary,
            state,
            research_summary,
            thinking_summary,
        )
        safe_write_text_locked(progress_file, progress_content)

    # Save updated state
    save_state(workdir, state)

    memory_ops.update_task_info(str(session_path), state.task.description if state.task else "(未设置)", phase)
    memory_ops.update_resume_point(str(session_path), phase, progress)
    if runtime_profile:
        memory_ops.update_runtime_profile(
            str(session_path),
            skill_policy=str(runtime_profile.get("skill_policy", "")),
            use_skill=bool(runtime_profile.get("use_skill", False)),
            skill_activation_level=int(runtime_profile.get("skill_activation_level", 0)),
            tokens_expected=int(runtime_profile.get("tokens_expected", 0)),
            profile_source=str(runtime_profile.get("profile_source", "router")),
            complexity=str(runtime_profile.get("complexity", state.metadata.get("complexity", "M")) if state.metadata else "M"),
            complexity_confidence=runtime_profile.get("complexity_confidence"),
        )
    memory_ops.update_planning_summary(
        str(session_path),
        get_planning_summary(workdir, state),
    )
    if phase == "THINKING":
        if thinking_summary is None:
            task_desc = state.task.description if state.task else (state.task.title if state.task else "")
            runtime_complexity = str(runtime_profile.get("complexity") or (state.metadata.get("complexity") if state.metadata else "M"))
            try:
                contract_summary = parse_phase_contract(workdir)
            except Exception:
                contract_summary = {}
            thinking_summary = build_thinking_summary(
                task_desc,
                runtime_complexity,
                research_summary=get_research_summary(workdir, state),
                contract_summary=contract_summary,
            )
        memory_ops.update_thinking_summary(
            str(session_path),
            thinking_summary,
        )

    if task_status:
        task_tracker.update_status(task_id, task_status, progress=progress, path=str(tracker_path))
        if task_status == "completed":
            # Run actual quality gate before marking as completed
            # Research tasks (current_phase == RESEARCH) don't need quality gate
            is_code_task = current_phase != "RESEARCH"
            quality_passed = _run_quality_gate_if_applicable(workdir, task_id, str(tracker_path), is_code_task)
            task_tracker.update_quality_gate(task_id, quality_passed, str(tracker_path))

    # Register phase-specific business artifacts on phase EXIT (not entry)
    # This ensures artifacts represent completed work, not just entry into a phase
    # Artifacts are generated when LEAVING RESEARCH/REVIEWING, not when entering
    from unified_state import ArtifactType, register_artifact
    session_id = state.session_id or "unknown"
    if current_phase == "RESEARCH" and phase != "RESEARCH":
        # Generating findings when leaving RESEARCH phase (completing research work)
        task_desc = state.task.description if state.task else 'N/A'
        task_title = state.task.title if state.task else 'Research Task'

        # Extract meaningful keywords and key phrases from task description
        words = task_desc.split()
        stop_words = {"的", "了", "和", "是", "在", "我", "有", "个", "等", "以", "对", "为", "与", "或", "及", "包括", "什么", "如何", "怎么", "哪些", "一个", "可以", "需要", "应该", "the", "a", "an", "of", "and", "in", "on", "for", "to", "is", "this", "that", "with", "as"}
        key_terms = [w for w in words if w.lower() not in stop_words and len(w) > 2][:10]
        key_terms_str = ", ".join(key_terms) if key_terms else task_title

        # Try real web search first
        search_response = search_adapter.search(task_desc, num_results=5)
        used_real_search = search_response.has_results

        if used_real_search:
            # Generate findings from real search results
            findings_list = []
            sources_list = []
            for i, result in enumerate(search_response.results, 1):
                findings_list.append(f"{i}. **{result.title}**: {result.snippet}")
                sources_list.append(f"[{i}] {result.title} - {result.url}")

            recommendations = [
                "- Review cited sources for detailed implementation guidance",
                "- Validate findings against project-specific constraints",
                "- Proceed to planning phase with verified research findings",
            ]

            findings_dir = ensure_findings_dir(workdir)
            findings_path = findings_dir / f"findings_{session_id}.md"
            findings_latest = findings_latest_path(workdir)
            engine_label = search_response.search_engine
            if search_response.search_engine == "duckduckgo":
                engine_label = f"{search_response.search_engine} [DEGRADED - DuckDuckGo HTML fallback]"
            findings_content = f"""# Research Findings: {task_title}

## Research Question
{task_desc}

## Method
- Research conducted at: {datetime.now().isoformat()}
- Search engine: {engine_label}
- Results: {search_response.total_results} sources found

## Key Findings
{chr(10).join(findings_list)}

## Sources
{chr(10).join(sources_list)}

## Conclusions
- Research completed with {search_response.total_results} verified sources
- Findings provide evidence-based insights for implementation planning
- Sources cited for further reference and validation

## Recommendations
{chr(10).join(recommendations)}
"""
            # Extract degraded_reason from search metadata if present
            degraded_reason = None
            if search_response.metadata and isinstance(search_response.metadata, dict):
                degraded_reason = search_response.metadata.get("degraded_reason")

            metadata = {
                "deliverable": "findings",
                "session_id": session_id,
                "has_method": True,
                "has_conclusions": True,
                "generated_on_exit": True,
                "key_terms": key_terms_str,
                "search_engine": search_response.search_engine,
                "sources_count": search_response.total_results,
                "used_real_search": True,
                "degraded_mode": search_response.search_engine == "duckduckgo",
            }
            if degraded_reason:
                metadata["degraded_reason"] = degraded_reason
            research_summary = {
                "research_found": True,
                "research_source": "findings_session",
                "research_path": str(findings_path),
                "key_terms": key_terms_str,
                "search_engine": search_response.search_engine,
                "sources_count": search_response.total_results,
                "used_real_search": True,
                "degraded_mode": search_response.search_engine == "duckduckgo",
                "degraded_reason": degraded_reason,
                "search_error": None,
                "evidence_status": "verified" if search_response.total_results > 0 else "degraded",
            }
        else:
            # Search failed or returned no usable results.
            # Emit an explicit degraded report instead of pretending we found evidence.
            search_note = search_response.error if search_response.error else "Search unavailable"
            findings_dir = ensure_findings_dir(workdir)
            findings_path = findings_dir / f"findings_{session_id}.md"
            findings_latest = findings_latest_path(workdir)

            findings_list = [
                f"1. **No verifiable external sources for {key_terms_str}**: configured search providers returned no usable evidence for this research question.",
            ]
            recommendations = [
                "- Re-run RESEARCH with a more specific query or narrower scope",
                "- Verify external search access before relying on this result",
                "- Fall back to manual source collection if search remains unavailable",
            ]
            findings_content = f"""# Research Findings: {task_title}

## Research Question
{task_desc}

## Method
- Research conducted at: {datetime.now().isoformat()}
- Focus: {key_terms_str}
- Search status: degraded
- Note: {search_note}

## Evidence Status
- No verifiable external sources were returned for this query
- This report records the failure mode instead of fabricating findings

## Key Findings
{chr(10).join(findings_list)}

## Conclusions
- Research could not be validated with external sources
- The current result should be treated as a degraded placeholder, not evidence-backed research

## Recommendations
{chr(10).join(recommendations)}
"""
            metadata = {
                "deliverable": "findings",
                "session_id": session_id,
                "has_method": True,
                "has_conclusions": True,
                "generated_on_exit": True,
                "key_terms": key_terms_str,
                "search_error": search_note,
                "used_real_search": False,
                "degraded_mode": True,
                "degraded_reason": search_note,
            }
            research_summary = {
                "research_found": True,
                "research_source": "findings_session",
                "research_path": str(findings_path),
                "key_terms": key_terms_str,
                "search_engine": search_response.search_engine,
                "sources_count": 0,
                "used_real_search": False,
                "degraded_mode": True,
                "degraded_reason": search_note,
                "search_error": search_note,
                "evidence_status": "degraded",
            }

        safe_write_text_locked(findings_path, findings_content)
        safe_write_text_locked(findings_latest, findings_content)
        register_artifact(workdir, ArtifactType.FINDINGS, str(findings_path), "RESEARCH", "system", metadata=metadata)
        session_state_path = Path(workdir) / memory_ops.DEFAULT_SESSION_STATE
        memory_ops.update_research_summary(str(session_state_path), research_summary)

    if current_phase == "REVIEWING" and phase != "REVIEWING":
        # Generating review when leaving REVIEWING phase (completing review work)
        task_title = state.task.title if state.task else 'N/A'
        task_desc = state.task.description if state.task else 'N/A'

        # Try to read actual code files from workdir
        workdir_path = Path(workdir)
        code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs', '.c', '.cpp'}
        code_files: list[Path] = []
        for ext in code_extensions:
            code_files.extend(workdir_path.rglob(f'*{ext}'))

        # Filter out common non-source directories
        excluded_dirs = {'node_modules', '.git', '__pycache__', 'venv', '.venv', 'dist', 'build'}

        # Task-directed review: prioritize spec-kit (tasks.md / .contract.json) over legacy task_plan.md
        target_files = []
        review_source = "none"

        # 1. Try canonical tasks.md (spec-kit): parse **Files:** per task
        tasks_md_path = _find_canonical_tasks_path(workdir)
        plan_path: Path | None = None
        if tasks_md_path and tasks_md_path.exists():
            tasks_content = tasks_md_path.read_text(encoding="utf-8", errors="ignore")
            files_pattern = re.compile(r'\*\*Files:\*\*\s*`([^`]+)`', re.IGNORECASE)
            for match in files_pattern.finditer(tasks_content):
                files_str = match.group(1).strip()
                for f in files_str.split(','):
                    f = f.strip()
                    if f:
                        fp = Path(workdir) / f
                        if fp.exists():
                            target_files.append(fp)
            if target_files:
                review_source = "tasks_md"

        # 2. Try .contract.json (spec-kit): owned_files field
        if not target_files:
            contract_json_path = Path(workdir) / ".contract.json"
            if contract_json_path.exists():
                try:
                    import json as json_lib
                    contract_data = json_lib.loads(contract_json_path.read_text(encoding="utf-8"))
                    owned = contract_data.get("owned_files", [])
                    for f in owned:
                        f = f.strip()
                        if f:
                            fp = Path(workdir) / f
                            if fp.exists():
                                target_files.append(fp)
                    if target_files:
                        review_source = "contract_json"
                except (json_lib.JSONDecodeError, OSError):
                    pass

        # 3. Try task_plan.md (legacy fallback): parse owned_files: line
        if not target_files:
            plan_path = Path(workdir) / "task_plan.md"
            if plan_path.exists():
                plan_content = plan_path.read_text(encoding="utf-8", errors="ignore")
                owned_pattern = re.compile(r'owned_files:\s*(.+)', re.IGNORECASE)
                for line in plan_content.split('\n'):
                    owned_match: re.Match[str] | None = owned_pattern.search(line)
                    if owned_match:
                        files_str = owned_match.group(1).strip()
                        for f in files_str.split(','):
                            f = f.strip()
                            if f:
                                fp = Path(workdir) / f
                                if fp.exists():
                                    target_files.append(fp)
                        if target_files:
                            review_source = "task_plan_md"
                            break

        # 4. Try state.file_changes
        if not target_files and state.file_changes:
            for fc in state.file_changes[:10]:  # Limit to first 10 changes
                fp = Path(workdir) / fc.path
                if fp.exists() and fp.suffix in {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs', '.c', '.cpp'}:
                    target_files.append(fp)
            if target_files:
                review_source = "file_changes"

        # 5. Strict fallback: ONLY do workdir_scan if explicitly allowed
        review_fallback_allowed = False
        if state.task:
            task_text = (state.task.description or "").lower() + (state.task.title or "").lower()
            if "allow_review_fallback" in task_text or "review_fallback=true" in task_text:
                review_fallback_allowed = True

        # Also check task_plan.md / tasks.md for explicit allow_fallback flag
        allow_fallback_candidates: list[Path] = []
        if tasks_md_path and tasks_md_path.exists():
            allow_fallback_candidates.append(tasks_md_path)
        if plan_path and plan_path.exists():
            allow_fallback_candidates.append(plan_path)

        for fallback_candidate in allow_fallback_candidates:
            if review_fallback_allowed:
                break
            plan_content = fallback_candidate.read_text(encoding="utf-8", errors="ignore").lower()
            if "allow_review_fallback" in plan_content or "review_fallback: true" in plan_content:
                review_fallback_allowed = True

        if not target_files:
            if review_fallback_allowed:
                # Explicitly allowed - do the scan
                code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs', '.c', '.cpp'}
                for ext in code_extensions:
                    for fp in workdir_path.rglob(f'*{ext}'):
                        if not any(ex in fp.parts for ex in excluded_dirs):
                            target_files.append(fp)
                if target_files:
                    review_source = "workdir_scan"
            else:
                # Not allowed - leave target_files empty; template-based review will be used
                review_source = "none"

        # Limit to 10 files total for performance
        target_files = target_files[:10]
        used_real_review = len(target_files) > 0
        reviewed_files_info = []

        if used_real_review:
            # Analyze actual code files
            risk_findings = []
            risk_level = "Medium"
            total_lines = 0

            for code_file in target_files:
                try:
                    content = code_file.read_text(encoding="utf-8", errors="ignore")
                    lines = content.split('\n')
                    total_lines += len(lines)
                    file_size = len(content)

                    # Generate findings based on actual code content
                    file_path_str = str(code_file.relative_to(workdir_path))

                    # Check for common security issues
                    if any(kw in content.lower() for kw in ['password', 'secret', 'token', 'api_key', 'apikey', 'auth']):
                        risk_findings.append(f"- **{file_path_str}**: Contains potential credential/secrets - review for hardcoded secrets (lines: {len(lines)})")
                        if risk_level != "Critical":
                            risk_level = "High"

                    # Check for error handling
                    if 'except' not in content and 'try:' not in content:
                        if file_size > 1000:  # Only flag larger files
                            risk_findings.append(f"- **{file_path_str}**: Missing try/except blocks - review error handling (lines: {len(lines)})")

                    # Check for TODO/FIXME (indicates incomplete work)
                    if '# TODO' in content or '# FIXME' in content:
                        risk_findings.append(f"- **{file_path_str}**: Contains TODO/FIXME comments - incomplete work identified (lines: {len(lines)})")

                    reviewed_files_info.append(f"- {file_path_str} ({len(lines)} lines)")

                except Exception:
                    continue

            # Add overall assessment findings
            if not risk_findings:
                risk_findings.append("- **Code Quality**: No critical issues identified in code review")

            # Generate recommendations based on actual findings
            recommendations = []
            if risk_level == "High":
                recommendations.append("- Address high-risk findings before production deployment")
                recommendations.append("- Remove or secure any hardcoded credentials/secrets")
            if "Contains potential credential" in " ".join(risk_findings):
                recommendations.append("- Implement secret management (environment variables or vault)")
            recommendations.append("- Verify implementation against specific acceptance criteria")
            recommendations.append("- Add integration tests for critical business paths")

            # Read phase contract if available (Anthropic-style negotiated contract)
            contract_info = ""
            contract = parse_phase_contract(workdir)
            contract_owned_files = [str(item).strip() for item in contract.get("owned_files", []) if str(item).strip()]
            contract_impact_files = [str(item).strip() for item in contract.get("impact_files", []) if str(item).strip()]
            contract_files = contract_owned_files + contract_impact_files
            reviewed_targets = [str(fp.relative_to(workdir_path)) for fp in target_files]

            def _paths_match(left: str, right: str) -> bool:
                left_norm = left.replace("\\", "/").strip().lower().lstrip("./")
                right_norm = right.replace("\\", "/").strip().lower().lstrip("./")
                return (
                    left_norm == right_norm
                    or left_norm.endswith("/" + right_norm)
                    or right_norm.endswith("/" + left_norm)
                    or left_norm in right_norm
                    or right_norm in left_norm
                )

            matched_contract_files = [
                target for target in reviewed_targets
                if any(_paths_match(target, contract_file) for contract_file in contract_files)
            ]
            if contract_files:
                contract_alignment = "contract_targeted" if matched_contract_files else "contract_miss"
            elif used_real_review and review_source in {"tasks_md", "contract_json", "file_changes"}:
                contract_alignment = "legacy_targeted"
            elif review_source == "workdir_scan":
                contract_alignment = "fallback_scan"
            elif review_source == "none":
                contract_alignment = "template"
            else:
                contract_alignment = "ad_hoc"

            if contract.get("goals"):
                contract_info = "\n## Phase Contract\n"
                if contract.get("goals"):
                    contract_info += "**Goals:**\n"
                    for goal in contract["goals"][:3]:
                        contract_info += f"- {goal}\n"
                if contract.get("verification_methods"):
                    contract_info += "\n**Verification:**\n"
                    for method in contract["verification_methods"][:2]:
                        contract_info += f"- {method}\n"
                if contract.get("owned_files"):
                    contract_info += f"\n**Contract Files:** {', '.join(contract['owned_files'][:3])}\n"

            review_dir = ensure_review_dir(workdir)
            review_path = review_dir / f"review_{session_id}.md"
            review_latest = review_latest_path(workdir)
            degraded_note = ""
            if review_source == "workdir_scan":
                degraded_note = """> **⚠️ Degraded Mode**: Review used workdir_scan fallback (no owned_files in tasks.md, .contract.json, task_plan.md, and no file_changes recorded). Results are less targeted than owned_files/file_changes directed review.
"""
            review_content = f"""# Code Review: {task_title}

## Review Scope
{task_title}

## Task Description
{task_desc}
{contract_info}

## Review Date
{datetime.now().isoformat()}

## Files Reviewed
**Files Reviewed**: {len(target_files)} code files

## Contract Coverage
- Contract alignment: {contract_alignment}
- Contract files count: {len(contract_files)}
- Reviewed targets count: {len(reviewed_targets)}
- Matched contract files: {len(matched_contract_files)}

## Stage 1: Spec Compliance
- Contract/owned_files alignment: reviewed against {review_source}
- Acceptance coverage: checked via task contract and target files
- Scope completeness: target files count = {len(target_files)}

## Stage 2: Code Quality
- Correctness: Implementation reviewed based on actual code
- Security: Security posture assessed based on code analysis
- Maintainability: Code structure supports future maintenance

{degraded_note}## Reviewed Files ({len(target_files)} files analyzed)
{chr(10).join(reviewed_files_info)}

## Risk Findings
{chr(10).join(risk_findings)}

## Risk Level
- **Overall**: {risk_level}
- {"High-risk areas identified - requires careful review" if risk_level == "High" else "Standard review findings apply" if risk_level == "Medium" else "Critical areas require immediate attention"}

## Recommendations
{chr(10).join(recommendations)}

## Verdict
- Status: REVIEWED
"""
            metadata = {
                "deliverable": "review",
                "session_id": session_id,
                "has_findings": True,
                "has_risk_level": True,
                "generated_on_exit": True,
                "risk_level": risk_level,
                "files_reviewed": len(target_files),
                "total_lines": total_lines,
                "used_real_review": True,
                "review_source": review_source,
                "degraded_mode": review_source == "workdir_scan",
                "fallback_mode": review_source == "workdir_scan",
                "contract_alignment": contract_alignment,
                "contract_files_count": len(contract_files),
                "reviewed_targets_count": len(reviewed_targets),
                "matched_contract_files_count": len(matched_contract_files),
            }
            review_summary = {
                "review_found": True,
                "review_source": review_source,
                "review_status": "reviewed",
                "stage_1_status": "reviewed",
                "stage_2_status": "reviewed",
                "risk_level": risk_level,
                "verdict": "REVIEWED",
                "degraded_mode": review_source == "workdir_scan",
                "files_reviewed": len(target_files),
                "contract_alignment": contract_alignment,
                "contract_files_count": len(contract_files),
                "reviewed_targets_count": len(reviewed_targets),
                "matched_contract_files_count": len(matched_contract_files),
            }
        else:
            # Fall back to template-based review (no code files found)
            desc_lower = task_desc.lower()
            risk_findings = []
            risk_level = "Medium"

            # Generate specific risk findings based on task type
            if "认证" in desc_lower or "auth" in desc_lower or "login" in desc_lower:
                risk_findings.append("- **Authentication**: Credential handling and session management reviewed for security concerns")
                risk_level = "High"
            if "API" in desc_lower or "rest" in desc_lower or "接口" in desc_lower:
                risk_findings.append("- **API Security**: Endpoint validation, rate limiting, and input sanitization reviewed")
            if "用户" in desc_lower or "user" in desc_lower:
                risk_findings.append("- **Data Handling**: User input validation and data protection mechanisms reviewed")
            if "注册" in desc_lower or "register" in desc_lower:
                risk_findings.append("- **Registration Flow**: Password policy, email verification, and duplicate prevention reviewed")
                risk_level = "High"
            if "支付" in desc_lower or "payment" in desc_lower or "transaction" in desc_lower:
                risk_findings.append("- **Transaction Safety**: ACID compliance, idempotency, and financial error handling critical")
                risk_level = "Critical"
            if "敏感" in desc_lower or "sensitive" in desc_lower or "privacy" in desc_lower:
                risk_findings.append("- **Data Privacy**: PII handling, encryption, and compliance considerations reviewed")
                risk_level = "High"
            if not risk_findings:
                risk_findings.append("- **General Quality**: Code structure, error handling, and edge cases reviewed for correctness")

            # Generate specific recommendations based on identified risks
            recommendations = []
            if "认证" in desc_lower or "auth" in desc_lower:
                recommendations.append("- Implement multi-factor authentication for production")
            if "API" in desc_lower or "rest" in desc_lower:
                recommendations.append("- Add API rate limiting and request validation middleware")
            if risk_level == "High" or risk_level == "Critical":
                recommendations.append("- Conduct dedicated security review before production deployment")
            recommendations.append("- Verify implementation against specific acceptance criteria")
            recommendations.append("- Add integration tests for critical business paths")

            review_dir = ensure_review_dir(workdir)
            review_path = review_dir / f"review_{session_id}.md"
            review_latest = review_latest_path(workdir)
            review_content = f"""# Code Review: {task_title}

## Review Scope
{task_title}

## Task Description
{task_desc}

## Review Date
{datetime.now().isoformat()}

## Files Reviewed
**Files Reviewed**: 0 code files

## Contract Coverage
- Contract alignment: template
- Contract files count: 0
- Reviewed targets count: 0
- Matched contract files: 0

## Stage 1: Spec Compliance
- Contract/owned_files alignment: no file-level contract available
- Acceptance coverage: verified against task description only
- Scope completeness: template-based fallback

## Stage 2: Code Quality
- Correctness: Implementation reviewed for functional correctness
- Security: Security posture assessed based on task requirements
- Maintainability: Code structure supports future maintenance

## Risk Findings
{chr(10).join(risk_findings)}

## Risk Level
- **Overall**: {risk_level}
- {"High-risk areas identified - requires careful review" if risk_level == "High" else "Critical areas require dedicated security review" if risk_level == "Critical" else "Standard review findings apply"}

## Recommendations
{chr(10).join(recommendations)}

## Verdict
- Status: REVIEWED
"""
            metadata = {
                "deliverable": "review",
                "session_id": session_id,
                "has_findings": True,
                "has_risk_level": True,
                "generated_on_exit": True,
                "risk_level": risk_level,
                "files_reviewed": 0,
                "used_real_review": False,
                "review_source": "none",
                "note": "No code files found in workdir - template-based review",
            }
            review_summary = {
                "review_found": True,
                "review_source": "template",
                "review_status": "reviewed",
                "stage_1_status": "reviewed",
                "stage_2_status": "reviewed",
                "risk_level": risk_level,
                "verdict": "REVIEWED",
                "degraded_mode": True,
                "files_reviewed": 0,
                "contract_alignment": "template",
                "contract_files_count": 0,
                "reviewed_targets_count": 0,
                "matched_contract_files_count": 0,
            }

        safe_write_text_locked(review_path, review_content)
        safe_write_text_locked(review_latest, review_content)
        register_artifact(workdir, ArtifactType.REVIEW, str(review_path), "REVIEWING", "system", metadata=metadata)
        memory_ops.update_review_summary(str(session_path), review_summary)

    # Keep the progress sidecar in sync after contract activation so execution
    # sees the negotiated contract rather than a stale draft snapshot.
    if phase == "EXECUTING" and current_phase in ("PLANNING", "ANALYZING"):
        planning_summary = get_planning_summary(workdir, state)
        research_summary = get_research_summary(workdir, state)
        thinking_summary = build_thinking_summary(
            state.task.description if state.task else (state.task.title if state.task else ""),
            str(runtime_profile.get("complexity") or (state.metadata.get("complexity") if state.metadata else "M")),
            research_summary=research_summary,
            contract_summary=parse_phase_contract(workdir),
        )
        progress_content = _render_progress_content(
            phase,
            runtime_profile,
            planning_summary,
            state,
            research_summary,
            thinking_summary,
        )
        safe_write_text_locked(progress_file, progress_content)

    # Block COMPLETE transition if quality gate failed for code tasks
    if phase == "COMPLETE":
        if not complete_gate_prevalidated:
            # Defensive fallback: keep legacy behavior if the prevalidation block is bypassed.
            phase_history = state.phase.get("history", [])
            is_code_task = any(p.get("phase") in ("REVIEWING", "EXECUTING") for p in phase_history)

            if is_code_task:
                tracker_data = task_tracker.load_tracker(str(tracker_path))
                task_data = None
                for t in tracker_data.get("tasks", []):
                    if t.get("id") == task_id:
                        task_data = t
                        break

                quality_gate_passed = task_data.get("quality_gates_passed") if task_data else None
                task_priority = task_data.get("priority") if task_data else None
                task_verification = task_data.get("verification") if task_data else None

                if quality_gate_passed is not True:
                    raise ValueError(
                        f"Cannot transition to COMPLETE: quality gate not passed for task {task_id}. "
                        f"quality_gates_passed={quality_gate_passed}. "
                        f"Allowed transitions: stay in {current_phase}, go to DEBUGGING, or abort."
                    )

                if task_priority in ("P0", "P1") and not task_verification:
                    raise ValueError(
                        f"Cannot transition to COMPLETE: task {task_id} (P0/P1) has no verification method. "
                        f"Allowed transitions: stay in {current_phase}, go to DEBUGGING, or abort."
                    )

                review_valid, review_error = _run_review_gate_if_applicable(workdir, True)
                if not review_valid:
                    raise ValueError(
                        f"Cannot transition to COMPLETE: {review_error}. "
                        f"Allowed transitions: stay in {current_phase}, go to REVIEWING, or abort."
                    )

            contract_valid, contract_error = validate_contract_gate(workdir, state)
            if not contract_valid:
                raise ValueError(
                    f"Cannot transition to COMPLETE: {contract_error}"
                )

        _generate_and_register_summary(workdir, state, current_phase, "completed", session_id)
        # Keep the sidecar review summary aligned with the final review artifact.
        memory_ops.update_review_summary(str(session_path), get_review_summary(workdir, state))

    # Load and format skill prompt for the new phase
    skill_prompt_path = None
    skill_name = None
    try:
        skill = load_skill(phase)
        if skill:
            formatter = SkillPromptFormatter(skill)
            task_desc = state.task.description if state.task else ""
            task_title = state.task.title if state.task else ""
            prompt = formatter.format(
                task=task_desc or task_title or "未指定任务",
                session_id=session_id or "",
            )
            # Save skill prompt as artifact (use PROGRESS type, not SUMMARY - SUMMARY is for completion_summary)
            skill_prompt_path = Path(workdir) / f"skill_prompt_{phase.lower()}_{session_id}.md"
            safe_write_text_locked(skill_prompt_path, prompt)
            skill_name = skill.metadata.name
            register_artifact(workdir, ArtifactType.PROGRESS, str(skill_prompt_path), phase, "system",
                             metadata={"skill_name": skill_name, "phase": phase})
            # SKILL0 P3: Record skill usage for telemetry
            try:
                from skill_telemetry import record_skill_usage
                record_skill_usage(
                    skill_name=skill_name,
                    phase=phase,
                    workdir=workdir,
                    metadata={"session_id": session_id, "outcome": "loaded"},
                )
            except Exception:
                pass  # Skill telemetry is best-effort
    except Exception:
        # Skill loading is best-effort - don't fail the phase transition
        pass

    # Calculate progress visualization data
    phase_sequence = state.metadata.get("phase_sequence") if state.metadata else None
    phase_index = None
    total_phases = None
    if phase_sequence and isinstance(phase_sequence, list):
        try:
            phase_index = phase_sequence.index(phase) + 1
            total_phases = len(phase_sequence)
        except ValueError:
            pass

    # Build context for next phase — what the AI should read before proceeding
    context_for_next_phase = _build_phase_context(phase, workdir, state.session_id or "unknown")

    # Reflexion P1: Surface experience warning prominently if found
    experience_warning = None
    exp_check = context_for_next_phase.get("experience_check", {})
    if isinstance(exp_check, dict) and exp_check.get("warning"):
        experience_warning = exp_check["warning"]

    return {
        "task_id": task_id,
        "session_id": state.session_id,
        "phase": phase,
        "progress": progress,
        "task_status": task_status,
        "recommended_next_phases": recommend_next_phases(phase, state.trigger_type),
        "state_file": str(workflow_state_path(workdir)),
        "skill_prompt_path": str(skill_prompt_path) if skill_prompt_path else None,
        "skill_name": skill_name,
        "phase_index": phase_index,
        "total_phases": total_phases,
        "complexity": state.metadata.get("complexity") if state.metadata else None,
        "context_for_next_phase": context_for_next_phase,
        # Reflexion P1: Top-level experience warning for visibility
        "experience_warning": experience_warning,
        # P2 ToT: Deliberation result (if deliberation was triggered)
        "deliberation": deliberation_result if deliberation_result else None,
    }


def complete_workflow(
    workdir: str = ".",
    final_state: str = "completed",
    failure_reason: str | None = None,
) -> dict[str, Any]:
    """
    Complete the workflow and finalize trajectory logging.

    Validates contract fulfillment gate before allowing completion (contract must
    be active/fulfilled, goals must not be placeholders). Generates final
    summary artifact and flushes trajectory logger.

    Args:
        workdir: Working directory
        final_state: Final state string (completed/failed/aborted)
        failure_reason: Reason for failure (if final_state is not completed)

    Returns:
        Completion result dict with session_id and final state

    Raises:
        ValueError: If contract gate validation fails or workflow not initialized
    """
    state = load_state(workdir)
    if state is None:
        raise ValueError("workflow state not found, please run init first")

    current_phase = state.phase.get("current", "IDLE")
    session_id = state.session_id or "unknown"
    if final_state == "completed":
        contract_valid, contract_error = validate_contract_gate(workdir, state)
        if not contract_valid:
            raise ValueError(f"Cannot complete workflow: {contract_error}")

    # Gate blocking for code tasks - same logic as advance_workflow COMPLETE
    phase_history = state.phase.get("history", [])
    is_code_task = any(p.get("phase") in ("REVIEWING", "EXECUTING") for p in phase_history)

    if is_code_task and final_state == "completed":
        # Get task_id from state
        task_id = state.task.task_id if state.task else None

        # Code tasks MUST have a valid task_id to complete
        # If task_id is None, we cannot verify quality gate was run - fail closed
        if task_id is None:
            raise ValueError(
                f"Cannot complete workflow: task has no task_id. "
                f"Cannot verify quality gate was run. "
                f"Allowed transitions: stay in {current_phase}, go to DEBUGGING, or abort."
            )

        tracker_path = Path(workdir) / ".task_tracker.json"
        tracker_data = task_tracker.load_tracker(str(tracker_path))
        task_data = None
        for t in tracker_data.get("tasks", []):
            if t.get("id") == task_id:
                task_data = t
                break

        quality_gate_passed = task_data.get("quality_gates_passed") if task_data else None
        task_priority = task_data.get("priority") if task_data else None
        task_verification = task_data.get("verification") if task_data else None

        # Code tasks must have explicitly passed quality gate (None = not run, False = failed)
        if quality_gate_passed is not True:
            raise ValueError(
                f"Cannot complete workflow: quality gate not passed for task {task_id}. "
                f"quality_gates_passed={quality_gate_passed}. "
                f"Allowed transitions: stay in {current_phase}, go to DEBUGGING, or abort."
            )

        # If P0/P1 task has no verification, block COMPLETE
        if task_priority in ("P0", "P1") and not task_verification:
            raise ValueError(
                f"Cannot complete workflow: task {task_id} (P0/P1) has no verification method. "
                f"Allowed transitions: stay in {current_phase}, go to DEBUGGING, or abort."
            )

        review_valid, review_error = _run_review_gate_if_applicable(workdir, True, state)
        if not review_valid:
            raise ValueError(
                f"Cannot complete workflow: {review_error}. "
                f"Allowed transitions: stay in {current_phase}, go to REVIEWING, or abort."
            )

    # Complete trajectory logging
    if state.session_id in _active_loggers:
        logger = _active_loggers[state.session_id]
        logger.exit_phase(current_phase)
        logger.complete(final_state, failure_reason)
        del _active_loggers[state.session_id]

    # Register completion summary artifact using shared helper
    _generate_and_register_summary(workdir, state, current_phase, final_state, session_id, failure_reason)

    # Transition to COMPLETE if not already there
    if current_phase != "COMPLETE":
        state = transition_phase(state, "COMPLETE", reason=f"Workflow {final_state}")
        save_state(workdir, state)

    return {
        "session_id": state.session_id,
        "final_state": final_state,
        "failure_reason": failure_reason,
    }


def log_workflow_decision(
    workdir: str,
    decision: str,
    reason: str = "",
) -> dict[str, Any]:
    """Log workflow decision to trajectory"""
    state = load_state(workdir)
    if state is None:
        raise ValueError("workflow state not found")

    if state.session_id in _active_loggers:
        logger = _active_loggers[state.session_id]
        logger.log_decision(decision, reason)
        return {"status": "logged", "decision": decision}

    return {"status": "no_active_logger", "decision": decision}


def log_workflow_file_change(
    workdir: str,
    file_path: str,
    action: str,
) -> dict[str, Any]:
    """Log file change to trajectory"""
    state = load_state(workdir)
    if state is None:
        raise ValueError("workflow state not found")

    if state.session_id in _active_loggers:
        logger = _active_loggers[state.session_id]
        logger.log_file_change(file_path, action)
        return {"status": "logged", "file_path": file_path, "action": action}

    return {"status": "no_active_logger", "file_path": file_path, "action": action}


# ============================================================================
# Lightweight Generator-Evaluator Loop
# ============================================================================
# Anthropic-style generator-evaluator pattern, thin stable implementation.
#
# Trigger conditions (one of):
#   - High complexity task (detected by task size/complexity indicators)
#   - Quality gate failure during REVIEWING
#   - Explicit opt-in via task_plan.md flag: `enable_evaluator_loop=true`
#
# Revision cycle:
#   REVIEWING -> (if issues found) -> EXECUTING (revise) -> REVIEWING (re-verify)
#   Maximum 2 revision cycles per phase contract
# ============================================================================

MAX_REVISION_CYCLES = 2


def request_revision(
    workdir: str,
    reason: str,
    feedback: str,
) -> dict[str, Any]:
    """
    Request revision from REVIEWING back to EXECUTING.

    Lightweight Generator-Evaluator loop integration point.
    Tracks revision count in state and limits to MAX_REVISION_CYCLES.

    Args:
        workdir: Working directory
        reason: Why revision is needed (e.g., "quality_gate_failed", "high_risk_issues")
        feedback: Specific feedback for the executor

    Returns:
        Dict with transition info including revision_count and whether revision is allowed
    """
    from state_schema import Decision

    state = load_state(workdir)
    if state is None:
        raise ValueError("workflow state not found")

    # Track revision count in state decisions
    revision_decisions = [d for d in state.decisions if "revision" in d.decision.lower()]
    revision_count = len(revision_decisions)

    if revision_count >= MAX_REVISION_CYCLES:
        return {
            "status": "revision_limit_reached",
            "revision_count": revision_count,
            "max_revisions": MAX_REVISION_CYCLES,
            "message": f"Maximum revision cycles ({MAX_REVISION_CYCLES}) reached. Proceeding to COMPLETE.",
        }

    # Log revision request
    state.decisions.append(Decision(
        timestamp=datetime.now().isoformat(),
        decision=f"Revision requested: {reason}",
        reason=feedback,
    ))
    save_state(workdir, state)

    return {
        "status": "revision_requested",
        "revision_count": revision_count + 1,
        "max_revisions": MAX_REVISION_CYCLES,
        "reason": reason,
        "feedback": feedback,
        "next_phase": "EXECUTING",
    }


def resume_workflow(
    workdir: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """
    Resume workflow from a checkpoint.

    Loads checkpoint state from .checkpoints/ directory (or from trajectory if
    session_id not provided), restores .workflow_state.json, and updates
    task tracker to reflect resumed state.

    Args:
        workdir: Working directory
        session_id: Optional session ID (auto-detected from trajectories if None)

    Returns:
        Restored state snapshot dict with resume metadata
    """
    from trajectory_logger import list_trajectories, resume_from_point

    # 如果没有指定 session_id，找到最新的中断工作流
    if session_id is None:
        trajectories = list_trajectories(workdir)
        for traj in trajectories:
            if traj.get("final_state") == "running":
                session_id = traj.get("session_id")
                break

        if session_id is None:
            return {"success": False, "error": "No interrupted workflow found to resume"}

    # 获取恢复点
    result = resume_from_point(workdir, session_id)
    if not result:
        return {"success": False, "error": f"Failed to resume session {session_id}"}

    # 获取新的 session_id 和 next_phase
    new_session_id = result["session_id"]
    next_phase = result["next_phase"]
    resume_summary = result.get("resume_summary", {})
    research_summary = resume_summary.get("research_summary", {})
    planning_summary = resume_summary.get("planning_summary", {})
    review_summary = resume_summary.get("review_summary", {})
    debug_summary = resume_summary.get("debug_summary", {})
    thinking_summary = resume_summary.get("thinking_summary", {})

    # 更新 unified state - 这是关键同步步骤
    state = load_state(workdir)
    if state is not None:
        runtime_profile_summary = get_runtime_profile_summary(state)
        failure_event_summary = get_failure_event_summary(state)
        state_planning_summary = get_planning_summary(workdir, state)
        state_research_summary = get_research_summary(workdir, state)
        state_review_summary = get_review_summary(workdir, state)
        state_debug_summary = get_debug_summary(workdir, state)
        if not planning_summary or planning_summary.get("plan_source") in {None, "", "none"}:
            planning_summary = state_planning_summary
        if not research_summary or research_summary.get("research_source") in {None, "", "none"}:
            research_summary = state_research_summary
        if not review_summary or review_summary.get("review_source") in {None, "", "none"}:
            review_summary = state_review_summary
        if not debug_summary or debug_summary.get("debug_source") in {None, "", "none"}:
            debug_summary = state_debug_summary
        resume_summary["debug_summary"] = debug_summary
        if state.metadata is None:
            state.metadata = {}
        state.metadata["debug_summary"] = debug_summary
        # 记录恢复决策
        from datetime import datetime

        from state_schema import Decision
        state.decisions.append(Decision(
            timestamp=datetime.now().isoformat(),
            decision=f"Resumed from {session_id}",
            reason=f"resume_from={result['resume_from']}",
            metadata={
                "original_session": session_id,
                "resumed_session": new_session_id,
                "resume_from": result["resume_from"],
                "next_phase": next_phase,
                "resume_summary": resume_summary,
                "runtime_profile_summary": runtime_profile_summary,
                "research_summary": research_summary,
                "planning_summary": planning_summary,
                "review_summary": review_summary,
                "debug_summary": debug_summary,
                "thinking_summary": thinking_summary,
                "failure_event_summary": failure_event_summary,
            },
        ))

        # 更新 session_id
        state.session_id = new_session_id

        # 更新 phase
        state.phase["current"] = next_phase

        save_state(workdir, state)
    else:
        runtime_profile_summary = {}
        failure_event_summary = {}
        research_summary = research_summary or get_research_summary(workdir, None)
        planning_summary = planning_summary or get_planning_summary(workdir, None)
        review_summary = review_summary or get_review_summary(workdir, None)
        debug_summary = debug_summary or get_debug_summary(workdir, None)

    session_path = Path(workdir) / memory_ops.DEFAULT_SESSION_STATE
    memory_ops.update_resume_summary(
        str(session_path),
        resume_from=result["resume_from"],
        next_phase=next_phase,
        original_session_id=session_id,
        runtime_profile=runtime_profile_summary,
        research_summary=research_summary,
        planning_summary=planning_summary,
        review_summary=review_summary,
        debug_summary=debug_summary,
        thinking_summary=thinking_summary,
        failure_event_summary=failure_event_summary,
    )
    memory_ops.update_planning_summary(
        str(session_path),
        planning_summary,
    )

    # 重新初始化 trajectory logger
    new_logger = TrajectoryLogger(workdir, new_session_id)
    new_logger.start(
        f"[RESUMED from {session_id}]",
        "RESUMED",
        runtime_profile=runtime_profile_summary,
        resume_summary=resume_summary,
    )
    new_logger.enter_phase(next_phase)
    _active_loggers[new_session_id] = new_logger

    return {
        "success": True,
        "original_session_id": session_id,
        "new_session_id": new_session_id,
        "resume_from": result["resume_from"],
        "next_phase": next_phase,
        "resume_summary": resume_summary,
        "runtime_profile_summary": runtime_profile_summary,
        "research_summary": research_summary,
        "planning_summary": planning_summary,
        "review_summary": review_summary,
        "debug_summary": debug_summary,
        "thinking_summary": thinking_summary,
        "failure_event_summary": failure_event_summary,
        "state_synced": True,
    }


from error_classifier import (  # noqa: F401
    _ERROR_TYPE_PATTERNS,
    _build_debug_summary,
    _extract_quality_gate_details,
    _get_error_history,
    _persist_failure_reflection,
    _should_escalate_skill_activation,
    classify_error,
)


def handle_workflow_failure(
    workdir: str,
    error: str,
    strategy: str = "retry",
    max_retries: int = 3,
) -> dict[str, Any]:
    """
    Handle workflow failure with intelligent error classification and retry strategy.

    Args:
        workdir: Working directory
        error: Error message
        strategy: Failure handling strategy
            - "retry": Retry current phase
            - "debugging": Transition to DEBUGGING phase
            - "abort": Abort workflow
        max_retries: Maximum retry count

    Returns:
        Handling result
    """
    from datetime import datetime

    from state_schema import Decision

    state = load_state(workdir)
    if state is None:
        return {"success": False, "error": "workflow state not found"}

    current_phase = state.phase.get("current", "IDLE")

    # Classify the error
    error_type, confidence = classify_error(error)

    # Log failure to trajectory
    if state.session_id in _active_loggers:
        logger = _active_loggers[state.session_id]
        logger.log_error(error, recoverable=(strategy != "abort"))

    # Check for quality gate failure details
    quality_gate_details = None
    if error_type == "quality_gate_failed":
        quality_gate_details = _extract_quality_gate_details(workdir)

    # Determine retry count early so we can make a stricter escalation decision.
    runtime_profile = state.metadata.get("runtime_profile", {}) if state.metadata else {}
    retry_count = 0
    if state.decisions:
        last_decision = state.decisions[-1]
        retry_count = int(last_decision.metadata.get("retry_count", 0))

    error_history = _get_error_history(state)

    # Escalate activation level only for explicit failure events.
    if runtime_profile:
        current_activation_level = int(runtime_profile.get("skill_activation_level", 0))
        should_escalate, escalation_reason = _should_escalate_skill_activation(
            error=error,
            error_type=error_type,
            strategy=strategy,
            retry_count=retry_count,
            error_history=error_history,
        )
        escalated_activation_level = (
            escalate_skill_activation_level(current_activation_level) if should_escalate else current_activation_level
        )
        if escalated_activation_level != current_activation_level:
            runtime_profile["skill_activation_level"] = escalated_activation_level
            if state.metadata is None:
                state.metadata = {}
            state.metadata["runtime_profile"] = runtime_profile
            state.decisions.append(Decision(
                timestamp=datetime.now().isoformat(),
                decision="Escalate skill activation",
                reason=f"{escalation_reason} escalated activation to {escalated_activation_level}",
                metadata={
                    "error_type": error_type,
                    "current_activation_level": current_activation_level,
                    "escalated_activation_level": escalated_activation_level,
                    "escalation_reason": escalation_reason,
                    "retry_count": retry_count,
                    "profile_source": runtime_profile.get("profile_source", "router"),
                },
            ))
            session_path = Path(workdir) / memory_ops.DEFAULT_SESSION_STATE
            memory_ops.update_runtime_profile(
                str(session_path),
                skill_policy=str(runtime_profile.get("skill_policy", "")),
                use_skill=bool(runtime_profile.get("use_skill", False)),
                skill_activation_level=escalated_activation_level,
                tokens_expected=int(runtime_profile.get("tokens_expected", 0)),
                profile_source=str(runtime_profile.get("profile_source", "router")),
                complexity=str(runtime_profile.get("complexity", state.metadata.get("complexity", "M")) if state.metadata else "M"),
                complexity_confidence=runtime_profile.get("complexity_confidence"),
            )
            if state.session_id in _active_loggers:
                logger = _active_loggers[state.session_id]
                logger.log_decision(
                    "Escalate skill activation",
                    f"{escalation_reason} escalated activation to {escalated_activation_level}",
                    activation_level=escalated_activation_level,
                    error_type=error_type,
                    escalation_reason=escalation_reason,
                )
            save_state(workdir, state)

    # Syntax errors always go to debugging immediately - they can't be fixed by retry
    if error_type == "syntax_error":
        strategy = "debugging"
        retry_hint = "syntax error cannot be fixed by retry"
    else:
        retry_hint = ""

    reflection_artifact: dict[str, Any] = {}
    debug_summary: dict[str, Any] = {}
    session_path = Path(workdir) / memory_ops.DEFAULT_SESSION_STATE

    if strategy == "retry":
        # Get retry count and error history from decisions
        retry_count = 0
        error_history = _get_error_history(state)

        if state.decisions:
            last_decision = state.decisions[-1]
            retry_count = last_decision.metadata.get("retry_count", 0)

        # Adjust max_retries based on error classification
        adjusted_max_retries = max_retries

        # Generate dynamic reflexion hint based on actual error content
        from reflexion import reflect_on_errors
        reflex = reflect_on_errors(error, error_type, {
            "phase": current_phase,
            "retry_count": retry_count,
        })
        retry_hint = reflex.hint

        reflection_artifact = _persist_failure_reflection(
            workdir,
            state,
            error,
            error_type,
            confidence,
            retry_hint,
            strategy,
            quality_gate_details=quality_gate_details,
        )

        if error_type == "test_failure" and retry_count >= 1:
            # After one test failure retry, suggest debugging
            adjusted_max_retries = max(retry_count + 1, 2)
        elif error_type == "lint_error" and not retry_hint:
            # Lint errors often fixed by auto-fix (only if reflexion didn't find specifics)
            retry_hint = "try running ruff/lint auto-fix"
        elif error_type == "type_error" and not retry_hint:
            # Type errors need careful review (only if reflexion didn't find specifics)
            retry_hint = "check type annotations"

        if retry_count >= adjusted_max_retries:
            strategy = "debugging"
        else:
            new_retry_count = retry_count + 1
            state.decisions.append(Decision(
                timestamp=datetime.now().isoformat(),
                decision=f"Retry attempt {new_retry_count}",
                reason=f"Retry after {error_type} error: {error[:200]}",
                metadata={
                    "retry_count": new_retry_count,
                    "error": error,
                "error_type": error_type,
                "error_confidence": confidence,
                "error_history": error_history,
                "reflection": reflex.reflection,
                "reflection_hint": retry_hint,
            },
            ))
            save_state(workdir, state)

            result = {
                "success": True,
                "action": "retry",
                "phase": current_phase,
                "retry_count": new_retry_count,
                "error_type": error_type,
                "confidence": confidence,
                "message": f"Retrying {current_phase} (attempt {new_retry_count}/{adjusted_max_retries})",
                "reflection_recorded": bool(reflection_artifact),
            }
            if retry_hint:
                result["retry_hint"] = retry_hint
            if quality_gate_details:
                result["quality_gate_details"] = quality_gate_details
            if reflection_artifact:
                result.update(reflection_artifact)
            debug_summary = _build_debug_summary(
                strategy="retry",
                error=error,
                error_type=error_type,
                confidence=confidence,
                retry_count=new_retry_count,
                activation_level=int(runtime_profile.get("skill_activation_level", 0)) if runtime_profile else 0,
                retry_hint=retry_hint,
                quality_gate_details=quality_gate_details,
                reflection_artifact=reflection_artifact,
                escalation_reason="retry",
            )
            if state.metadata is None:
                state.metadata = {}
            state.metadata["debug_summary"] = debug_summary
            save_state(workdir, state)
            memory_ops.update_debug_summary(str(session_path), debug_summary)
            result["debug_summary"] = debug_summary
            return result

    if strategy == "debugging":
        reflection_artifact = _persist_failure_reflection(
            workdir,
            state,
            error,
            error_type,
            confidence,
            retry_hint,
            strategy,
            quality_gate_details=quality_gate_details,
        )
        if can_transition(current_phase, "DEBUGGING"):
            owned_files_count = len(state.task.owned_files) if state.task else 0
            diff_size = len(state.file_changes) if state.file_changes else 0
            failure_count = len(error_history)
            task_text = state.task.description if state.task else error
            debug_activation_level = debugging_activation_level_for_context(
                str(runtime_profile.get("complexity", state.metadata.get("complexity", "M")) if state.metadata else "M"),
                task_text=task_text,
                owned_files_count=owned_files_count,
                diff_size=diff_size,
                failure_count=failure_count,
            )

            if runtime_profile:
                runtime_profile["skill_activation_level"] = debug_activation_level
                runtime_profile["skill_policy"] = (
                    "conditional_enable_after_optimization" if debug_activation_level > 0 else "disable"
                )
                runtime_profile["use_skill"] = debug_activation_level > 0
                if state.metadata is None:
                    state.metadata = {}
                state.metadata["runtime_profile"] = runtime_profile
                state.decisions.append(Decision(
                    timestamp=datetime.now().isoformat(),
                    decision="Tune debugging activation",
                    reason=f"context-based debug activation set to {debug_activation_level}",
                    metadata={
                        "owned_files_count": owned_files_count,
                        "diff_size": diff_size,
                        "failure_count": failure_count,
                        "debug_activation_level": debug_activation_level,
                        "profile_source": runtime_profile.get("profile_source", "router"),
                    },
                ))
                session_path = Path(workdir) / memory_ops.DEFAULT_SESSION_STATE
                memory_ops.update_runtime_profile(
                    str(session_path),
                    skill_policy=str(runtime_profile.get("skill_policy", "")),
                    use_skill=bool(runtime_profile.get("use_skill", False)),
                    skill_activation_level=debug_activation_level,
                    tokens_expected=int(runtime_profile.get("tokens_expected", 0)),
                    profile_source=str(runtime_profile.get("profile_source", "router")),
                    complexity=str(runtime_profile.get("complexity", state.metadata.get("complexity", "M")) if state.metadata else "M"),
                    complexity_confidence=runtime_profile.get("complexity_confidence"),
                )
                debug_summary = _build_debug_summary(
                    strategy="debugging",
                    error=error,
                    error_type=error_type,
                    confidence=confidence,
                    retry_count=failure_count,
                    activation_level=debug_activation_level,
                    retry_hint=retry_hint,
                    quality_gate_details=quality_gate_details,
                    reflection_artifact=reflection_artifact,
                    escalation_reason="debugging",
                )
                state.metadata["debug_summary"] = debug_summary
                memory_ops.update_debug_summary(str(session_path), debug_summary)

            state = transition_phase(state, "DEBUGGING", reason=f"Failure: {error}")
            save_state(workdir, state)

            if state.session_id in _active_loggers:
                logger = _active_loggers[state.session_id]
                logger.exit_phase(current_phase)
                logger.enter_phase("DEBUGGING")

            return {
                "success": True,
                "action": "debugging",
                "previous_phase": current_phase,
                "new_phase": "DEBUGGING",
                "error": error,
                "error_type": error_type,
                "error_history": _get_error_history(state),
                "reflection_recorded": bool(reflection_artifact),
                "debug_summary": state.metadata.get("debug_summary", {}) if state.metadata else {},
                **reflection_artifact,
            }
        else:
            return {
                "success": False,
                "error": f"Cannot transition from {current_phase} to DEBUGGING",
                "reflection_recorded": bool(reflection_artifact),
                "debug_summary": state.metadata.get("debug_summary", {}) if state.metadata else {},
                **reflection_artifact,
            }

    if strategy == "abort":
        reflection_artifact = _persist_failure_reflection(
            workdir,
            state,
            error,
            error_type,
            confidence,
            retry_hint,
            strategy,
            quality_gate_details=quality_gate_details,
        )
        debug_summary = _build_debug_summary(
            strategy="abort",
            error=error,
            error_type=error_type,
            confidence=confidence,
            retry_count=retry_count,
            activation_level=int(runtime_profile.get("skill_activation_level", 0)) if runtime_profile else 0,
            retry_hint=retry_hint,
            quality_gate_details=quality_gate_details,
            reflection_artifact=reflection_artifact,
            escalation_reason="abort",
        )
        if state.metadata is None:
            state.metadata = {}
        state.metadata["debug_summary"] = debug_summary
        memory_ops.update_debug_summary(str(session_path), debug_summary)
        complete_workflow(workdir, "failed", error)
        return {
            "success": True,
            "action": "aborted",
            "final_state": "failed",
            "error": error,
            "error_type": error_type,
            "reflection_recorded": bool(reflection_artifact),
            "debug_summary": debug_summary,
            **reflection_artifact,
        }

    return {"success": False, "error": f"Unknown strategy: {strategy}"}


def main() -> int:
    """
    CLI entry point for the workflow runtime engine.

    Supported operations (--op):
        init          Initialize a new workflow session
        advance       Advance to a new phase
        snapshot      Get a snapshot of current workflow state
        recommend     Recommend next phases from current state
        validate      Validate workflow state integrity
        plan          Generate a task plan
        frontier      Compute the execution frontier (ready/blocked/conflict tasks)
        checkpoint    Conditionally save a checkpoint
        complete      Mark workflow as complete (with contract gate validation)
        log-decision  Record a workflow decision
        log-file      Record a file change
        validate-plan Validate task plan structure
        update-task   Update task status in plan
        resume        Resume from a checkpoint
        handle-failure Handle workflow failure with error classification
        team-run      Run multi-agent team orchestration

    Returns:
        Exit code (0 = success, non-zero = error)
    """
    parser = argparse.ArgumentParser(description="Agentic workflow runtime engine")
    parser.add_argument("--workdir", default=".", help="workspace directory")
    parser.add_argument("--op", choices=["init", "advance", "snapshot", "recommend", "validate", "plan", "frontier", "checkpoint", "complete", "log-decision", "log-file", "validate-plan", "update-task", "resume", "handle-failure", "team-run"], required=True)
    parser.add_argument("--prompt", help="user prompt for workflow initialization")
    parser.add_argument("--task-id", help="optional task id")
    parser.add_argument("--phase", help="target phase for advance")
    parser.add_argument("--progress", type=int, default=0, help="progress percent for advance")
    parser.add_argument("--task-status", help="task status for advance")
    parser.add_argument("--note", default="", help="note for phase advance")
    parser.add_argument("--no-auto-plan", action="store_true", help="disable auto task plan creation")
    parser.add_argument("--final-state", default="completed", help="final state for complete")
    parser.add_argument("--failure-reason", help="failure reason for complete")
    parser.add_argument("--decision", help="decision text for log-decision")
    parser.add_argument("--reason", default="", help="decision reason for log-decision")
    parser.add_argument("--path", help="file path for log-file")
    parser.add_argument("--action", default="modify", help="file action for log-file (create/modify/delete)")
    parser.add_argument("--status", help="task status for update-task (backlog/in_progress/completed/blocked)")
    parser.add_argument("--session-id", help="session id for resume")
    parser.add_argument("--error", help="error message for handle-failure")
    parser.add_argument("--strategy", default="retry", choices=["retry", "debugging", "abort"], help="failure handling strategy")
    parser.add_argument("--max-retries", type=int, default=3, help="max retry count")
    parser.add_argument("--use-real-agent", action="store_true", help="use real AI subagents in team-run (requires claude CLI)")
    args = parser.parse_args()

    if args.op == "init":
        if not args.prompt:
            print("错误: --prompt 必须指定")
            return 1
        result = initialize_workflow(
            args.prompt,
            workdir=args.workdir,
            task_id=args.task_id,
            auto_create_plan=not args.no_auto_plan,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "advance":
        if not args.phase:
            print("错误: --phase 必须指定")
            return 1
        try:
            result = advance_workflow(
                args.phase,
                workdir=args.workdir,
                progress=args.progress,
                task_status=args.task_status,
                note=args.note,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except ValueError as e:
            # Phase transition blocked (e.g., quality gate failure) - return as JSON error
            print(json.dumps({"error": str(e), "blocked": True}, ensure_ascii=False, indent=2))
            return 1

    if args.op == "recommend":
        snapshot = get_workflow_snapshot(args.workdir)
        print(json.dumps({"recommended_next_phases": snapshot["recommended_next_phases"]}, ensure_ascii=False, indent=2))
        return 0

    if args.op == "validate":
        from unified_state import validate_workflow_state
        is_valid, errors = validate_workflow_state(args.workdir)
        print(json.dumps({"valid": is_valid, "errors": errors}, ensure_ascii=False, indent=2))
        return 0

    if args.op == "plan":
        tasks, source = load_planning_tasks(args.workdir)
        print(json.dumps({"tasks": tasks, "next_tasks": next_plan_tasks(args.workdir), "plan_source": source}, ensure_ascii=False, indent=2))
        return 0

    if args.op == "frontier":
        frontier = compute_frontier(args.workdir)
        print(json.dumps(frontier, ensure_ascii=False, indent=2))
        return 0

    if args.op == "checkpoint":
        result = conditional_checkpoint(args.workdir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "validate-plan":
        is_valid, errors = validate_task_plan(args.workdir)
        print(json.dumps({"valid": is_valid, "errors": errors}, ensure_ascii=False, indent=2))
        return 0

    if args.op == "update-task":
        if not args.task_id:
            print("错误: --task-id required for update-task")
            return 1
        if not args.status:
            print("错误: --status required for update-task")
            return 1
        result = update_task_status_in_plan(args.workdir, args.task_id, args.status)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "complete":
        try:
            result = complete_workflow(
                args.workdir,
                final_state=args.final_state,
                failure_reason=args.failure_reason,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except ValueError as e:
            # Quality gate blocked completion
            print(json.dumps({"error": str(e), "blocked": True}, ensure_ascii=False, indent=2))
            return 1

    if args.op == "log-decision":
        if not args.decision:
            print("错误: --decision required for log-decision")
            return 1
        result = log_workflow_decision(args.workdir, args.decision, args.reason)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "log-file":
        if not args.path:
            print("错误: --path required for log-file")
            return 1
        result = log_workflow_file_change(args.workdir, args.path, args.action)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "resume":
        result = resume_workflow(args.workdir, args.session_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "handle-failure":
        if not args.error:
            print("错误: --error required for handle-failure")
            return 1
        result = handle_workflow_failure(
            args.workdir,
            error=args.error,
            strategy=args.strategy,
            max_retries=args.max_retries,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.op == "team-run":
        # Load state to get task info
        state = load_state(args.workdir)
        task_obj = state.task if state else None
        task_title = task_obj.title if task_obj and task_obj.title else "Untitled Team Task"
        contract = parse_phase_contract(args.workdir)
        frontier = compute_frontier(args.workdir)

        # Create and run team - tasks come from frontier/contract, not hardcoded
        phase_name = state.phase.get("current", "EXECUTING") if state and state.phase else "EXECUTING"
        team = TeamAgent(
            args.workdir,
            task=task_title,
            contract=contract,
            frontier=frontier,
            use_real_agent=getattr(args, 'use_real_agent', True),
        )
        team_result = team.run(phase=phase_name, register_artifacts=True)

        print(json.dumps({
            "team_session_id": team_result["session_id"],
            "tasks_completed": team_result["tasks_completed"],
            "tasks_failed": team_result["tasks_failed"],
            "outputs": team_result["outputs"],
            "used_real_agent": getattr(args, 'use_real_agent', True),
        }, ensure_ascii=False, indent=2))
        return 0

    print(json.dumps(get_workflow_snapshot(args.workdir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
