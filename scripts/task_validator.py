"""
Task plan validation and status update helpers.

Provides:
- validate_task_plan: check for cycle and missing dependencies
- update_task_status_in_plan: write a new status back to task_plan.md or tasks.md
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from frontier_scheduler import _find_canonical_tasks_path, load_planning_tasks
from safe_io import safe_write_text_locked


def validate_task_plan(workdir: str = ".") -> tuple[bool, list[str]]:
    """
    验证任务计划的合法性

    检查:
    - 循环依赖
    - 缺失的依赖
    - 非法的任务ID引用

    Returns:
        (is_valid, error_list)
    """
    tasks, _source = load_planning_tasks(workdir)
    if not tasks:
        return True, []

    errors = []
    task_ids = {t["id"] for t in tasks}
    task_map = {t["id"]: t for t in tasks}

    for task in tasks:
        deps = task.get("dependencies", [])
        for dep in deps:
            if dep not in task_ids:
                errors.append(f"Task {task['id']} depends on non-existent task {dep}")

    # 检查循环依赖 (简单的 DFS)
    def has_cycle(task_id: str, visited: set, rec_stack: set) -> bool:
        visited.add(task_id)
        rec_stack.add(task_id)
        for dep in task_map.get(task_id, {}).get("dependencies", []):
            if dep not in visited:
                if has_cycle(dep, visited, rec_stack):
                    return True
            elif dep in rec_stack:
                return True
        rec_stack.remove(task_id)
        return False

    for task in tasks:
        if task["id"] not in task_ids:
            continue
        if has_cycle(task["id"], set(), set()):
            errors.append(f"Circular dependency detected involving {task['id']}")

    return len(errors) == 0, errors


def update_task_status_in_plan(
    workdir: str,
    task_id: str,
    status: str,
) -> dict[str, Any]:
    """
    更新 task_plan.md 中任务的状态

    Args:
        workdir: 工作目录
        task_id: 任务ID (如 "TASK-001")
        status: 新状态 (backlog | in_progress | completed | blocked)

    Returns:
        更新结果
    """
    if status not in ("backlog", "in_progress", "completed", "blocked"):
        return {"success": False, "error": f"Invalid status: {status}"}

    plan_path = _find_canonical_tasks_path(workdir)
    source = "tasks.md"
    if plan_path is None:
        plan_path = Path(workdir) / "task_plan.md"
        source = "task_plan.md"

    if not plan_path.exists():
        return {"success": False, "error": "task_plan.md not found"}

    content = plan_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    new_lines: list[str] = []
    task_found = False
    in_target_task = False

    legacy_task_pattern = re.compile(r"^- \[(?P<done>[ xX])\] (?P<id>TASK-\d+): (?P<title>.+)$")
    canonical_task_pattern = re.compile(r"^- \[(?P<done>[ xX])\] \*\*(?P<id>[^:]+):\*\* (?P<title>.+)$")
    status_pattern = re.compile(r"^\s+- \*\*Status:\*\*")

    task_pattern = canonical_task_pattern if source == "tasks.md" else legacy_task_pattern

    for line in lines:
        line_stripped = line.rstrip()
        task_match = task_pattern.match(line_stripped)
        if task_match:
            in_target_task = task_match.group("id") == task_id
            if in_target_task:
                task_found = True
                done_marker = "x" if status == "completed" else " "
                if source == "tasks.md":
                    task_title = task_match.group("title").rstrip()
                    new_lines.append(f"- [{done_marker}] **{task_match.group('id')}:** {task_title}")
                    new_lines.append(f"  - **Status:** {status}")
                else:
                    task_title = task_match.group("title").rstrip()
                    new_lines.append(f"- [{done_marker}] {task_match.group('id')}: {task_title}")
                continue

        if in_target_task:
            if source == "tasks.md" and status_pattern.match(line_stripped):
                continue
            if source == "task_plan.md":
                field_pattern = re.compile(r"^\s+- (?P<key>[a-zA-Z_]+):")
                field_match = field_pattern.match(line)
                if field_match and field_match.group("key") == "status":
                    new_lines.append(f"  - status: {status}")
                    continue

        new_lines.append(line)

    if not task_found:
        return {"success": False, "error": f"Task {task_id} not found"}

    safe_write_text_locked(plan_path, "\n".join(new_lines))
    return {"success": True, "task_id": task_id, "status": status, "source": source}
