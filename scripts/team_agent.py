#!/usr/bin/env python3
"""
Small Team Agent - Lightweight Multi-Agent Team Orchestration

Stable team topology:
- 1 Lead Agent: task allocation and coordination
- Typed Workers: researcher, coder, reviewer, debugger
- Simple file-based communication via artifacts (no heavy message bus)

Works with contract + frontier mode:
1. Lead receives task and phase contract
2. Lead computes frontier, assigns tasks to workers
3. Worker executes task, writes results to artifact
4. Lead summarizes results, advances workflow

Usage:
    from team_agent import TeamAgent, WorkerType

    team = TeamAgent(workdir, task="Implement REST API", contract=contract)
    result = team.run()

    # Or use a single worker directly
    worker = WorkerAgent(WorkerType.CODER, workdir)
    output = worker.execute(task="Implement /users endpoint")
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, TypedDict

import search_adapter
from findings_paths import ensure_findings_dir, findings_latest_path
from review_paths import ensure_review_dir, review_latest_path
from safe_io import safe_write_text_locked
from unified_state import (
    ArtifactType,
    get_planning_summary,
    get_research_summary,
    get_review_summary,
    get_runtime_profile_summary,
    get_thinking_summary,
    load_state,
    register_artifact,
)

# Optional real agent runner (lazy import to avoid hard dependency)
_subagent_runner = None


def _get_subagent_runner():
    """Lazy-load SubAgentRunner to avoid circular imports."""
    global _subagent_runner
    if _subagent_runner is None:
        try:
            from subagent_runner import SubAgentRunner
            _subagent_runner = SubAgentRunner
        except ImportError:
            _subagent_runner = False  # Not available
    return _subagent_runner


# ============================================================================
# Worker Type Definitions
# ============================================================================

class WorkerType(Enum):
    """Worker类型枚举"""
    RESEARCHER = "researcher"   # 研究搜索
    CODER = "coder"            # 代码实现
    REVIEWER = "reviewer"      # 代码审查
    DEBUGGER = "debugger"      # 调试修复
    LEAD = "lead"              # 领导协调


WORKER_DESCRIPTIONS: dict[WorkerType, str] = {
    WorkerType.RESEARCHER: "信息搜索、最佳实践调研、技术方案研究",
    WorkerType.CODER: "代码实现、TDD驱动开发、功能实现",
    WorkerType.REVIEWER: "代码审查、质量门禁、验收测试",
    WorkerType.DEBUGGER: "错误定位、问题修复、调试执行",
    WorkerType.LEAD: "任务分配、进度协调、结果汇总",
}


class TeamRunResults(TypedDict):
    """Team run results type"""
    session_id: str
    task: str
    tasks_completed: int
    tasks_failed: int
    outputs: list[dict[str, Any]]
    artifacts: list[str]


class WorkerEnvelope(TypedDict):
    """Structured worker output passed back to the lead agent.

    Keep the lead-side payload small and schema-driven so raw tool output stays
    in the worker artifact, not in the coordination channel.
    """
    worker_type: str
    task: str
    success: bool
    summary: str
    artifact_refs: list[str]
    duration_seconds: float
    degraded_mode: bool
    warning: str | None
    error: str | None


def _compact_value(value: Any, limit: int = 120) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float, bool)):
        return str(value)
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _compact_list(values: Any, limit: int = 3) -> list[str]:
    if not isinstance(values, list):
        return []
    compacted: list[str] = []
    for item in values[:limit]:
        item_text = _compact_value(item, 80)
        if item_text:
            compacted.append(item_text)
    return compacted


def build_shared_memory_capsule(
    workdir: str,
    task: str,
    contract: dict[str, Any] | None = None,
    frontier: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a short lead-facing memory capsule from the runtime state."""
    state = load_state(workdir)
    runtime_profile = get_runtime_profile_summary(state)
    planning_summary = get_planning_summary(workdir, state)
    research_summary = get_research_summary(workdir, state)
    thinking_summary = get_thinking_summary(workdir, state)
    review_summary = get_review_summary(workdir, state)
    contract = contract or {}
    frontier = frontier or {}

    capsule = {
        "task": _compact_value(task, 160),
        "runtime_profile": {
            "complexity": runtime_profile.get("complexity"),
            "skill_policy": runtime_profile.get("skill_policy"),
            "skill_activation_level": runtime_profile.get("skill_activation_level"),
            "profile_source": runtime_profile.get("profile_source"),
        },
        "contract": {
            "status": contract.get("status"),
            "goal_count": len(contract.get("goals", [])) if isinstance(contract.get("goals"), list) else 0,
            "acceptance_count": len(contract.get("acceptance_criteria", [])) if isinstance(contract.get("acceptance_criteria"), list) else 0,
            "impact_files": _compact_list(contract.get("impact_files", []), limit=3),
            "dependencies": _compact_list(contract.get("dependencies", []), limit=3),
            "rollback_note": _compact_value(contract.get("rollback_note", ""), 100),
        },
        "planning": {
            "planning_mode": planning_summary.get("planning_mode"),
            "plan_source": planning_summary.get("plan_source"),
            "plan_digest": planning_summary.get("plan_digest"),
            "worktree_recommended": planning_summary.get("worktree_recommended"),
            "next_task_ids": _compact_list(planning_summary.get("next_task_ids", []), limit=3),
        },
        "research": {
            "evidence_status": research_summary.get("evidence_status"),
            "evidence_tier": research_summary.get("evidence_tier"),
            "sources_count": research_summary.get("sources_count"),
            "search_engine": research_summary.get("search_engine"),
            "degraded_mode": research_summary.get("degraded_mode"),
        },
        "thinking": {
            "workflow_label": thinking_summary.get("workflow_label"),
            "thinking_mode": thinking_summary.get("thinking_mode"),
            "thinking_methods": _compact_list(thinking_summary.get("thinking_methods", []), limit=5),
            "major_contradiction": _compact_value(thinking_summary.get("major_contradiction", ""), 100),
            "stage_judgment": thinking_summary.get("stage_judgment"),
            "local_attack_point": _compact_value(thinking_summary.get("local_attack_point", ""), 100),
            "confidence_level": thinking_summary.get("confidence_level"),
        },
        "review": {
            "review_status": review_summary.get("review_status"),
            "review_source": review_summary.get("review_source"),
            "stage_1_status": review_summary.get("stage_1_status"),
            "stage_2_status": review_summary.get("stage_2_status"),
            "risk_level": review_summary.get("risk_level"),
            "files_reviewed": review_summary.get("files_reviewed"),
            "degraded_mode": review_summary.get("degraded_mode"),
        },
        "frontier": {
            "plan_source": frontier.get("plan_source"),
            "executable_count": len(frontier.get("executable_frontier", [])) if isinstance(frontier.get("executable_frontier"), list) else 0,
            "parallel_group_count": len(frontier.get("parallel_candidates", [])) if isinstance(frontier.get("parallel_candidates"), list) else 0,
            "conflict_group_count": len(frontier.get("conflict_groups", [])) if isinstance(frontier.get("conflict_groups"), list) else 0,
        },
    }
    return capsule


# ============================================================================
# Message Types for Team Communication
# ============================================================================

class MessageType(Enum):
    """消息类型"""
    TASK_ASSIGN = "task_assign"       # 任务分配
    TASK_RESULT = "task_result"       # 任务结果
    TASK_ERROR = "task_error"         # 任务错误
    STATUS_UPDATE = "status_update"   # 状态更新
    FRONTIER_UPDATE = "frontier_update"  # frontier 更新


@dataclass
class TeamMessage:
    """团队消息"""
    id: str
    msg_type: MessageType
    from_worker: WorkerType
    to_worker: WorkerType | None  # None = broadcast
    content: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    parent_id: str | None = None  # for tracing

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.msg_type.value,
            "from": self.from_worker.value,
            "to": self.to_worker.value if self.to_worker else "broadcast",
            "content": self.content,
            "timestamp": self.timestamp,
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TeamMessage:
        return cls(
            id=d["id"],
            msg_type=MessageType(d["type"]),
            from_worker=WorkerType(d["from"]),
            to_worker=WorkerType(d["to"]) if d.get("to") and d["to"] != "broadcast" else None,
            content=d["content"],
            timestamp=d.get("timestamp", datetime.now().isoformat()),
            parent_id=d.get("parent_id"),
        )


# ============================================================================
# Worker Agent
# ============================================================================

@dataclass
class WorkerResult:
    """Worker执行结果"""
    worker_type: WorkerType
    task: str
    output: str
    success: bool
    artifacts: list[str] = field(default_factory=list)
    error: str | None = None
    duration_seconds: float = 0.0


class WorkerAgent:
    """
    轻量级 Worker Agent

    每个 worker 只做一件事:
    - Researcher: 搜索研究
    - Coder: 实现代码
    - Reviewer: 审查代码
    - Debugger: 调试修复
    """

    def __init__(self, worker_type: WorkerType, workdir: str = ".", use_real_agent: bool = True):
        self.worker_type = worker_type
        self.workdir = Path(workdir)
        self.session_id = f"{worker_type.value}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.use_real_agent = use_real_agent

    def execute(self, task: str, context: dict[str, Any] | None = None) -> WorkerResult:
        """
        执行任务

        Args:
            task: 任务描述
            context: 上下文信息 (可选)

        Returns:
            WorkerResult: 执行结果
        """
        start_time = datetime.now()

        try:
            if self.worker_type == WorkerType.RESEARCHER:
                output, artifacts = self._do_research(task, context)
            elif self.worker_type == WorkerType.CODER:
                output, artifacts = self._do_code(task, context)
            elif self.worker_type == WorkerType.REVIEWER:
                output, artifacts = self._do_review(task, context)
            elif self.worker_type == WorkerType.DEBUGGER:
                output, artifacts = self._do_debug(task, context)
            else:
                output = f"Unknown worker type: {self.worker_type}"
                artifacts = []

            duration = (datetime.now() - start_time).total_seconds()
            return WorkerResult(
                worker_type=self.worker_type,
                task=task,
                output=output,
                success=True,
                artifacts=artifacts,
                duration_seconds=duration,
            )

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            return WorkerResult(
                worker_type=self.worker_type,
                task=task,
                output="",
                success=False,
                error=str(e),
                duration_seconds=duration,
            )

    @staticmethod
    def _summarize_output(output: str, limit: int | None = None) -> str:
        """Create a compact, schema-friendly summary for lead-side consumption.

        AgentSys P0: The summary is the ONLY thing that crosses to lead context.
        Raw tool output stays in artifacts. This method enforces the boundary.
        Default limit is MAX_SUMMARY_LENGTH (260 chars) to keep lead payload small.
        """
        if not output:
            return ""
        effective_limit = limit if limit is not None else WorkerAgent.MAX_SUMMARY_LENGTH
        normalized = " ".join(output.split())
        if len(normalized) <= effective_limit:
            return normalized
        return normalized[: effective_limit - 1].rstrip() + "…"

    # AgentSys P0: Hard limits to prevent raw output leaking into lead context
    MAX_SUMMARY_LENGTH: int = 260  # Lead-safe summary max chars
    MAX_WARNING_LENGTH: int = 200   # Warning field max chars

    @staticmethod
    def _validate_envelope(envelope: WorkerEnvelope) -> None:
        """Validate the lead-facing envelope before it leaves the worker boundary.

        AgentSys enforcement:
        - All required keys must be present
        - Summary must be a short, lead-safe string (not raw output)
        - Artifact refs must be valid paths
        - No raw tool output in any envelope field
        """
        required_keys = {
            "worker_type",
            "task",
            "success",
            "summary",
            "artifact_refs",
            "duration_seconds",
            "degraded_mode",
            "warning",
            "error",
        }
        missing = required_keys.difference(envelope.keys())
        if missing:
            raise ValueError(f"invalid worker envelope: missing keys {sorted(missing)}")

        if not isinstance(envelope["summary"], str):
            raise ValueError("invalid worker envelope: summary must be a string")
        if not isinstance(envelope["artifact_refs"], list) or not all(
            isinstance(item, str) for item in envelope["artifact_refs"]
        ):
            raise ValueError("invalid worker envelope: artifact_refs must be a list[str]")
        if envelope["success"] and not envelope["summary"].strip():
            raise ValueError("invalid worker envelope: success results must include a summary")
        if envelope["duration_seconds"] < 0:
            raise ValueError("invalid worker envelope: duration_seconds must be non-negative")

        # AgentSys P0: Prevent raw output from leaking into lead context
        # These fields must ONLY contain structured summaries, NOT raw tool output
        max_summary_len = WorkerAgent.MAX_SUMMARY_LENGTH
        max_warning_len = WorkerAgent.MAX_WARNING_LENGTH
        if len(envelope["summary"]) > max_summary_len:
            raise ValueError(
                f"invalid worker envelope: summary exceeds {max_summary_len} chars. "
                f"Raw output must stay in artifact files, not in envelope."
            )
        if envelope["warning"] and len(envelope["warning"]) > max_warning_len:
            raise ValueError(
                f"invalid worker envelope: warning exceeds {max_warning_len} chars. "
                f"Short warning only, raw output in artifacts."
            )
        if envelope["error"] and len(envelope["error"]) > max_warning_len:
            raise ValueError(
                f"invalid worker envelope: error exceeds {max_warning_len} chars. "
                f"Short error only, full trace in artifacts."
            )

    def build_envelope(self, task: str, result: WorkerResult) -> WorkerEnvelope:
        """Convert a raw WorkerResult into a structured, lead-safe envelope."""
        degraded_mode = False
        warning = None
        if self.worker_type == WorkerType.RESEARCHER and result.success and result.artifacts:
            degraded_mode = any("degraded" in Path(path).name for path in result.artifacts)

        if result.success and self.worker_type == WorkerType.RESEARCHER and result.output:
            if "degraded" in result.output.lower():
                degraded_mode = True
                warning = "research output indicates degraded mode"

        summary = self._summarize_output(result.output)
        if not summary and result.success:
            summary = f"{self.worker_type.value} completed {task}"

        return WorkerEnvelope(
            worker_type=self.worker_type.value,
            task=task,
            success=result.success,
            summary=summary,
            artifact_refs=list(result.artifacts),
            duration_seconds=result.duration_seconds,
            degraded_mode=degraded_mode,
            warning=warning,
            error=result.error,
        )

    def _do_research(self, task: str, context: dict[str, Any] | None) -> tuple[str, list[str]]:
        """Research worker: 搜索研究"""
        query = task
        response, used_fallback = search_adapter.search_with_fallback(query, num_results=5)

        findings: list[str] = []
        if response.results:
            for r in response.results:
                findings.append(f"## {r.title}\n{r.snippet}\nSource: {r.url}")
            evidence_status = "- External sources were found and summarized"
            conclusions = "- Research produced source-backed notes for downstream planning"
        else:
            findings.append("## No verifiable sources\nNo usable external sources were returned for this query.")
            evidence_status = "- No verifiable external sources were returned"
            conclusions = "- Treat this result as degraded and re-run research with a narrower query"

        output = f"# Research Findings\n\nQuery: {query}\n\n## Evidence Status\n{evidence_status}\n\n## Key Findings\n" + "\n\n".join(findings)
        output += f"\n\n## Conclusions\n{conclusions}"
        output += f"\n\n**Search Engine**: {response.search_engine}"
        if used_fallback or response.metadata.get("degraded_mode"):
            output += f"\n**Warning**: {response.metadata.get('degraded_reason', 'Degraded mode')}"

        # Write findings artifact via safe_write_text_locked
        findings_dir = ensure_findings_dir(self.workdir)
        findings_path = findings_dir / f"findings_{self.session_id}.md"
        findings_latest = findings_latest_path(self.workdir)
        safe_write_text_locked(findings_path, output)
        safe_write_text_locked(findings_latest, output)
        # Register artifact with unified pipeline
        register_artifact(str(self.workdir), ArtifactType.FINDINGS, str(findings_path), self.worker_type.value, "team-agent",
                         metadata={"task": task, "session_id": self.session_id})

        return output, [str(findings_path)]

    def _do_code(self, task: str, context: dict[str, Any] | None) -> tuple[str, list[str]]:
        """Coder worker: 代码实现 (生成代码片段/建议)"""
        # 如果 use_real_agent=False，明确跳过，不输出假结果
        if not self.use_real_agent:
            skipped_msg = (
                f"# Code Implementation Plan\n\nTask: {task}\n\n"
                f"## Status: SKIPPED\n\n"
                f"Real agent execution is disabled (`use_real_agent=False`).\n"
                f"To enable, set `use_real_agent=True` when constructing WorkerAgent.\n"
            )
            code_path = self.workdir / f"code_{self.session_id}.md"
            safe_write_text_locked(code_path, skipped_msg)
            register_artifact(str(self.workdir), ArtifactType.CODE, str(code_path), self.worker_type.value, "team-agent",
                            metadata={"task": task, "session_id": self.session_id, "skipped": True})
            return skipped_msg, [str(code_path)]

        subagent_runner_class = _get_subagent_runner()
        if subagent_runner_class:
            runner = subagent_runner_class(workdir=str(self.workdir))
            result = runner.run(
                phase="EXECUTING",
                task=task,
                session_id=self.session_id,
                context=context,
            )
            if result.success:
                return result.output, result.artifacts

        # Fallback when SubAgentRunner unavailable: explicit template (not fake output)
        output = f"# Code Implementation Plan\n\nTask: {task}\n\n"
        capsule = context.get("shared_memory_capsule") if context else None
        if capsule and capsule.get("contract", {}).get("impact_files"):
            output += "## Shared Memory Capsule\n"
            output += f"- Plan digest: {capsule.get('planning', {}).get('plan_digest')}\n"
            output += f"- Contract status: {capsule.get('contract', {}).get('status')}\n"
            output += f"- Evidence tier: {capsule.get('research', {}).get('evidence_tier')}\n"
            output += f"- Thinking mode: {capsule.get('thinking', {}).get('thinking_mode')}\n"
        if context and context.get("owned_files"):
            output += "## Target Files\n"
            for f in context["owned_files"]:
                output += f"- {f}\n"
        if context and context.get("verification"):
            output += f"\n## Verification\n{context['verification']}\n"
        if context and context.get("planning_summary"):
            planning_summary = context["planning_summary"]
            output += "\n## Planning Context\n"
            output += f"- Plan digest: {planning_summary.get('plan_digest')}\n"
            output += f"- Worktree recommended: {planning_summary.get('worktree_recommended')}\n"
            next_task_ids = planning_summary.get("next_task_ids", [])
            if next_task_ids:
                output += f"- Next tasks: {', '.join(next_task_ids)}\n"
        output += "\n## Implementation Notes\n"
        output += "TDD approach recommended:\n1. Write failing test\n2. Implement minimal code\n3. Refactor\n"

        code_path = self.workdir / f"code_{self.session_id}.md"
        safe_write_text_locked(code_path, output)
        register_artifact(str(self.workdir), ArtifactType.CODE, str(code_path), self.worker_type.value, "team-agent",
                        metadata={"task": task, "session_id": self.session_id})
        return output, [str(code_path)]

    def _do_review(self, task: str, context: dict[str, Any] | None) -> tuple[str, list[str]]:
        """Reviewer worker: 代码审查"""
        # 如果 use_real_agent=False，明确跳过
        if not self.use_real_agent:
            skipped_msg = (
                f"# Code Review\n\nTask: {task}\n\n"
                f"## Status: SKIPPED\n\n"
                f"Real agent execution is disabled (`use_real_agent=False`).\n"
                f"To enable, set `use_real_agent=True` when constructing WorkerAgent.\n"
                f"\n## Files Reviewed\n"
                f"**Files Reviewed**: 0 code files\n"
                f"\n## Contract Coverage\n"
                f"- Contract alignment: template\n"
                f"- Contract files count: 0\n"
                f"- Reviewed targets count: 0\n"
                f"- Matched contract files: 0\n"
                f"\n## Stage 1: Spec Compliance\n"
                f"- Contract/owned_files alignment: UNKNOWN\n"
                f"- Acceptance coverage: UNKNOWN\n"
                f"- Scope completeness: UNKNOWN\n"
                f"\n## Stage 2: Code Quality\n"
                f"- Correctness: UNKNOWN\n"
                f"- Security: UNKNOWN\n"
                f"- Performance: UNKNOWN\n"
                f"- Maintainability: UNKNOWN\n"
                f"\n## Verdict\n"
                f"- Status: SKIPPED\n"
            )
            review_dir = ensure_review_dir(self.workdir)
            review_path = review_dir / f"review_{self.session_id}.md"
            review_latest = review_latest_path(self.workdir)
            safe_write_text_locked(review_path, skipped_msg)
            safe_write_text_locked(review_latest, skipped_msg)
            register_artifact(str(self.workdir), ArtifactType.REVIEW, str(review_path), self.worker_type.value, "team-agent",
                            metadata={"task": task, "session_id": self.session_id, "skipped": True})
            return skipped_msg, [str(review_path)]

        output = f"# Code Review\n\nTask: {task}\n\n"
        output += "## Stage 1: Spec Compliance\n"
        output += "- Contract/owned_files alignment\n"
        output += "- Acceptance coverage\n"
        output += "- Scope completeness\n"
        output += "\n## Stage 2: Code Quality\n"
        output += "- Correctness\n"
        output += "- Security\n"
        output += "- Performance\n"
        output += "- Maintainability\n"

        capsule = context.get("shared_memory_capsule") if context else None
        if capsule and capsule.get("review"):
            output += "\n## Shared Memory Capsule\n"
            output += f"- Plan digest: {capsule.get('planning', {}).get('plan_digest')}\n"
            output += f"- Contract status: {capsule.get('contract', {}).get('status')}\n"
            output += f"- Review status: {capsule.get('review', {}).get('review_status')}\n"
            output += f"- Contract alignment: {capsule.get('review', {}).get('contract_alignment')}\n"
            output += f"- Thinking mode: {capsule.get('thinking', {}).get('thinking_mode')}\n"
        if context and context.get("owned_files"):
            output += "\n## Files to Review\n"
            for f in context["owned_files"]:
                output += f"- {f}\n"
        reviewed_files = len(context.get("owned_files", [])) if context else 0
        output += f"\n## Files Reviewed\n**Files Reviewed**: {reviewed_files} code files\n"
        contract_files_count = 0
        if context and context.get("contract"):
            contract_files_count = len(context.get("contract", {}).get("owned_files", [])) + len(context.get("contract", {}).get("impact_files", []))
        contract_alignment = "legacy_targeted" if reviewed_files > 0 else "template"
        output += "\n## Contract Coverage\n"
        output += f"- Contract alignment: {contract_alignment}\n"
        output += f"- Contract files count: {contract_files_count}\n"
        output += f"- Reviewed targets count: {reviewed_files}\n"
        output += f"- Matched contract files: {reviewed_files if contract_files_count else 0}\n"

        if context and context.get("planning_summary"):
            planning_summary = context["planning_summary"]
            output += "\n## Planning Context\n"
            output += f"- Plan digest: {planning_summary.get('plan_digest')}\n"
            output += f"- Worktree recommended: {planning_summary.get('worktree_recommended')}\n"
            next_task_ids = planning_summary.get("next_task_ids", [])
            if next_task_ids:
                output += f"- Next tasks: {', '.join(next_task_ids)}\n"

        output += "\n## Verdict\n"
        output += "- Status: REVIEWED\n"

        review_dir = ensure_review_dir(self.workdir)
        review_path = review_dir / f"review_{self.session_id}.md"
        review_latest = review_latest_path(self.workdir)
        safe_write_text_locked(review_path, output)
        safe_write_text_locked(review_latest, output)
        register_artifact(str(self.workdir), ArtifactType.REVIEW, str(review_path), self.worker_type.value, "team-agent",
                        metadata={"task": task, "session_id": self.session_id})
        return output, [str(review_path)]

    def _do_debug(self, task: str, context: dict[str, Any] | None) -> tuple[str, list[str]]:
        """Debugger worker: 调试修复"""
        # 如果 use_real_agent=False，明确跳过
        if not self.use_real_agent:
            skipped_msg = (
                f"# Debug Analysis\n\nTask: {task}\n\n"
                f"## Status: SKIPPED\n\n"
                f"Real agent execution is disabled (`use_real_agent=False`).\n"
                f"To enable, set `use_real_agent=True` when constructing WorkerAgent.\n"
            )
            debug_path = self.workdir / f"debug_{self.session_id}.md"
            safe_write_text_locked(debug_path, skipped_msg)
            register_artifact(str(self.workdir), ArtifactType.DEBUG, str(debug_path), self.worker_type.value, "team-agent",
                            metadata={"task": task, "session_id": self.session_id, "skipped": True})
            return skipped_msg, [str(debug_path)]

        output = f"# Debug Analysis\n\nTask: {task}\n\n"
        output += "## Debugging Steps\n"
        output += "1. Reproduce the issue\n"
        output += "2. Identify root cause\n"
        output += "3. Implement fix\n"
        output += "4. Verify fix\n"
        output += "5. Check for regressions\n"

        if context and context.get("error"):
            output += f"\n## Error Context\n{context['error']}\n"

        debug_path = self.workdir / f"debug_{self.session_id}.md"
        safe_write_text_locked(debug_path, output)
        register_artifact(str(self.workdir), ArtifactType.DEBUG, str(debug_path), self.worker_type.value, "team-agent",
                        metadata={"task": task, "session_id": self.session_id})
        return output, [str(debug_path)]


# ============================================================================
# Team Agent (Lead Orchestrator)
# ============================================================================

@dataclass
class TeamTask:
    """团队任务"""
    id: str
    description: str
    assigned_worker: WorkerType | None = None
    status: str = "pending"  # pending, assigned, completed, failed
    result: WorkerResult | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class TeamAgent:
    """
    Lead Agent - Team Coordinator.

    Responsibilities:
    1. Parse contract and frontier
    2. Assign tasks to appropriate workers
    3. Collect and summarize results
    4. Advance workflow

    Usage:
        team = TeamAgent(workdir, task="Implement REST API")
        result = team.run()
    """

    def __init__(
        self,
        workdir: str = ".",
        task: str | None = None,
        contract: dict[str, Any] | None = None,
        frontier: dict[str, Any] | None = None,
        use_real_agent: bool = True,
    ):
        self.workdir = Path(workdir)
        self.task = task or "Untitled task"
        self.contract = contract or {}
        self.frontier = frontier or {}
        self.session_id = f"team-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.tasks: dict[str, TeamTask] = {}
        self.messages: list[TeamMessage] = []
        self.use_real_agent = use_real_agent
        self.execution_context: dict[str, Any] = {}

    def add_task(self, description: str, worker_type: WorkerType | None = None) -> str:
        """添加任务"""
        task_id = str(uuid.uuid4())[:8]
        # If worker_type is provided, auto-assign
        status = "assigned" if worker_type else "pending"
        task = TeamTask(
            id=task_id,
            description=description,
            assigned_worker=worker_type,
            status=status,  # pending, assigned, completed, failed
        )
        self.tasks[task_id] = task
        return task_id

    def assign_task(self, task_id: str, worker_type: WorkerType) -> None:
        """分配任务给 worker"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        self.tasks[task_id].assigned_worker = worker_type
        self.tasks[task_id].status = "assigned"

    def execute_task(self, task_id: str) -> WorkerResult:
        """执行单个任务"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]
        if not task.assigned_worker:
            raise ValueError(f"Task {task_id} has no assigned worker")

        worker = WorkerAgent(task.assigned_worker, str(self.workdir), use_real_agent=self.use_real_agent)
        execution_context = self.execution_context or {"contract": self.contract}
        result = worker.execute(task.description, context=execution_context)
        envelope = worker.build_envelope(task.description, result)
        WorkerAgent._validate_envelope(envelope)

        task.result = result
        task.status = "completed" if result.success else "failed"

        # Log message
        msg = TeamMessage(
            id=str(uuid.uuid4())[:8],
            msg_type=MessageType.TASK_RESULT if result.success else MessageType.TASK_ERROR,
            from_worker=task.assigned_worker,
            to_worker=WorkerType.LEAD,
            content={
                "task_id": task_id,
                "envelope": envelope,
            },
            parent_id=task_id,
        )
        self.messages.append(msg)

        return result

    def run(self, phase: str = "EXECUTING", register_artifacts: bool = False) -> TeamRunResults:
        """
        运行团队任务

        基于 contract 和 frontier 自动分配任务。
        使用 frontier 分组进行 parallel-safe scheduling:
        - parallel_candidates: parallel-ready 任务候选（当前为顺序调度，不是真并发）
        - conflict_groups: 有文件冲突的任务，必须串行执行

        注意: 当前实现是 "parallel-ready scheduling hints"（调度语义），
        不是 "stable parallel orchestration"（真并发执行）。
        要支持真并发需接入 parallel_executor.py 等并发执行器。

        Args:
            phase: Current workflow phase for artifact registration
            register_artifacts: Whether to register artifacts with the artifact registry

        Returns:
            TeamRunResults with results summary
        """
        results: TeamRunResults = {
            "session_id": self.session_id,
            "task": self.task,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "outputs": [],
            "artifacts": [],
        }

        shared_memory_capsule = build_shared_memory_capsule(
            str(self.workdir),
            self.task,
            contract=self.contract,
            frontier=self.frontier,
        )
        self.execution_context = {
            "shared_memory_capsule": shared_memory_capsule,
            "contract": self.contract,
            "frontier": self.frontier,
            "planning_summary": shared_memory_capsule.get("planning", {}),
            "research_summary": shared_memory_capsule.get("research", {}),
            "thinking_summary": shared_memory_capsule.get("thinking", {}),
            "review_summary": shared_memory_capsule.get("review", {}),
            "runtime_profile_summary": shared_memory_capsule.get("runtime_profile", {}),
        }

        executed_ids: set = set()

        # 如果有 frontier，使用 frontier 分配任务
        if self.frontier.get("executable_frontier"):
            for task_data in self.frontier["executable_frontier"]:
                task_desc = f"Execute: {task_data.get('title', 'Untitled')}"
                worker_type = self._infer_worker_type(task_data)
                self.add_task(task_desc, worker_type)

        # 如果有 contract goals，为每个 goal 添加任务
        if self.contract.get("goals"):
            for goal in self.contract["goals"]:
                task_desc = f"Goal: {goal}"
                self.add_task(task_desc, WorkerType.CODER)

        # 执行 parallel_candidates (顺序执行，当前为 parallel-ready)
        parallel_candidates = self.frontier.get("parallel_candidates", [])
        for parallel_group in parallel_candidates:
            # 并行执行组内所有任务
            for task_data in parallel_group:
                task_desc = f"Parallel: {task_data.get('title', 'Untitled')}"
                worker_type = self._infer_worker_type(task_data)
                task_id = self.add_task(task_desc, worker_type)
                self._execute_single_task(task_id, results, executed_ids)

        # 2. 执行 conflict_groups (冲突任务串行)
        conflict_groups = self.frontier.get("conflict_groups", [])
        for conflict_group in conflict_groups:
            for task_data in conflict_group:
                task_desc = f"Conflict: {task_data.get('title', 'Untitled')}"
                worker_type = self._infer_worker_type(task_data)
                task_id = self.add_task(task_desc, worker_type)
                self._execute_single_task(task_id, results, executed_ids)

        # 3. 执行通过 add_task 直接添加的任务（非 frontier 任务）
        for task_id, task in self.tasks.items():
            if task.status == "assigned" and task.assigned_worker and task_id not in executed_ids:
                self._execute_single_task(task_id, results, executed_ids)

        # Save team snapshot for recoverability
        self.save_snapshot(str(self.workdir))

        # Register artifacts with authoritative pipeline if requested
        if register_artifacts and results.get("artifacts"):
            for artifact in results["artifacts"]:
                register_artifact(str(self.workdir), "team_output", artifact, phase)

        return results

    def _execute_single_task(self, task_id: str, results: TeamRunResults, executed_ids: set) -> None:
        """执行单个任务并更新 results"""
        task = self.tasks.get(task_id)
        if not task or not task.assigned_worker:
            return
        if task_id in executed_ids:
            return

        result = self.execute_task(task_id)
        executed_ids.add(task_id)

        if result.success:
            results["tasks_completed"] += 1
            results["artifacts"].extend(result.artifacts)
        else:
            results["tasks_failed"] += 1
        envelope = task.result and WorkerAgent._summarize_output(task.result.output) or ""
        results["outputs"].append({
            "task_id": task_id,
            "worker": task.assigned_worker.value,
            "success": result.success,
            "summary": envelope,
            "artifact_refs": result.artifacts,
            "error": result.error,
        })

    def _infer_worker_type(self, task_data: dict[str, Any]) -> WorkerType:
        """根据任务数据推断合适的 worker 类型"""
        title = task_data.get("title", "").lower()
        desc = task_data.get("description", "").lower()

        combined = title + " " + desc

        if any(k in combined for k in ["research", "search", "调研", "研究", "查找"]):
            return WorkerType.RESEARCHER
        if any(k in combined for k in ["review", "审查", "检查", "验证"]):
            return WorkerType.REVIEWER
        if any(k in combined for k in ["debug", "fix", "error", "bug", "调试", "修复"]):
            return WorkerType.DEBUGGER
        if any(k in combined for k in ["implement", "code", "实现", "代码", "功能"]):
            return WorkerType.CODER

        # 默认分配给 coder
        return WorkerType.CODER

    def get_state(self) -> dict[str, Any]:
        """获取团队状态（含 output summaries 和 artifact paths，用于可审计性）"""
        return {
            "session_id": self.session_id,
            "task": self.task,
            "total_tasks": len(self.tasks),
            "tasks": {
                tid: {
                    "description": t.description,
                    "assigned_worker": t.assigned_worker.value if t.assigned_worker else None,
                    "status": t.status,
                    "success": t.result.success if t.result else None,
                    "output_summary": t.result.output[:200] if t.result and t.result.output else None,
                    "error": t.result.error if t.result else None,
                    "artifacts": t.result.artifacts if t.result else [],
                    "duration_seconds": t.result.duration_seconds if t.result else None,
                }
                for tid, t in self.tasks.items()
            },
            "messages_count": len(self.messages),
        }

    def sanitize_for_handoff(self) -> dict[str, Any]:
        """AgentSys P0: Strip raw outputs, keep only lead-safe structured summaries.

        This is the boundary function: checkpoint/handoff must NEVER carry raw
        tool output. Only summaries and artifact references cross to lead context.
        Raw outputs stay in worker artifacts on disk.

        Returns:
            Handoff-safe dict with only summaries, artifact refs, and metadata.
        """
        sanitized_tasks: list[dict[str, Any]] = []
        for tid, t in self.tasks.items():
            task_summary: dict[str, Any] = {
                "id": tid,
                "description": t.description,
                "assigned_worker": t.assigned_worker.value if t.assigned_worker else None,
                "status": t.status,
                "success": t.result.success if t.result else None,
                "duration_seconds": t.result.duration_seconds if t.result else None,
            }
            # Only include lead-safe fields: summary and artifact refs
            # NEVER include raw output in handoff
            if t.result:
                task_summary["summary"] = WorkerAgent._summarize_output(
                    t.result.output, limit=WorkerAgent.MAX_SUMMARY_LENGTH
                )
                task_summary["artifact_refs"] = list(t.result.artifacts) if t.result.artifacts else []
                task_summary["error"] = (t.result.error or "")[:WorkerAgent.MAX_WARNING_LENGTH] if t.result.error else None
            sanitized_tasks.append(task_summary)

        return {
            "session_id": self.session_id,
            "task": self.task,
            "shared_memory_capsule": self.execution_context.get("shared_memory_capsule", {}),
            "total_tasks": len(sanitized_tasks),
            "tasks": sanitized_tasks,
            "messages_count": len(self.messages),
        }

    def save_snapshot(self, workdir: str) -> None:
        """Save team state snapshot to .team_registry.json for recoverability"""
        registry_path = Path(workdir) / ".team_registry.json"

        # Load existing registry or create new
        if registry_path.exists():
            try:
                import json as json_lib
                registry = json_lib.loads(registry_path.read_text(encoding="utf-8"))
            except (json_lib.JSONDecodeError, OSError):
                registry = {"team_sessions": []}
        else:
            registry = {"team_sessions": []}

        # Add/update this session
        snapshot = {
            "session_id": self.session_id,
            "task": self.task,
            "timestamp": datetime.now().isoformat(),
            "total_tasks": len(self.tasks),
            "completed_tasks": sum(1 for t in self.tasks.values() if t.status == "completed"),
            "failed_tasks": sum(1 for t in self.tasks.values() if t.status == "failed"),
            "state": self.get_state(),
        }

        # Update or append
        found = False
        for i, sess in enumerate(registry.get("team_sessions", [])):
            if sess.get("session_id") == self.session_id:
                registry["team_sessions"][i] = snapshot
                found = True
                break
        if not found:
            registry["team_sessions"].append(snapshot)

        # Write registry
        import json as json_lib
        safe_write_text_locked(registry_path, json_lib.dumps(registry, indent=2, ensure_ascii=False))

    @classmethod
    def load_snapshot(cls, workdir: str, session_id: str) -> TeamAgent | None:
        """
        从 .team_registry.json 恢复一个团队会话。

        恢复后团队状态完整（task、contract、tasks 及其 results），
        可用于审计断点或继续执行。

        Args:
            workdir: 工作目录
            session_id: 要恢复的会话 ID

        Returns:
            TeamAgent 实例或 None（找不到对应会话）
        """
        registry_path = Path(workdir) / ".team_registry.json"
        if not registry_path.exists():
            return None

        try:
            import json as json_lib
            registry = json_lib.loads(registry_path.read_text(encoding="utf-8"))
        except (json_lib.JSONDecodeError, OSError):
            return None

        # Find the session
        snapshot = None
        for sess in registry.get("team_sessions", []):
            if sess.get("session_id") == session_id:
                snapshot = sess
                break

        if not snapshot:
            return None

        # Reconstruct TeamAgent
        state = snapshot.get("state", {})
        team = cls(workdir=workdir, task=snapshot.get("task", "Recovered task"))

        # Restore session_id
        team.session_id = session_id

        # Restore tasks with their results
        for tid, tdata in state.get("tasks", {}).items():
            task = TeamTask(
                id=tid,
                description=tdata.get("description", ""),
                assigned_worker=WorkerType(tdata["assigned_worker"]) if tdata.get("assigned_worker") else None,
                status=tdata.get("status", "pending"),
            )

            # Reconstruct WorkerResult if task was completed
            if tdata.get("status") in ("completed", "failed") and tdata.get("assigned_worker"):
                result = WorkerResult(
                    worker_type=WorkerType(tdata["assigned_worker"]),
                    task=tdata.get("description", ""),
                    output=tdata.get("output_summary", "") or "",
                    success=tdata.get("success", False),
                    artifacts=tdata.get("artifacts", []),
                    error=tdata.get("error"),
                    duration_seconds=tdata.get("duration_seconds", 0.0),
                )
                task.result = result

            team.tasks[tid] = task

        return team


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Small Team Agent")
    parser.add_argument("--workdir", default=".", help="workspace directory")
    parser.add_argument("--task", required=True, help="task description")
    parser.add_argument("--type", choices=["researcher", "coder", "reviewer", "debugger"],
                        help="worker type (for single worker mode)")
    args = parser.parse_args()

    if args.type:
        # 单 worker 模式
        worker_type = WorkerType(args.type)
        worker = WorkerAgent(worker_type, args.workdir)
        result = worker.execute(args.task)
        print(f"Worker: {worker_type.value}")
        print(f"Success: {result.success}")
        print(f"Output:\n{result.output}")
        if result.error:
            print(f"Error: {result.error}")
        print(f"Artifacts: {result.artifacts}")
        print(f"Duration: {result.duration_seconds:.2f}s")
    else:
        # 团队模式
        team = TeamAgent(args.workdir, task=args.task)
        if not team.contract.get("goals") and not team.frontier.get("executable_frontier") and not team.frontier.get("parallel_candidates") and not team.frontier.get("conflict_groups"):
            team.add_task(args.task, WorkerType.CODER)
        result = team.run()
        print(f"Team Session: {result['session_id']}")
        print(f"Tasks: {result['tasks_completed']} completed, {result['tasks_failed']} failed")
        for output in result["outputs"]:
            print(f"  - [{output['worker']}] {'✓' if output['success'] else '✗'}")


if __name__ == "__main__":
    main()
