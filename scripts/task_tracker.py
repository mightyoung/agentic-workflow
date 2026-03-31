#!/usr/bin/env python3
"""
Task Tracker - 任务状态追踪工具

追踪任务进度、状态变更、问题记录：
- 创建任务
- 更新状态
- 记录问题
- 生成进度报告

用法:
    python task_tracker.py --op=create --task-id=T001 --desc="任务描述"
    python task_tracker.py --op=status --task-id=T001 --status=in_progress
    python task_tracker.py --op=report
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, List

from safe_io import safe_write_json

# 默认任务状态文件
DEFAULT_TRACKER_FILE = ".task_tracker.json"


def _validate_path(path: str) -> bool:
    """验证路径安全（防止路径遍历攻击）"""
    try:
        # 解析符号链接，获取真实路径
        real_path = os.path.realpath(path)
        # 允许绝对路径（用户明确指定的位置，如临时文件）
        # 只阻止使用 .. 进行遍历的相对路径
        if os.path.isabs(path):
            return True
        # 相对路径：检查解析后是否在当前目录内
        cwd = os.getcwd()
        return real_path.startswith(cwd)
    except OSError:
        return False


def load_tracker(path: str) -> Dict:
    """加载任务追踪数据（带旧数据迁移）"""
    if not _validate_path(path):
        return {"tasks": [], "version": "1.0", "created": datetime.now().isoformat()}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        return {"tasks": [], "version": "1.0", "created": datetime.now().isoformat()}

    # 迁移旧任务数据（v4.8新增字段）
    for task in data.get("tasks", []):
        if "budget_seconds" not in task:
            task["budget_seconds"] = 300
        if "time_spent_seconds" not in task:
            task["time_spent_seconds"] = 0
        if "started_at" not in task:
            task["started_at"] = None
        if "quality_gates_passed" not in task:
            task["quality_gates_passed"] = None
        if "step_failures" not in task:
            task["step_failures"] = {}  # {"step_name": count}

    return data


def save_tracker(path: str, data: Dict) -> None:
    """保存任务追踪数据"""
    if not _validate_path(path):
        return
    safe_write_json(path, data)


def create_task(task_id: str, description: str, priority: str = "P2",
                dependencies: Optional[List[str]] = None, path: str = DEFAULT_TRACKER_FILE,
                budget_seconds: int = 300) -> bool:
    """创建新任务（带预算控制）"""
    tracker = load_tracker(path)

    # 检查是否已存在
    for task in tracker["tasks"]:
        if task["id"] == task_id:
            print(f"任务已存在: {task_id}")
            return False

    task = {
        "id": task_id,
        "description": description,
        "status": "pending",
        "priority": priority,
        "dependencies": dependencies or [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "progress": 0,
        "issues": [],
        # 预算控制字段 (v4.8新增)
        "budget_seconds": budget_seconds,      # 预算时间（秒）
        "time_spent_seconds": 0,                # 已消耗时间
        "started_at": None,                      # 开始时间
        "quality_gates_passed": None,           # 质量门禁状态
        "step_failures": {},                    # 断路器：步骤失败计数 {"step_name": count}
    }

    tracker["tasks"].append(task)
    save_tracker(path, tracker)

    print(f"已创建任务: {task_id} - {description} (预算: {budget_seconds}s)")
    return True


def start_task(task_id: str, path: str = DEFAULT_TRACKER_FILE) -> bool:
    """开始任务计时"""
    tracker = load_tracker(path)

    for task in tracker["tasks"]:
        if task["id"] == task_id:
            if task["started_at"] is None:
                task["started_at"] = datetime.now().isoformat()
                task["status"] = "in_progress"
                task["updated_at"] = datetime.now().isoformat()
                save_tracker(path, tracker)
                print(f"任务已开始: {task_id}")
                return True
            else:
                print(f"任务已在进行中: {task_id}")
                return False

    print(f"任务未找到: {task_id}")
    return False


def check_task_budget(task_id: str, path: str = DEFAULT_TRACKER_FILE) -> dict:
    """检查任务预算状态"""
    tracker = load_tracker(path)

    for task in tracker["tasks"]:
        if task["id"] == task_id:
            if task["started_at"] is None:
                return {
                    "task_id": task_id,
                    "started": False,
                    "budget_seconds": task.get("budget_seconds", 300),
                    "time_spent_seconds": 0,
                    "over_budget": False
                }

            started = datetime.fromisoformat(task["started_at"])
            elapsed = (datetime.now() - started).total_seconds()
            budget = task.get("budget_seconds", 300)
            over_budget = elapsed > budget

            return {
                "task_id": task_id,
                "started": True,
                "started_at": task["started_at"],
                "budget_seconds": budget,
                "time_spent_seconds": int(elapsed),
                "remaining_seconds": max(0, budget - int(elapsed)),
                "over_budget": over_budget,
                "budget_percent": min(100, int(elapsed / budget * 100)) if budget > 0 else 0
            }

    return {"error": f"任务未找到: {task_id}"}


def update_quality_gate(task_id: str, passed: bool, path: str = DEFAULT_TRACKER_FILE) -> bool:
    """更新任务质量门禁状态"""
    tracker = load_tracker(path)

    for task in tracker["tasks"]:
        if task["id"] == task_id:
            task["quality_gates_passed"] = passed
            task["updated_at"] = datetime.now().isoformat()
            save_tracker(path, tracker)
            status = "通过" if passed else "未通过"
            print(f"质量门禁更新: {task_id} -> {status}")
            return True

    print(f"任务未找到: {task_id}")
    return False


def record_step_failure(task_id: str, step_name: str, threshold: int = 3,
                        path: str = DEFAULT_TRACKER_FILE) -> dict:
    """
    记录步骤失败并检查是否应触发断路器

    Returns:
        {"tripped": True/False, "count": N, "step": step_name}
    """
    tracker = load_tracker(path)

    for task in tracker["tasks"]:
        if task["id"] == task_id:
            if "step_failures" not in task:
                task["step_failures"] = {}

            current_count = task["step_failures"].get(step_name, 0)
            new_count = current_count + 1
            task["step_failures"][step_name] = new_count
            task["updated_at"] = datetime.now().isoformat()
            save_tracker(path, tracker)

            tripped = new_count >= threshold

            if tripped:
                print("╔══════════════════════════════════════╗")
                print("║ ⚠️  断路器触发                        ║")
                print("╠══════════════════════════════════════╣")
                print(f"║ 任务: {task_id:<32} ║")
                print(f"║ 步骤: {step_name:<32} ║")
                print(f"║ 失败次数: {new_count:<27} ║")
                print("╠══════════════════════════════════════╣")
                print("║ [1] 换方案继续                       ║")
                print("║ [2] 寻求帮助                         ║")
                print("║ [3] 中止任务                         ║")
                print("╚══════════════════════════════════════╝")
            else:
                print(f"记录失败: {task_id}/{step_name} (当前: {new_count}/{threshold})")

            return {"tripped": tripped, "count": new_count, "step": step_name}

    return {"tripped": False, "count": 0, "step": step_name, "error": f"任务未找到: {task_id}"}


def check_circuit_state(task_id: str, step_name: Optional[str] = None,
                        path: str = DEFAULT_TRACKER_FILE) -> dict:
    """检查指定步骤的断路器状态"""
    tracker = load_tracker(path)

    for task in tracker["tasks"]:
        if task["id"] == task_id:
            step_failures = task.get("step_failures", {})

            if step_name is None:
                # 返回所有步骤的状态
                return {
                    "task_id": task_id,
                    "steps": step_failures
                }

            count = step_failures.get(step_name, 0)
            return {
                "task_id": task_id,
                "step": step_name,
                "failure_count": count,
                "circuit_open": count >= 3
            }

    return {"error": f"任务未找到: {task_id}"}


def reset_circuit(task_id: str, step_name: Optional[str] = None,
                  path: str = DEFAULT_TRACKER_FILE) -> bool:
    """重置断路器。可指定步骤或全部重置"""
    tracker = load_tracker(path)

    for task in tracker["tasks"]:
        if task["id"] == task_id:
            if step_name is None:
                # 重置所有步骤
                task["step_failures"] = {}
                save_tracker(path, tracker)
                print(f"已重置任务 {task_id} 的所有断路器")
                return True
            else:
                # 重置指定步骤
                if step_name in task.get("step_failures", {}):
                    del task["step_failures"][step_name]
                    save_tracker(path, tracker)
                    print(f"已重置断路器: {task_id}/{step_name}")
                    return True
                else:
                    print(f"断路器未激活: {task_id}/{step_name}")
                    return False

    print(f"任务未找到: {task_id}")
    return False


def update_status(task_id: str, status: str, progress: Optional[int] = None,
                  path: str = DEFAULT_TRACKER_FILE) -> bool:
    """更新任务状态"""
    tracker = load_tracker(path)

    for task in tracker["tasks"]:
        if task["id"] == task_id:
            task["status"] = status
            task["updated_at"] = datetime.now().isoformat()
            if progress is not None:
                task["progress"] = progress
            save_tracker(path, tracker)
            print(f"已更新任务状态: {task_id} -> {status} ({progress or task['progress']}%)")
            return True

    print(f"任务未找到: {task_id}")
    return False


def add_issue(task_id: str, issue: str, solution: str = "",
              path: str = DEFAULT_TRACKER_FILE) -> bool:
    """添加问题记录"""
    tracker = load_tracker(path)

    for task in tracker["tasks"]:
        if task["id"] == task_id:
            issue_record = {
                "description": issue,
                "solution": solution,
                "attempts": 0,
                "timestamp": datetime.now().isoformat()
            }
            task["issues"].append(issue_record)
            task["updated_at"] = datetime.now().isoformat()
            save_tracker(path, tracker)
            print(f"已添加问题到任务 {task_id}: {issue}")
            return True

    print(f"任务未找到: {task_id}")
    return False


def get_task(task_id: str, path: str = DEFAULT_TRACKER_FILE) -> Optional[Dict]:
    """获取任务详情"""
    tracker = load_tracker(path)

    for task in tracker["tasks"]:
        if task["id"] == task_id:
            return task

    return None


def list_tasks(status: Optional[str] = None, path: str = DEFAULT_TRACKER_FILE) -> List[Dict]:
    """列出任务"""
    tracker = load_tracker(path)

    if status:
        return [t for t in tracker["tasks"] if t["status"] == status]
    return tracker["tasks"]


def generate_report(path: str = DEFAULT_TRACKER_FILE) -> str:
    """生成进度报告"""
    tracker = load_tracker(path)

    if not tracker["tasks"]:
        return "暂无任务记录"

    # 统计
    total = len(tracker["tasks"])
    pending = sum(1 for t in tracker["tasks"] if t["status"] == "pending")
    in_progress = sum(1 for t in tracker["tasks"] if t["status"] == "in_progress")
    completed = sum(1 for t in tracker["tasks"] if t["status"] == "completed")
    blocked = sum(1 for t in tracker["tasks"] if t["status"] == "blocked")

    # 计算总进度
    total_progress = sum(t["progress"] for t in tracker["tasks"]) / total if total > 0 else 0

    lines = [
        "=" * 60,
        "任务进度报告",
        "=" * 60,
        f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"任务总数: {total}",
        f"总进度: {total_progress:.1f}%",
        "-" * 60,
        f"待处理: {pending} | 进行中: {in_progress} | 已完成: {completed} | 阻塞: {blocked}",
        "-" * 60,
    ]

    # 按状态分组显示
    if in_progress > 0:
        lines.append("\n进行中的任务:")
        for task in tracker["tasks"]:
            if task["status"] == "in_progress":
                lines.append(f"  [{task['id']}] {task['description']} ({task['progress']}%)")

    if blocked > 0:
        lines.append("\n阻塞的任务:")
        for task in tracker["tasks"]:
            if task["status"] == "blocked":
                lines.append(f"  [{task['id']}] {task['description']}")
                if task["issues"]:
                    lines.append(f"       问题: {task['issues'][-1]['description']}")

    if pending > 0:
        lines.append("\n待处理的任务:")
        for task in tracker["tasks"]:
            if task["status"] == "pending":
                lines.append(f"  [{task['id']}] {task['description']} ({task['priority']})")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description='Task Tracker - 任务状态追踪工具')
    parser.add_argument('--path', default=DEFAULT_TRACKER_FILE, help='追踪文件路径')
    parser.add_argument('--op', choices=['create', 'status', 'issue', 'get', 'list', 'report', 'start', 'budget', 'quality-gate', 'step-failure', 'circuit-check', 'circuit-reset'],
                       required=True, help='操作类型')
    parser.add_argument('--task-id', help='任务ID')
    parser.add_argument('--desc', help='任务描述')
    parser.add_argument('--status', help='任务状态 (pending/in_progress/completed/blocked)')
    parser.add_argument('--progress', type=int, help='进度百分比')
    parser.add_argument('--priority', default='P2', help='优先级 (P0/P1/P2/P3)')
    parser.add_argument('--deps', nargs='*', help='依赖任务ID')
    parser.add_argument('--issue', help='问题描述')
    parser.add_argument('--solution', help='解决方案')
    parser.add_argument('--budget-seconds', type=int, default=300, help='预算时间（秒，默认300）')
    parser.add_argument('--passed', type=lambda x: x.lower() == 'true', default=True, help='质量门禁是否通过')
    parser.add_argument('--step', help='步骤名称（用于断路器操作）')
    parser.add_argument('--threshold', type=int, default=3, help='断路器阈值（默认3）')

    args = parser.parse_args()

    if args.op == 'create':
        if not args.task_id or not args.desc:
            print("错误: --task-id 和 --desc 必须指定")
            return 1
        create_task(args.task_id, args.desc, args.priority, args.deps, args.path, args.budget_seconds)

    elif args.op == 'start':
        if not args.task_id:
            print("错误: --task-id 必须指定")
            return 1
        start_task(args.task_id, args.path)

    elif args.op == 'budget':
        if not args.task_id:
            print("错误: --task-id 必须指定")
            return 1
        result = check_task_budget(args.task_id, args.path)
        if "error" in result:
            print(result["error"])
        else:
            print(f"任务: {result['task_id']}")
            print(f"  开始时间: {result.get('started_at', 'N/A')}")
            print(f"  预算: {result['budget_seconds']}s")
            print(f"  已用: {result['time_spent_seconds']}s")
            print(f"  剩余: {result.get('remaining_seconds', 'N/A')}s")
            print(f"  进度: {result.get('budget_percent', 0)}%")
            if result.get('over_budget'):
                print("  ⚠️ 已超出预算!")

    elif args.op == 'quality-gate':
        if not args.task_id:
            print("错误: --task-id 必须指定")
            return 1
        update_quality_gate(args.task_id, args.passed, args.path)

    elif args.op == 'status':
        if not args.task_id or not args.status:
            print("错误: --task-id 和 --status 必须指定")
            return 1
        update_status(args.task_id, args.status, args.progress, args.path)

    elif args.op == 'issue':
        if not args.task_id or not args.issue:
            print("错误: --task-id 和 --issue 必须指定")
            return 1
        add_issue(args.task_id, args.issue, args.solution or "", args.path)

    elif args.op == 'get':
        if not args.task_id:
            print("错误: --task-id 必须指定")
            return 1
        task = get_task(args.task_id, args.path)
        if task:
            print(json.dumps(task, ensure_ascii=False, indent=2))
        else:
            print(f"任务未找到: {args.task_id}")

    elif args.op == 'list':
        tasks = list_tasks(args.status, args.path)
        if tasks:
            for task in tasks:
                print(f"[{task['id']}] {task['description']} - {task['status']} ({task['progress']}%)")
        else:
            print("暂无任务")

    elif args.op == 'report':
        print(generate_report(args.path))

    elif args.op == 'step-failure':
        if not args.task_id or not args.step:
            print("错误: --task-id 和 --step 必须指定")
            return 1
        record_step_failure(args.task_id, args.step, args.threshold, args.path)

    elif args.op == 'circuit-check':
        if not args.task_id:
            print("错误: --task-id 必须指定")
            return 1
        result = check_circuit_state(args.task_id, args.step, args.path)
        if "error" in result:
            print(result["error"])
        else:
            if args.step:
                print(f"任务: {result['task_id']}")
                print(f"  步骤: {result['step']}")
                print(f"  失败次数: {result['failure_count']}")
                print(f"  断路器状态: {'开启' if result['circuit_open'] else '关闭'}")
            else:
                print(f"任务: {result['task_id']}")
                if result['steps']:
                    print("  步骤失败情况:")
                    for step, count in result['steps'].items():
                        status = "开启" if count >= 3 else "关闭"
                        print(f"    {step}: {count}次 ({status})")
                else:
                    print("  无失败记录")

    elif args.op == 'circuit-reset':
        if not args.task_id:
            print("错误: --task-id 必须指定")
            return 1
        reset_circuit(args.task_id, args.step, args.path)

    return 0


if __name__ == '__main__':
    sys.exit(main())
