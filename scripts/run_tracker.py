#!/usr/bin/env python3
"""
Run Tracker - 执行追踪工具

追踪每次执行的统计数据：
- steps, tokens, duration
- success/failure
- task category

用法:
    python run_tracker.py --op=start --run-id=R001 --category=DEBUGGING
    python run_tracker.py --op=record --run-id=R001 --step=THINKING --tokens=1500
    python run_tracker.py --op=finish --run-id=R001 --status=success
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

# 默认追踪文件
DEFAULT_TRACKER_FILE = ".run_tracker.json"


def _validate_path(path: str) -> bool:
    """验证路径安全（防止路径遍历攻击）"""
    try:
        real_path = os.path.realpath(path)
        if os.path.isabs(path):
            return True
        cwd = os.getcwd()
        return real_path.startswith(cwd)
    except OSError:
        return False


def load_tracker(path: str = DEFAULT_TRACKER_FILE) -> Dict:
    """加载追踪数据"""
    if not _validate_path(path):
        return {"runs": [], "version": "1.0"}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"runs": [], "version": "1.0"}


def save_tracker(path: str, data: Dict) -> None:
    """保存追踪数据"""
    if not _validate_path(path):
        return
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def start_run(run_id: str, task_category: str, description: str = "",
              path: str = DEFAULT_TRACKER_FILE) -> bool:
    """开始一次执行追踪"""
    tracker = load_tracker(path)

    # 检查是否已存在
    for run in tracker.get("runs", []):
        if run["run_id"] == run_id and run.get("status") == "running":
            print(f"Run {run_id} 已在运行中")
            return False

    run = {
        "run_id": run_id,
        "category": task_category,
        "description": description,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "steps": [],
        "total_tokens": 0,
        "total_errors": 0,
        "duration_ms": None,
        "success": None
    }

    if "runs" not in tracker:
        tracker["runs"] = []
    tracker["runs"].append(run)
    save_tracker(path, tracker)

    print(f"开始追踪: {run_id} [{task_category}]")
    return True


def record_step(run_id: str, step_name: str, tokens: int = 0,
                error: bool = False, path: str = DEFAULT_TRACKER_FILE) -> bool:
    """记录单个 step"""
    tracker = load_tracker(path)

    for run in tracker.get("runs", []):
        if run["run_id"] == run_id:
            step_record = {
                "step": step_name,
                "tokens": tokens,
                "error": error,
                "recorded_at": datetime.now().isoformat()
            }
            run["steps"].append(step_record)
            run["total_tokens"] += tokens
            if error:
                run["total_errors"] += 1
            save_tracker(path, tracker)
            print(f"记录 step: {run_id}/{step_name} (+{tokens} tokens)")
            return True

    print(f"Run {run_id} 未找到")
    return False


def finish_run(run_id: str, success: bool, path: str = DEFAULT_TRACKER_FILE) -> Dict:
    """结束执行追踪"""
    tracker = load_tracker(path)

    for run in tracker.get("runs", []):
        if run["run_id"] == run_id:
            run["status"] = "completed"
            run["finished_at"] = datetime.now().isoformat()
            run["success"] = success

            # 计算 duration
            if run.get("started_at"):
                started = datetime.fromisoformat(run["started_at"])
                finished = datetime.fromisoformat(run["finished_at"])
                run["duration_ms"] = int((finished - started).total_seconds() * 1000)

            save_tracker(path, tracker)

            # 打印摘要
            duration = run.get("duration_ms", 0) / 1000
            print(f"\n{'='*50}")
            print(f"Run {run_id} 已完成")
            print(f"  状态: {'✅ 成功' if success else '❌ 失败'}")
            print(f"  耗时: {duration:.1f}s")
            print(f"  Steps: {len(run['steps'])}")
            print(f"  Tokens: {run['total_tokens']}")
            print(f"  Errors: {run['total_errors']}")
            print(f"{'='*50}\n")

            return run

    print(f"Run {run_id} 未找到")
    return {}


def get_run_stats(run_id: str = None, path: str = DEFAULT_TRACKER_FILE) -> Dict:
    """获取执行统计"""
    tracker = load_tracker(path)

    if run_id:
        for run in tracker.get("runs", []):
            if run["run_id"] == run_id:
                return run
        return {"error": f"Run {run_id} 未找到"}

    # 汇总统计
    runs = tracker.get("runs", [])
    completed = [r for r in runs if r.get("status") == "completed"]

    total = len(completed)
    success = len([r for r in completed if r.get("success")])
    total_tokens = sum(r.get("total_tokens", 0) for r in completed)
    total_duration = sum(r.get("duration_ms", 0) for r in completed)

    return {
        "total_runs": total,
        "success_count": success,
        "success_rate": success / total if total > 0 else 0,
        "total_tokens": total_tokens,
        "avg_tokens": total_tokens / total if total > 0 else 0,
        "total_duration_s": total_duration / 1000 if total_duration > 0 else 0,
        "avg_duration_s": (total_duration / total) / 1000 if total > 0 else 0
    }


def main():
    parser = argparse.ArgumentParser(description='Run Tracker - 执行追踪工具')
    parser.add_argument('--path', default=DEFAULT_TRACKER_FILE, help='追踪文件路径')
    parser.add_argument('--op', choices=['start', 'step', 'finish', 'stats'],
                       required=True, help='操作类型')
    parser.add_argument('--run-id', '--run_id', dest='run_id', help='Run ID')
    parser.add_argument('--category', help='任务类别')
    parser.add_argument('--desc', help='任务描述')
    parser.add_argument('--step', help='Step 名称')
    parser.add_argument('--tokens', type=int, default=0, help='Token 数量')
    parser.add_argument('--error', action='store_true', help='是否出错')
    parser.add_argument('--status', choices=['success', 'failure'], help='执行状态')

    args = parser.parse_args()

    if args.op == 'start':
        if not args.run_id or not args.category:
            print("错误: --run-id 和 --category 必须指定")
            return 1
        start_run(args.run_id, args.category, args.desc or "", args.path)

    elif args.op == 'step':
        if not args.run_id or not args.step:
            print("错误: --run-id 和 --step 必须指定")
            return 1
        record_step(args.run_id, args.step, args.tokens, args.error, args.path)

    elif args.op == 'finish':
        if not args.run_id:
            print("错误: --run-id 必须指定")
            return 1
        success = args.status == 'success'
        finish_run(args.run_id, success, args.path)

    elif args.op == 'stats':
        stats = get_run_stats(args.run_id, args.path)
        print(json.dumps(stats, ensure_ascii=False, indent=2))

    return 0


if __name__ == '__main__':
    sys.exit(main())
