#!/usr/bin/env python3
"""
Step Recorder - Phase 执行记录器

记录每个 phase 的执行情况：
- phase 名称
- 开始/结束时间
- 输入/输出 tokens
- 状态

用法:
    python step_recorder.py --op=start --run-id=R001 --phase=THINKING
    python step_recorder.py --op=end --run-id=R001 --phase=THINKING --output-tokens=500
    python step_recorder.py --op=report --run-id=R001
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict

from safe_io import safe_write_json

# 默认记录文件
DEFAULT_STEP_FILE = ".step_records.json"


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


def load_records(path: str = DEFAULT_STEP_FILE) -> Dict:
    """加载记录数据"""
    if not _validate_path(path):
        return {"records": []}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    return {"records": []}


def save_records(path: str, data: Dict) -> None:
    """保存记录数据"""
    if not _validate_path(path):
        return
    safe_write_json(path, data)


# Phase 持续时间基准（秒）
PHASE_BENCHMARKS = {
    "ROUTER": 1,
    "OFFICE-HOURS": 60,
    "EXPLORING": 120,
    "RESEARCH": 180,
    "THINKING": 120,
    "PLANNING": 90,
    "EXECUTING": 300,
    "REVIEWING": 120,
    "DEBUGGING": 180,
    "REFINING": 120,
    "COMPLETE": 30
}


def start_phase(run_id: str, phase: str, input_tokens: int = 0,
                path: str = DEFAULT_STEP_FILE) -> bool:
    """开始一个 phase"""
    records = load_records(path)

    record = {
        "run_id": run_id,
        "phase": phase,
        "input_tokens": input_tokens,
        "output_tokens": 0,
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "duration_ms": None,
        "status": "running",
        "error": None
    }

    records["records"].append(record)
    save_records(path, records)

    print(f"Phase 开始: {run_id}/{phase} (+{input_tokens} input tokens)")
    return True


def end_phase(run_id: str, phase: str, output_tokens: int = 0,
              error: Optional[str] = None,
              path: str = DEFAULT_STEP_FILE) -> bool:
    """结束一个 phase"""
    records = load_records(path)

    # 找到最后一个匹配的 running phase
    for record in reversed(records.get("records", [])):
        if (record["run_id"] == run_id and
            record["phase"] == phase and
            record["status"] == "running"):

            record["output_tokens"] = output_tokens
            record["finished_at"] = datetime.now().isoformat()
            record["status"] = "completed" if not error else "failed"
            record["error"] = error

            # 计算 duration
            if record.get("started_at"):
                started = datetime.fromisoformat(record["started_at"])
                finished = datetime.fromisoformat(record["finished_at"])
                record["duration_ms"] = int((finished - started).total_seconds() * 1000)

            save_records(path, records)

            duration = record.get("duration_ms", 0) / 1000
            benchmark = PHASE_BENCHMARKS.get(phase, 60)
            efficiency = min(1.0, benchmark / duration) if duration > 0 else 0

            print(f"Phase 结束: {run_id}/{phase}")
            print(f"  耗时: {duration:.1f}s (基准: {benchmark}s)")
            print(f"  Tokens: {record['input_tokens']} in / {output_tokens} out")
            print(f"  效率: {efficiency:.1%}")
            if error:
                print(f"  错误: {error}")

            return True

    print(f"未找到运行中的 phase: {run_id}/{phase}")
    return False


def get_phase_report(run_id: str, path: str = DEFAULT_STEP_FILE) -> Dict:
    """获取 phase 执行报告"""
    records = load_records(path)

    run_records = [r for r in records.get("records", []) if r["run_id"] == run_id]

    if not run_records:
        return {"error": f"Run {run_id} 无记录"}

    total_duration = sum(r.get("duration_ms", 0) for r in run_records)
    total_input = sum(r.get("input_tokens", 0) for r in run_records)
    total_output = sum(r.get("output_tokens", 0) for r in run_records)
    failed = len([r for r in run_records if r.get("status") == "failed"])

    phases = []
    for r in run_records:
        phases.append({
            "phase": r["phase"],
            "duration_s": r.get("duration_ms", 0) / 1000,
            "input_tokens": r.get("input_tokens", 0),
            "output_tokens": r.get("output_tokens", 0),
            "status": r.get("status"),
            "error": r.get("error")
        })

    return {
        "run_id": run_id,
        "total_phases": len(run_records),
        "total_duration_s": total_duration / 1000,
        "total_tokens": total_input + total_output,
        "failed_phases": failed,
        "phases": phases
    }


def main():
    parser = argparse.ArgumentParser(description='Step Recorder - Phase 执行记录器')
    parser.add_argument('--path', default=DEFAULT_STEP_FILE, help='记录文件路径')
    parser.add_argument('--op', choices=['start', 'end', 'report'],
                       required=True, help='操作类型')
    parser.add_argument('--run-id', '--run_id', dest='run_id', help='Run ID')
    parser.add_argument('--phase', help='Phase 名称')
    parser.add_argument('--input-tokens', type=int, default=0, help='输入 tokens')
    parser.add_argument('--output-tokens', type=int, default=0, help='输出 tokens')
    parser.add_argument('--error', help='错误信息')

    args = parser.parse_args()

    if args.op == 'start':
        if not args.run_id or not args.phase:
            print("错误: --run-id 和 --phase 必须指定")
            return 1
        start_phase(args.run_id, args.phase, args.input_tokens, args.path)

    elif args.op == 'end':
        if not args.run_id or not args.phase:
            print("错误: --run-id 和 --phase 必须指定")
            return 1
        end_phase(args.run_id, args.phase, args.output_tokens,
                  args.error, args.path)

    elif args.op == 'report':
        if not args.run_id:
            print("错误: --run-id 必须指定")
            return 1
        report = get_phase_report(args.run_id, args.path)
        print(json.dumps(report, ensure_ascii=False, indent=2))

    return 0


if __name__ == '__main__':
    sys.exit(main())
