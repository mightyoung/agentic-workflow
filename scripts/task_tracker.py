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
from pathlib import Path
from typing import Optional, Dict, List, Any

# 默认任务状态文件
DEFAULT_TRACKER_FILE = ".task_tracker.json"


def load_tracker(path: str) -> Dict:
    """加载任务追踪数据"""
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"tasks": [], "version": "1.0", "created": datetime.now().isoformat()}


def save_tracker(path: str, data: Dict) -> None:
    """保存任务追踪数据"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_task(task_id: str, description: str, priority: str = "P2",
                dependencies: List[str] = None, path: str = DEFAULT_TRACKER_FILE) -> bool:
    """创建新任务"""
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
        "issues": []
    }

    tracker["tasks"].append(task)
    save_tracker(path, tracker)

    print(f"已创建任务: {task_id} - {description}")
    return True


def update_status(task_id: str, status: str, progress: int = None,
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


def list_tasks(status: str = None, path: str = DEFAULT_TRACKER_FILE) -> List[Dict]:
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
    parser.add_argument('--op', choices=['create', 'status', 'issue', 'get', 'list', 'report'],
                       required=True, help='操作类型')
    parser.add_argument('--task-id', help='任务ID')
    parser.add_argument('--desc', help='任务描述')
    parser.add_argument('--status', help='任务状态 (pending/in_progress/completed/blocked)')
    parser.add_argument('--progress', type=int, help='进度百分比')
    parser.add_argument('--priority', default='P2', help='优先级 (P0/P1/P2/P3)')
    parser.add_argument('--deps', nargs='*', help='依赖任务ID')
    parser.add_argument('--issue', help='问题描述')
    parser.add_argument('--solution', help='解决方案')

    args = parser.parse_args()

    if args.op == 'create':
        if not args.task_id or not args.desc:
            print("错误: --task-id 和 --desc 必须指定")
            return 1
        create_task(args.task_id, args.desc, args.priority, args.deps, args.path)

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

    return 0


if __name__ == '__main__':
    sys.exit(main())
