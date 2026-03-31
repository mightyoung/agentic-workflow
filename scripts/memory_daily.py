#!/usr/bin/env python3
"""
Daily Memory Operations - 每日日志操作工具

管理 memory/YYYY-MM-DD.md 每日日志文件：
- 创建每日日志
- 添加任务记录
- 添加教训记录
- 归档会话总结

用法:
    python memory_daily.py --op=create --date=2026-03-20
    python memory_daily.py --op=add-task --date=2026-03-20 --task-id=T001 --desc="完成任务"
    python memory_daily.py --op=add-lesson --date=2026-03-20 --lesson="学到X"
    python memory_daily.py --op=show --date=2026-03-20
"""

import argparse
import os
import re
from datetime import datetime
from typing import List

# 默认每日日志目录
DEFAULT_MEMORY_DIR = "memory"


def ensure_memory_dir(memory_dir: str = DEFAULT_MEMORY_DIR) -> bool:
    """确保 memory 目录存在"""
    if not os.path.exists(memory_dir):
        os.makedirs(memory_dir, exist_ok=True)
        return True
    return False


def get_daily_file_path(date: str, memory_dir: str = DEFAULT_MEMORY_DIR) -> str:
    """获取指定日期的日志文件路径"""
    ensure_memory_dir(memory_dir)
    return os.path.join(memory_dir, f"{date}.md")


def create_daily_log(date: str, memory_dir: str = DEFAULT_MEMORY_DIR) -> bool:
    """创建每日日志"""
    filepath = get_daily_file_path(date, memory_dir)

    if os.path.exists(filepath):
        print(f"每日日志已存在: {filepath}")
        return False

    template = f"""# {date} - 每日工作日志

> 自动生成

## 任务记录

| 时间 | 任务ID | 描述 | 结果 |
|------|--------|------|------|
"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(template)

    print(f"已创建每日日志: {filepath}")
    return True


def add_task_record(date: str, task_id: str, description: str, result: str = "",
                   memory_dir: str = DEFAULT_MEMORY_DIR) -> bool:
    """添加任务记录"""
    filepath = get_daily_file_path(date, memory_dir)

    if not os.path.exists(filepath):
        create_daily_log(date, memory_dir)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    timestamp = datetime.now().strftime('%H:%M:%S')
    new_row = f"| {timestamp} | {task_id} | {description} | {result} |\n"

    # 在表格末尾添加新行
    content = content.rstrip() + '\n' + new_row

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"已添加任务记录: [{task_id}] {description}")
    return True


def add_lesson(date: str, lesson: str, memory_dir: str = DEFAULT_MEMORY_DIR) -> bool:
    """添加教训记录"""
    filepath = get_daily_file_path(date, memory_dir)

    if not os.path.exists(filepath):
        create_daily_log(date, memory_dir)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否有教训章节
    lesson_section = f"\n## 教训\n\n- {lesson}\n"

    if "## 教训" in content:
        # 追加到现有教训章节
        content = content.replace("\n## 教训\n", lesson_section)
    else:
        content += lesson_section

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"已添加教训: {lesson}")
    return True


def show_daily_log(date: str, memory_dir: str = DEFAULT_MEMORY_DIR) -> None:
    """显示每日日志"""
    filepath = get_daily_file_path(date, memory_dir)

    if not os.path.exists(filepath):
        print(f"每日日志不存在: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        print(f.read())


def list_daily_logs(memory_dir: str = DEFAULT_MEMORY_DIR) -> List[str]:
    """列出所有每日日志"""
    ensure_memory_dir(memory_dir)

    logs = []
    for f in os.listdir(memory_dir):
        if f.endswith('.md') and f != 'README.md':
            logs.append(f.replace('.md', ''))

    logs.sort(reverse=True)
    return logs


def distill_from_session(session_file: str = "SESSION-STATE.md",
                        memory_dir: str = DEFAULT_MEMORY_DIR) -> bool:
    """将会话状态蒸馏到每日日志"""
    if not os.path.exists(session_file):
        print(f"会话文件不存在: {session_file}")
        return False

    with open(session_file, 'r', encoding='utf-8') as f:
        content = f.read()

    today = datetime.now().strftime('%Y-%m-%d')
    create_daily_log(today, memory_dir)

    # 提取任务描述
    task_match = re.search(r'\*\*任务描述\*\*: (.+)', content)
    if task_match:
        task_desc = task_match.group(1).strip()
        if task_desc and task_desc != '(未设置)':
            add_task_record(today, "SESSION", task_desc, "从会话归档", memory_dir)

    # 提取决策记录
    decisions = re.findall(r'\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*([^|]+)\s*\|', content)
    for decision in decisions[:3]:  # 最多取3个
        decision = decision.strip()
        if decision:
            add_lesson(today, f"决策: {decision}", memory_dir)

    print(f"已将会话蒸馏到每日日志: {today}")
    return True


def main():
    parser = argparse.ArgumentParser(description='Daily Memory Operations - 每日日志操作工具')
    parser.add_argument('--dir', default=DEFAULT_MEMORY_DIR, help='记忆目录')
    parser.add_argument('--date', help='日期 (YYYY-MM-DD格式，默认今天)')
    parser.add_argument('--op', choices=['create', 'add-task', 'add-lesson', 'show', 'list', 'distill'],
                       required=True, help='操作类型')
    parser.add_argument('--task-id', help='任务ID')
    parser.add_argument('--desc', help='任务描述')
    parser.add_argument('--result', default='', help='任务结果')
    parser.add_argument('--lesson', help='教训内容')
    parser.add_argument('--session', default='SESSION-STATE.md', help='会话文件路径')

    args = parser.parse_args()

    # 默认日期为今天
    if not args.date:
        args.date = datetime.now().strftime('%Y-%m-%d')

    if args.op == 'create':
        create_daily_log(args.date, args.dir)
    elif args.op == 'add-task':
        if not args.task_id or not args.desc:
            print("错误: --task-id 和 --desc 必须指定")
            return 1
        add_task_record(args.date, args.task_id, args.desc, args.result, args.dir)
    elif args.op == 'add-lesson':
        if not args.lesson:
            print("错误: --lesson 必须指定")
            return 1
        add_lesson(args.date, args.lesson, args.dir)
    elif args.op == 'show':
        show_daily_log(args.date, args.dir)
    elif args.op == 'list':
        logs = list_daily_logs(args.dir)
        if logs:
            print("每日日志列表:")
            for log in logs:
                print(f"  - {log}")
        else:
            print("暂无每日日志")
    elif args.op == 'distill':
        distill_from_session(args.session, args.dir)

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
