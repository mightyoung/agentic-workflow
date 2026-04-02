#!/usr/bin/env python3
"""
Pattern Detector - 失败模式检测器

基于 WAL Scanner 增强，检测执行中的失败模式：
- 重复错误模式
- 性能瓶颈
- 建议优化

用法:
    python pattern_detector.py --analyze --run-id=R001
    python pattern_detector.py --detect-failures
"""

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any

from safe_io import safe_write_json

# 默认模式文件
DEFAULT_PATTERNS_FILE = ".failure_patterns.json"


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


def load_patterns(path: str = DEFAULT_PATTERNS_FILE) -> dict:
    """加载失败模式数据"""
    if not _validate_path(path):
        return {"patterns": [], "version": "1.0"}
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    return {"patterns": [], "version": "1.0"}


def save_patterns(path: str, data: dict) -> None:
    """保存失败模式数据"""
    if not _validate_path(path):
        return
    safe_write_json(path, data)


def detect_error_pattern(errors: list[str]) -> dict:
    """检测错误模式

    分析错误列表，识别重复出现的错误模式
    """
    if not errors:
        return {"has_patterns": False}

    error_counter = Counter(errors)
    repeated = {k: v for k, v in error_counter.items() if v >= 2}

    return {
        "has_patterns": len(repeated) > 0,
        "repeated_errors": repeated,
        "total_unique": len(error_counter),
        "recommendation": _generate_recommendation(repeated)
    }


def _generate_recommendation(repeated_errors: dict[str, int]) -> str:
    """根据重复错误生成建议"""
    if not repeated_errors:
        return "无明显重复错误模式"

    top_error = max(repeated_errors.items(), key=lambda x: x[1])

    recommendations = {
        "connection": "检测到连接错误，建议检查网络和超时配置",
        "timeout": "检测到超时错误，建议增加超时时间或优化处理逻辑",
        "memory": "检测到内存错误，建议检查资源使用或增加限制",
        "auth": "检测到认证错误，建议检查凭据配置",
        "rate": "检测到频率限制错误，建议实现退避策略",
        "validation": "检测到验证错误，建议检查输入数据和验证逻辑",
        "default": f"检测到重复错误 [{top_error[0]}] x{top_error[1]}，建议深入分析根因"
    }

    error_lower = top_error[0].lower()
    for key, rec in recommendations.items():
        if key in error_lower:
            return rec

    return recommendations["default"]


def analyze_run(run_data: dict[str, Any]) -> dict[str, Any]:
    """分析单个 run 的数据，生成建议"""
    errors = run_data.get("errors", [])
    steps = run_data.get("steps", [])
    tokens = run_data.get("total_tokens", 0)
    duration_ms = run_data.get("duration_ms", 0)

    analysis: dict[str, Any] = {
        "run_id": run_data.get("run_id"),
        "error_pattern": detect_error_pattern(errors),
        "performance": _analyze_performance(steps, tokens, duration_ms),
        "suggestions": []
    }

    # 基于分析生成建议
    if analysis["error_pattern"]["has_patterns"]:
        analysis["suggestions"].append({
            "type": "error_pattern",
            "priority": "HIGH",
            "message": analysis["error_pattern"]["recommendation"]
        })

    perf = analysis["performance"]
    if perf.get("slow_phases"):
        analysis["suggestions"].append({
            "type": "performance",
            "priority": "MEDIUM",
            "message": f"检测到慢 phase: {', '.join(perf['slow_phases'])}"
        })

    if tokens > 50000:
        analysis["suggestions"].append({
            "type": "token_efficiency",
            "priority": "LOW",
            "message": f"Token 使用较高 ({tokens})，考虑优化提示词"
        })

    return analysis


def _analyze_performance(steps: list[dict[str, Any]], tokens: int, duration_ms: int) -> dict[str, Any]:
    """分析性能"""
    if not steps:
        return {"slow_phases": [], "avg_step_duration_ms": 0}

    total_duration = sum(s.get("duration_ms", 0) for s in steps)
    avg_duration = total_duration / len(steps) if steps else 0

    slow_threshold = avg_duration * 2  # 超过平均值 2 倍视为慢
    slow_phases = [s["phase"] for s in steps if s.get("duration_ms", 0) > slow_threshold]

    return {
        "total_steps": len(steps),
        "total_duration_ms": duration_ms,
        "avg_step_duration_ms": round(avg_duration, 0),
        "slow_phases": slow_phases
    }


def load_run_tracker(tracker_path: str = ".run_tracker.json") -> list[dict]:
    """加载运行追踪数据"""
    if not _validate_path(tracker_path) or not os.path.exists(tracker_path):
        return []
    with open(tracker_path) as f:
        data = json.load(f)
        if isinstance(data, dict):
            runs = data.get("runs", [])
            if isinstance(runs, list):
                return runs
        return []


def load_step_records(records_path: str = ".step_records.json") -> list[dict]:
    """加载步骤记录数据"""
    if not _validate_path(records_path) or not os.path.exists(records_path):
        return []
    with open(records_path) as f:
        data = json.load(f)
        if isinstance(data, dict):
            records = data.get("records", [])
            if isinstance(records, list):
                return records
        return []


def detect_failures() -> dict:
    """检测所有失败模式"""
    runs = load_run_tracker()
    step_records = load_step_records()

    if not runs:
        return {"message": "无运行数据"}

    failed_runs = [r for r in runs if r.get("status") == "completed" and not r.get("success")]

    analysis_results = []
    for run in failed_runs[:10]:  # 只分析最近 10 个失败
        run_steps = [s for s in step_records if s.get("run_id") == run.get("run_id")]
        analysis = analyze_run({
            "run_id": run.get("run_id"),
            "errors": [s.get("error") for s in run_steps if s.get("error")],
            "steps": run_steps,
            "total_tokens": run.get("total_tokens", 0),
            "duration_ms": run.get("duration_ms", 0)
        })
        analysis_results.append(analysis)

    # 统计失败模式
    pattern_counter: Counter[str] = Counter()
    for a in analysis_results:
        if a["error_pattern"]["repeated_errors"]:
            pattern_counter.update(a["error_pattern"]["repeated_errors"].keys())

    return {
        "total_failed": len(failed_runs),
        "analyzed": len(analysis_results),
        "common_patterns": dict(pattern_counter.most_common(5)),
        "analyses": analysis_results
    }


def main():
    parser = argparse.ArgumentParser(description='Pattern Detector - 失败模式检测')
    parser.add_argument('--patterns-file', default=DEFAULT_PATTERNS_FILE,
                       help='模式文件路径')
    parser.add_argument('--op', choices=['detect-failures', 'analyze'],
                       required=True, help='操作类型')
    parser.add_argument('--run-id', '--run_id', dest='run_id', help='Run ID')
    parser.add_argument('--json', action='store_true', help='输出 JSON')

    args = parser.parse_args()

    if args.op == 'detect-failures':
        result = detect_failures()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"检测到 {result.get('total_failed', 0)} 个失败运行")
            if result.get('common_patterns'):
                print("\n常见错误模式:")
                for pattern, count in result.get('common_patterns', {}).items():
                    print(f"  {pattern}: x{count}")

    elif args.op == 'analyze':
        if not args.run_id:
            print("错误: --run-id 必须指定")
            return 1

        runs = load_run_tracker()
        run = next((r for r in runs if r.get("run_id") == args.run_id), None)

        if not run:
            print(f"Run {args.run_id} 未找到")
            return 1

        step_records = load_step_records()
        run_steps = [s for s in step_records if s.get("run_id") == args.run_id]

        analysis = analyze_run({
            "run_id": run.get("run_id"),
            "errors": [s.get("error") for s in run_steps if s.get("error")],
            "steps": run_steps,
            "total_tokens": run.get("total_tokens", 0),
            "duration_ms": run.get("duration_ms", 0)
        })

        if args.json:
            print(json.dumps(analysis, ensure_ascii=False, indent=2))
        else:
            print(f"\nRun {args.run_id} 分析结果:")
            if analysis["suggestions"]:
                print("\n建议:")
                for s in analysis["suggestions"]:
                    print(f"  [{s['priority']}] {s['message']}")
            else:
                print("  无明显问题")

    return 0


if __name__ == '__main__':
    sys.exit(main())
