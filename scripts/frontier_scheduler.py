"""
Frontier scheduler: task plan parsing and checkpoint helpers.

Provides:
- parse_task_plan: parse task_plan.md into structured task list
- parse_tasks_md: parse .specs/<feature_id>/tasks.md
- load_planning_tasks: load tasks preferring spec-kit format
- _find_canonical_tasks_path: locate the canonical tasks.md
- next_plan_tasks: return next tasks ordered by priority
- compute_frontier: compute executable task frontier
- CheckpointConfig: dataclass for checkpoint thresholds
- should_checkpoint: decide if a checkpoint is needed
- conditional_checkpoint: save checkpoint if conditions met
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def parse_task_plan(workdir: str = ".") -> list[dict[str, Any]]:
    """
    解析 task_plan.md 为结构化任务列表

    支持的字段:
    - id, title, done (从 checkbox 解析)
    - status: backlog | in_progress | completed | blocked
    - priority: P0 | P1 | P2 | P3
    - description: 任务描述
    - owned_files: 逗号分隔的文件列表
    - dependencies: 逗号分隔的任务ID列表
    - verification: 验证命令或方法
    - acceptance: 验收标准
    """
    plan_path = Path(workdir) / "task_plan.md"
    if not plan_path.exists():
        return []

    tasks: list[dict[str, Any]] = []
    current_priority = None
    current_task: dict[str, Any] | None = None
    task_pattern = re.compile(r"^- \[(?P<done>[ xX])\] (?P<id>TASK-\d+): (?P<title>.+)$")
    field_pattern = re.compile(r"^\s+- (?P<key>[a-zA-Z_]+): (?P<value>.+)$")

    for raw_line in plan_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()

        if line.startswith("### P"):
            current_priority = line.replace("###", "").strip()
            continue

        task_match = task_pattern.match(line)
        if task_match:
            is_done = task_match.group("done").lower() == "x"
            current_task = {
                "id": task_match.group("id"),
                "title": task_match.group("title"),
                "done": is_done,
                "priority": current_priority,
                "status": "completed" if is_done else "backlog",
            }
            tasks.append(current_task)
            continue

        field_match = field_pattern.match(line)
        if field_match and current_task is not None:
            key = field_match.group("key")
            value = field_match.group("value")
            # Only set status if checkbox and status disagree, prefer checkbox
            if key == "status" and not current_task.get("done"):
                current_task[key] = value
            elif key == "dependencies":
                current_task[key] = [d.strip() for d in value.split(",") if d.strip()]
            elif key == "owned_files":
                current_task[key] = [f.strip() for f in value.split(",") if f.strip()]
            elif key != "status":  # Skip status if from checkbox
                current_task[key] = value

    return tasks


def parse_tasks_md(workdir: str = ".") -> list[dict[str, Any]]:
    """
    Parse tasks.md (spec-kit style) from .specs/<feature_id>/tasks.md.

    Returns structured tasks with owned_files, dependencies, and verification.

    Supports the format:
    - [ ] **TASK-US1-1:** Title [P]
      - **Files:** `file1.py`, `file2.py`
      - **Verification:** `[P]` pytest tests/ -v
      - **Blocked-By:** TASK-US1-2
    """
    # Find the most recent .specs/<feature_id>/tasks.md
    specs_dir = Path(workdir) / ".specs"
    if not specs_dir.exists():
        return []

    # Get the most recent feature directory
    feature_dirs = sorted(specs_dir.glob("*/"), key=lambda p: p.stat().st_mtime, reverse=True)
    tasks_path = None
    for feature_dir in feature_dirs:
        tp = feature_dir / "tasks.md"
        if tp.exists():
            tasks_path = tp
            break

    if not tasks_path or not tasks_path.exists():
        return []

    tasks: list[dict[str, Any]] = []
    current_section = None

    # Patterns for parsing
    task_pattern = re.compile(r"^- \[(?P<done>[ xX])\] \*\*(?P<id>[^:]+):\*\* (?P<title>.+?)(?:\s+\[P\])?$")
    file_pattern = re.compile(r"\*\*Files:\*\*\s*`?([^`]+)`?")
    verification_pattern = re.compile(r"\*\*Verification:\*\*\s*(?:\[P\]\s*)?([^\n]+)")
    blocked_by_pattern = re.compile(r"\*\*Blocked-By:\*\*\s*([^\n]+)")
    status_pattern = re.compile(r"\*\*Status:\*\*\s*([^\n]+)")
    section_pattern = re.compile(r"^## (.+)$")

    current_task: dict[str, Any] | None = None

    for raw_line in tasks_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()

        # Check for section headers
        section_match = section_pattern.match(line)
        if section_match:
            current_section = section_match.group(1)
            continue

        # Try to match task line
        task_match = task_pattern.match(line)
        if task_match:
            if current_task:
                tasks.append(current_task)

            task_id = task_match.group("id")
            title = task_match.group("title").strip()
            is_done = task_match.group("done").lower() == "x"

            # Determine priority from section or task ID
            priority = "P1"
            if current_section in ("Setup", "Foundational"):
                priority = "P0"
            elif current_section == "Polish":
                priority = "P2"

            current_task = {
                "id": task_id,
                "title": title,
                "status": "completed" if is_done else "backlog",
                "priority": priority,
                "owned_files": [],
                "dependencies": [],
                "verification": "",
                "section": current_section,
            }
            continue

        # Parse fields for current task
        if current_task:
            file_match = file_pattern.search(line)
            if file_match:
                files_str = file_match.group(1)
                current_task["owned_files"] = [f.strip() for f in files_str.split(",")]

            verification_match = verification_pattern.search(line)
            if verification_match:
                current_task["verification"] = verification_match.group(1).strip()

            blocked_match = blocked_by_pattern.search(line)
            if blocked_match:
                deps_str = blocked_match.group(1).strip()
                current_task["dependencies"] = [d.strip() for d in deps_str.split(",")]

            status_match = status_pattern.search(line)
            if status_match:
                current_task["status"] = status_match.group(1).strip()

    if current_task:
        tasks.append(current_task)

    return tasks


def load_planning_tasks(workdir: str = ".") -> tuple[list[dict[str, Any]], str]:
    """
    Load planning tasks, preferring the canonical spec-kit chain.

    Returns:
        (tasks, source_name) where source_name is "tasks.md", "task_plan.md", or "none".
    """
    tasks = parse_tasks_md(workdir)
    if tasks:
        return tasks, "tasks.md"

    legacy_tasks = parse_task_plan(workdir)
    if legacy_tasks:
        return legacy_tasks, "task_plan.md"

    return [], "none"


def _find_canonical_tasks_path(workdir: str = ".") -> Path | None:
    """Find the most recent canonical tasks.md file under .specs/."""
    specs_dir = Path(workdir) / ".specs"
    if not specs_dir.exists():
        return None

    feature_dirs = sorted(specs_dir.glob("*/"), key=lambda p: p.stat().st_mtime, reverse=True)
    for feature_dir in feature_dirs:
        tasks_path = feature_dir / "tasks.md"
        if tasks_path.exists():
            return tasks_path
    return None


def next_plan_tasks(workdir: str = ".", limit: int = 3) -> list[dict[str, Any]]:
    """
    获取下一个应该执行的任务列表

    考虑:
    - 优先级 (P0 > P1 > P2 > P3)
    - 依赖关系 (只有依赖都完成才能开始)
    - 状态 (只选 backlog 的)
    """
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, None: 9}
    # Prefer tasks.md (spec-kit style) over task_plan.md when available
    all_tasks, _source = load_planning_tasks(workdir)
    completed_ids = {t["id"] for t in all_tasks if t.get("status") == "completed"}

    candidates = []
    for task in all_tasks:
        if task.get("status") in ("completed", "in_progress", "blocked"):
            continue

        # 检查依赖是否都满足
        deps = task.get("dependencies", [])
        if deps and not all(d in completed_ids for d in deps):
            continue

        candidates.append(task)

    candidates.sort(key=lambda item: (priority_order.get(item.get("priority"), 9), item.get("id", "")))
    return candidates[:limit]


def compute_frontier(workdir: str = ".") -> dict[str, Any]:
    """
    Compute the executable task frontier from task_plan.md.

    Returns:
        {
            "executable_frontier": [task, ...],     # Tasks ready to execute
            "ready_tasks": [task, ...],            # Alias for executable_frontier
            "parallel_candidates": [[task, task], ...], # Tasks can run in parallel (ownership-safe, parallel-ready)
            "blocked_tasks": [task, ...],           # Tasks blocked by dependencies
            "conflict_groups": [[task, task], ...], # Tasks with overlapping owned_files (must be serialized)
            "completed_count": int,
            "total_count": int,
        }

    Frontier rules:
    - executable_frontier: backlog tasks with all dependencies satisfied
    - parallel_candidates: within frontier, tasks WITHOUT ownership conflicts can run concurrently (parallel-ready, not yet parallel execution)
    - conflict_groups: tasks with overlapping owned_files that must be serialized

    Prefers tasks.md (spec-kit style) over task_plan.md when available for richer owned_files semantics.
    """
    # Prefer tasks.md (spec-kit style) over task_plan.md when available
    all_tasks, source = load_planning_tasks(workdir)
    if not all_tasks:
        return {
            "executable_frontier": [],
            "ready_tasks": [],
            "parallel_candidates": [],
            "blocked_tasks": [],
            "conflict_groups": [],
            "completed_count": 0,
            "total_count": 0,
            "plan_source": "none",
        }

    completed_ids = {t["id"] for t in all_tasks if t.get("status") == "completed"}
    backlog_tasks = [t for t in all_tasks if t.get("status") == "backlog"]

    # Partition into frontier (ready) vs blocked
    frontier_tasks = []
    blocked_tasks = []
    for task in backlog_tasks:
        deps = task.get("dependencies", [])
        if deps and not all(d in completed_ids for d in deps):
            blocked_tasks.append(task)
        else:
            frontier_tasks.append(task)

    # Ownership conflict detection
    # Build a map: file -> [task_ids] that own it
    file_owner_map: dict[str, list[str]] = {}
    for task in frontier_tasks:
        owned = task.get("owned_files", [])
        if isinstance(owned, list):
            for f in owned:
                if f not in file_owner_map:
                    file_owner_map[f] = []
                file_owner_map[f].append(task["id"])

    # Find conflicting task pairs (share owned files)
    conflicts: list[tuple[str, str]] = []
    for _file_path, owners in file_owner_map.items():
        if len(owners) > 1:
            for i in range(len(owners)):
                for j in range(i + 1, len(owners)):
                    pair = (owners[i], owners[j]) if owners[i] < owners[j] else (owners[j], owners[i])
                    if pair not in conflicts:
                        conflicts.append(pair)

    # Build conflict groups
    conflict_graph: dict[str, set] = {}
    for t1, t2 in conflicts:
        if t1 not in conflict_graph:
            conflict_graph[t1] = set()
        if t2 not in conflict_graph:
            conflict_graph[t2] = set()
        conflict_graph[t1].add(t2)
        conflict_graph[t2].add(t1)

    # Find maximal independent sets for parallel execution
    parallel_groups: list[list[dict[str, Any]]] = []
    assigned_ids: set = set()

    # First, assign tasks that have conflicts to conflict_groups (serial execution)
    conflict_groups: list[list[dict[str, Any]]] = []
    for task in frontier_tasks:
        if task["id"] in conflict_graph and task["id"] not in assigned_ids:
            # This task has conflicts, find all its conflict partners
            group = [task]
            assigned_ids.add(task["id"])
            to_check = list(conflict_graph[task["id"]])
            while to_check:
                tid = to_check.pop()
                if tid in assigned_ids:
                    continue
                # Find task object
                t = next((x for x in frontier_tasks if x["id"] == tid), None)
                if t:
                    group.append(t)
                    assigned_ids.add(tid)
                    to_check.extend(conflict_graph.get(tid, []))
            conflict_groups.append(group)

    # Remaining tasks (no conflicts) can run in parallel
    independent_tasks = [t for t in frontier_tasks if t["id"] not in assigned_ids]
    if independent_tasks:
        # Each independent task is its own parallel group
        parallel_groups.extend([[t] for t in independent_tasks])
        for t in independent_tasks:
            assigned_ids.add(t["id"])

    # Handle dependency chains within non-conflicting tasks
    frontier_ids = {t["id"] for t in frontier_tasks}
    dep_graph: dict[str, set] = {}
    for task in frontier_tasks:
        task_deps = task.get("dependencies", [])
        relevant_deps = {d for d in task_deps if d in frontier_ids}
        dep_graph[task["id"]] = relevant_deps

    return {
        "executable_frontier": frontier_tasks,
        "ready_tasks": frontier_tasks,  # Alias
        "parallel_candidates": parallel_groups,
        "blocked_tasks": blocked_tasks,
        "conflict_groups": conflict_groups,
        "completed_count": len(completed_ids),
        "total_count": len(all_tasks),
        "plan_source": source,
    }


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
    # Delegate to checkpoint_manager (imported lazily to avoid circular dependency)
    from checkpoint_manager import should_checkpoint as _impl
    result: tuple[bool, str] = _impl(workdir, config)
    return bool(result[0]), str(result[1])


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
            error: str or None
            partial: bool (True if only JSON was saved, not handoff)
    """
    # Delegate to checkpoint_manager (imported lazily to avoid circular dependency)
    from checkpoint_manager import conditional_checkpoint as _impl
    result: dict[str, Any] = _impl(workdir, config)
    return result
