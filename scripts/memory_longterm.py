#!/usr/bin/env python3
"""
Long-term Memory Operations - 长期记忆操作工具

管理 MEMORY.md 长期记忆文件 + .memory_index.jsonl 结构化索引：
- 初始化长期记忆
- 添加核心经验（支持 confidence / scope / project_id）
- 添加模式记录
- 搜索记忆（支持项目范围过滤）
- 从每日日志提炼

用法:
    python memory_longterm.py --op=init
    python memory_longterm.py --op=add-experience --exp="核心经验描述"
    python memory_longterm.py --op=add-experience --exp="经验" --confidence=0.8 --scope=project
    python memory_longterm.py --op=add-pattern --pattern="模式名称" --desc="模式描述"
    python memory_longterm.py --op=search --query="关键词"
    python memory_longterm.py --op=search --query="关键词" --scope=project
    python memory_longterm.py --op=refine --days=7
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import uuid
from datetime import datetime, timedelta

# 默认长期记忆文件
DEFAULT_MEMORY_FILE = "MEMORY.md"

# 结构化索引文件（JSONL，每行一条记忆条目）
MEMORY_INDEX_FILE = ".memory_index.jsonl"

def get_project_id() -> str:
    """返回当前 git 仓库远端 URL 的 SHA-1 前8位，用于项目范围隔离。
    如果无法获取（非 git 目录 / 无 remote），返回 'local'。
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=3
        )
        url = result.stdout.strip()
        if url:
            return hashlib.sha1(url.encode()).hexdigest()[:8]
    except Exception:
        pass
    return "local"


def add_to_index(
    entry_type: str,
    text: str,
    confidence: float = 0.5,
    scope: str = "project",
    project_id: str | None = None,
    tags: list[str] | None = None,
    index_file: str = MEMORY_INDEX_FILE,
) -> str:
    """向 .memory_index.jsonl 写入一条结构化记忆条目。

    Args:
        entry_type: "experience" | "pattern"
        text: 记忆内容
        confidence: 置信度 0.3-0.9
        scope: "project" | "global"
        project_id: git remote URL hash；None 时自动检测
        tags: 标签列表
        index_file: JSONL 索引文件路径

    Returns:
        新条目的 UUID
    """
    entry_id = str(uuid.uuid4())[:8]
    entry = {
        "id": entry_id,
        "type": entry_type,
        "text": text,
        "confidence": max(0.3, min(0.9, float(confidence))),
        "scope": scope,
        "project_id": project_id or get_project_id(),
        "tags": tags or [],
        "timestamp": datetime.now().strftime("%Y-%m-%d"),
    }
    try:
        with open(index_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return entry_id


def search_index(
    query: str,
    scope: str | None = None,
    project_id: str | None = None,
    limit: int = 10,
    index_file: str = MEMORY_INDEX_FILE,
) -> list[dict]:
    """从 .memory_index.jsonl 搜索结构化记忆。

    Args:
        query: 关键词（大小写不敏感）
        scope: "project" | "global" | None（不过滤）
        project_id: git remote hash；None 时自动检测（project scope 下自动过滤）
        limit: 最多返回条数
        index_file: JSONL 索引文件路径

    Returns:
        匹配条目列表（按 confidence 降序）
    """
    if not os.path.exists(index_file):
        return []

    current_project = project_id or get_project_id()
    query_lower = query.lower()
    matches: list[dict] = []

    try:
        with open(index_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Scope filter
                if scope == "project" and entry.get("project_id") != current_project:
                    continue
                if scope == "global" and entry.get("scope") != "global":
                    continue

                # Text match
                if query_lower in entry.get("text", "").lower():
                    matches.append(entry)
    except OSError:
        return []

    # Sort by confidence descending
    matches.sort(key=lambda x: x.get("confidence", 0.5), reverse=True)
    return matches[:limit]


def ensure_memory_exists(filepath: str = DEFAULT_MEMORY_FILE) -> bool:
    """确保长期记忆文件存在"""
    if not os.path.exists(filepath):
        template = f"""# MEMORY.md - 长期记忆

> 自动生成的最后手段记忆

## 核心经验
- (从每日日志和工作会话中提炼)

## 模式记录
- (重复出现的模式)

## 项目知识
- (特定项目的关键信息)

## 技术栈
- (使用的技术栈和偏好)

## 偏好设置
- (用户偏好和技术偏好)

---
最后更新: {datetime.now().strftime('%Y-%m-%d')}
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(template)
        return True
    return False


def add_experience(
    experience: str,
    filepath: str = DEFAULT_MEMORY_FILE,
    confidence: float = 0.5,
    scope: str = "project",
    project_id: str | None = None,
) -> bool:
    """添加核心经验（同时写入 MEMORY.md 和 .memory_index.jsonl）。

    Args:
        experience: 经验描述（支持 "Task:... Trigger:... Mistake:... Fix:... Signal:..." 格式）
        filepath: MEMORY.md 路径
        confidence: 置信度 0.3-0.9（越高越可靠）
        scope: "project"（当前项目）| "global"（跨项目）
        project_id: git remote hash；None 时自动检测
    """
    ensure_memory_exists(filepath)

    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    # 在核心经验章节添加
    new_exp = f"- {experience}\n"

    if "## 核心经验" in content:
        # 检查是否有默认占位符
        if "(从每日日志和工作会话中提炼)" in content:
            content = content.replace("(从每日日志和工作会话中提炼)", new_exp)
        else:
            # 追加到现有经验
            pat = r'(## 核心经验\n)(.*?)(\n## |\n---)'
            match = re.search(pat, content, re.DOTALL)
            if match:
                content = content.replace(
                    match.group(0),
                    match.group(1) + match.group(2) + new_exp + match.group(3),
                )
    else:
        content += f"\n## 核心经验\n{new_exp}"

    # 更新最后更新时间
    content = re.sub(r'最后更新: .+', f'最后更新: {datetime.now().strftime("%Y-%m-%d")}', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    # 同步写入结构化索引
    add_to_index(
        entry_type="experience",
        text=experience,
        confidence=confidence,
        scope=scope,
        project_id=project_id,
    )

    print(f"已添加核心经验 [confidence={confidence:.1f}, scope={scope}]: {experience[:50]}...")
    return True


def add_pattern(pattern_name: str, description: str, filepath: str = DEFAULT_MEMORY_FILE) -> bool:
    """添加模式记录"""
    ensure_memory_exists(filepath)

    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    new_pattern = f"- **{pattern_name}**: {description}\n"

    if "## 模式记录" in content:
        if "(重复出现的模式)" in content:
            content = content.replace("(重复出现的模式)", new_pattern)
        else:
            pattern = r'(## 模式记录\n)(.*?)(\n## |\n---)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                content = content.replace(match.group(0), match.group(1) + match.group(2) + new_pattern + match.group(3))
    else:
        content += f"\n## 模式记录\n{new_pattern}"

    content = re.sub(r'最后更新: .+', f'最后更新: {datetime.now().strftime("%Y-%m-%d")}', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"已添加模式: {pattern_name}")
    return True


def search_memory(
    query: str,
    filepath: str = DEFAULT_MEMORY_FILE,
    scope: str | None = None,
    limit: int = 10,
) -> list[str]:
    """搜索记忆内容（先搜结构化索引，再 fallback 到 MEMORY.md 全文搜索）。

    Args:
        query: 搜索关键词
        filepath: MEMORY.md 路径
        scope: "project" | "global" | None（不过滤）
        limit: 最多返回条数
    """
    results: list[str] = []

    # 1. 优先搜索结构化索引（置信度排序）
    indexed = search_index(query, scope=scope, limit=limit)
    for entry in indexed:
        conf = entry.get("confidence", 0.5)
        ts = entry.get("timestamp", "")
        results.append(f"[{ts} conf={conf:.1f}] {entry.get('text', '')}")

    # 2. Fallback：全文搜索 MEMORY.md（去重）
    if os.path.exists(filepath):
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if query.lower() in line.lower():
                start = max(0, i - 1)
                end = min(len(lines), i + 2)
                context = '\n'.join(lines[start:end])
                # Avoid duplicating indexed results
                if context not in results:
                    results.append(context)

    return results[:limit]


def show_memory(filepath: str = DEFAULT_MEMORY_FILE) -> None:
    """显示长期记忆"""
    if not os.path.exists(filepath):
        print(f"长期记忆文件不存在: {filepath}")
        return

    with open(filepath, encoding='utf-8') as f:
        print(f.read())


def refine_from_daily_logs(days: int = 7, memory_dir: str = "memory",
                          output_file: str = DEFAULT_MEMORY_FILE) -> bool:
    """从每日日志提炼到长期记忆"""
    if not os.path.exists(memory_dir):
        print(f"每日日志目录不存在: {memory_dir}")
        return False

    # 收集最近N天的日志
    recent_logs = []
    end_date = datetime.now()

    for i in range(days):
        date = (end_date - timedelta(days=i)).strftime('%Y-%m-%d')
        log_file = os.path.join(memory_dir, f"{date}.md")
        if os.path.exists(log_file):
            with open(log_file, encoding='utf-8') as f:
                recent_logs.append(f.read())

    if not recent_logs:
        print(f"没有找到最近 {days} 天的日志")
        return False

    # 提取教训
    lessons = []
    for log in recent_logs:
        lesson_matches = re.findall(r'## 教训\s*\n(.*?)(?=\n## |\n---|\Z)', log, re.DOTALL)
        for match in lesson_matches:
            lines = match.strip().split('\n')
            for line in lines:
                if line.startswith('- '):
                    lessons.append(line[2:])

    # 添加到长期记忆
    ensure_memory_exists(output_file)
    for lesson in set(lessons):  # 去重
        if lesson:
            add_experience(f"[提炼] {lesson}", output_file)

    print(f"已从 {days} 天的日志中提炼 {len(set(lessons))} 条经验到长期记忆")
    return True


def read_task_history(limit: int = 100) -> list:
    """
    读取.task_history.jsonl任务历史

    Returns:
        list of task records
    """
    history_file = ".task_history.jsonl"

    if not os.path.exists(history_file):
        return []

    records = []
    try:
        with open(history_file, encoding='utf-8') as f:
            for line_num, line in enumerate(f):
                if line_num >= limit:
                    break
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return []

    return records


def generate_weekly_report(days: int = 7, output_format: str = "text") -> str:
    """
    从.task_history.jsonl生成周报

    统计:
    - 任务总数
    - 成功率
    - 平均耗时
    - 常见教训

    Returns:
        周报文本或JSON
    """
    records = read_task_history(limit=1000)

    if not records:
        if output_format == "json":
            return json.dumps({"error": "没有任务历史记录"}, ensure_ascii=False, indent=2)
        return "没有任务历史记录"

    # 过滤最近N天的记录
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_records = []

    for record in records:
        # 尝试解析时间戳
        timestamp = record.get("timestamp") or record.get("created_at") or record.get("date")
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    record_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    record_date = datetime.fromtimestamp(timestamp)
                if record_date >= cutoff_date:
                    recent_records.append(record)
            except (ValueError, TypeError):
                # 如果无法解析，仍然包含该记录
                recent_records.append(record)
        else:
            # 没有时间戳的记录也包含
            recent_records.append(record)

    if not recent_records:
        if output_format == "json":
            return json.dumps({
                "period_days": days,
                "total_tasks": 0,
                "message": f"最近 {days} 天没有任务记录"
            }, ensure_ascii=False, indent=2)
        return f"最近 {days} 天没有任务记录"

    # 统计
    total_tasks = len(recent_records)
    completed = sum(1 for r in recent_records if r.get("status") in ("completed", "success", "done"))
    failed = sum(1 for r in recent_records if r.get("status") in ("failed", "error", "failure"))

    success_rate = (completed / total_tasks * 100) if total_tasks > 0 else 0

    # 计算平均耗时
    durations = []
    for r in recent_records:
        duration = r.get("duration") or r.get("elapsed") or r.get("time_elapsed")
        if duration:
            try:
                durations.append(float(duration))
            except (ValueError, TypeError):
                pass

    avg_duration = sum(durations) / len(durations) if durations else 0

    # 提取教训
    lessons = []
    for r in recent_records:
        lesson = r.get("lesson") or r.get("lessons") or r.get("insight") or r.get("reflection")
        if lesson:
            if isinstance(lesson, list):
                lessons.extend(lesson)
            else:
                lessons.append(lesson)

    # 统计常见模式
    status_counts: dict[str, int] = {}
    for r in recent_records:
        status = r.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    if output_format == "json":
        return json.dumps({
            "period_days": days,
            "total_tasks": total_tasks,
            "completed": completed,
            "failed": failed,
            "success_rate": round(success_rate, 1),
            "avg_duration_seconds": round(avg_duration, 2),
            "lessons": list(set(lessons)),
            "status_breakdown": status_counts
        }, ensure_ascii=False, indent=2)

    # 文本格式输出
    report_lines = [
        f"=== {'周' if days == 7 else '月' if days == 30 else f'{days}天'}报 ({datetime.now().strftime('%Y-%m-%d')}) ===",
        "",
        f"任务总数: {total_tasks}",
        f"完成数: {completed}",
        f"失败数: {failed}",
        f"成功率: {success_rate:.1f}%",
        f"平均耗时: {avg_duration:.1f} 秒" if durations else "平均耗时: N/A",
        "",
        "状态分布:",
    ]

    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        report_lines.append(f"  - {status}: {count}")

    if lessons:
        report_lines.append("")
        report_lines.append("常见教训:")
        for lesson in list(set(lessons))[:5]:
            report_lines.append(f"  - {lesson}")

    return "\n".join(report_lines)


def main() -> int:
    parser = argparse.ArgumentParser(description='Long-term Memory Operations - 长期记忆操作工具')
    parser.add_argument('--file', default=DEFAULT_MEMORY_FILE, help='长期记忆文件路径')
    parser.add_argument('--dir', default='memory', help='每日日志目录')
    parser.add_argument('--op', choices=[
        'init', 'add-experience', 'add-pattern', 'search', 'show', 'refine',
        'weekly-report', 'monthly-report', 'history',
    ], required=True, help='操作类型')
    parser.add_argument('--exp', help='核心经验内容')
    parser.add_argument('--pattern', help='模式名称')
    parser.add_argument('--desc', help='模式描述')
    parser.add_argument('--query', help='搜索关键词')
    parser.add_argument('--days', type=int, default=7, help='提炼最近N天的日志')
    parser.add_argument('--limit', type=int, default=10, help='搜索/历史记录条数限制')
    parser.add_argument('--format', default='text', choices=['text', 'json'], help='输出格式')
    # ── 新增字段 ──────────────────────────────────────────────
    parser.add_argument('--confidence', type=float, default=0.5,
                        help='经验置信度 0.3-0.9（默认 0.5）')
    parser.add_argument('--scope', default='project', choices=['project', 'global'],
                        help='记忆范围: project（仅当前项目）| global（跨项目）')
    parser.add_argument('--project-id', default=None,
                        help='项目 ID（默认自动从 git remote 检测）')

    args = parser.parse_args()

    if args.op == 'init':
        ensure_memory_exists(args.file)
        print(f"已初始化长期记忆: {args.file}")
    elif args.op == 'add-experience':
        if not args.exp:
            print("错误: --exp 必须指定")
            return 1
        add_experience(
            args.exp, args.file,
            confidence=args.confidence,
            scope=args.scope,
            project_id=args.project_id,
        )
    elif args.op == 'add-pattern':
        if not args.pattern or not args.desc:
            print("错误: --pattern 和 --desc 必须指定")
            return 1
        add_pattern(args.pattern, args.desc, args.file)
    elif args.op == 'search':
        if not args.query:
            print("错误: --query 必须指定")
            return 1
        results = search_memory(args.query, args.file, scope=args.scope, limit=args.limit)
        if results:
            print(f"找到 {len(results)} 条匹配 (scope={args.scope or 'all'}):")
            for i, result in enumerate(results, 1):
                print(f"\n--- 结果 {i} ---")
                print(result)
        else:
            print(f"没有找到与 '{args.query}' 相关的记忆")
    elif args.op == 'show':
        show_memory(args.file)
    elif args.op == 'refine':
        refine_from_daily_logs(args.days, args.dir, args.file)
    elif args.op == 'history':
        records = read_task_history(args.limit)
        if records:
            print(f"共 {len(records)} 条历史记录:")
            for i, record in enumerate(records, 1):
                timestamp = record.get("timestamp") or record.get("created_at") or record.get("date", "N/A")
                status = record.get("status", "unknown")
                task_desc = record.get("task") or record.get("description") or record.get("prompt", "")[:50]
                print(f"{i}. [{timestamp}] {status}: {task_desc}...")
        else:
            print("没有任务历史记录")
    elif args.op == 'weekly-report':
        report = generate_weekly_report(args.days, args.format)
        print(report)
    elif args.op == 'monthly-report':
        report = generate_weekly_report(30, args.format)
        print(report)

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
