#!/usr/bin/env python3
"""
Memory Operations - 记忆操作工具

提供 SESSION-STATE.md 的自动化操作：
- 更新当前任务
- 添加修正记录
- 添加偏好
- 添加决策
- 添加具体数值

用法:
    python memory_ops.py --op=update --key=task --value="任务描述"
    python memory_ops.py --op=add --type=correction --from="错误理解" --to="正确理解"
    python memory_ops.py --op=get --key=preferences
"""

import argparse
import os
import re
import sys
from datetime import datetime
from typing import Any, Optional

from safe_io import safe_append_jsonl, safe_write_text_locked

# 默认 SESSION-STATE 路径
DEFAULT_SESSION_STATE = "SESSION-STATE.md"


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


def ensure_session_state_exists(path: str = DEFAULT_SESSION_STATE) -> bool:
    """确保 SESSION-STATE.md 存在"""
    if not _validate_path(path):
        return False
    if not os.path.exists(path):
        # 确保父目录存在
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            return False
        # 创建默认模板
        default_content = f"""# SESSION-STATE.md

> 自动生成的工作内存文件

## 当前任务
- **任务描述**: (未设置)
- **阶段**: IDLE
- **中断点**: (无)
- **进度**: 0
- **开始时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **优先级**: P2

## Skill 策略
- **skill_policy**: (未设置)
- **use_skill**: (未设置)
- **skill_activation_level**: (未设置)
- **tokens_expected**: (未设置)
- **profile_source**: (未设置)

## 计划摘要
- **plan_source**: (未设置)
- **plan_task_count**: 0
- **completed_task_count**: 0
- **in_progress_task_count**: 0
- **blocked_task_count**: 0
- **ready_task_count**: 0
- **parallel_candidate_group_count**: 0
- **parallel_ready_task_count**: 0
- **conflict_group_count**: 0
- **worktree_recommended**: (未设置)
- **worktree_reason**: (未设置)
- **plan_digest**: (未设置)

## THINKING摘要
- **workflow_label**: (未设置)
- **workflow**: (未设置)
- **major_contradiction**: (未设置)
- **stage_judgment**: (未设置)
- **local_attack_point**: (未设置)
- **recommendation**: (未设置)
- **memory_hints_count**: 0

## 恢复摘要
- **original_session_id**: (未设置)
- **resume_from**: (未设置)
- **next_phase**: (未设置)
- **skill_policy**: (未设置)
- **use_skill**: (未设置)
- **skill_activation_level**: (未设置)
- **complexity**: (未设置)
- **thinking_workflow_label**: (未设置)
- **thinking_major_contradiction**: (未设置)
- **thinking_stage_judgment**: (未设置)
- **thinking_local_attack_point**: (未设置)
- **thinking_recommendation**: (未设置)
- **thinking_memory_hints_count**: 0
- **failure_event_count**: 0
- **escalation_event_count**: 0

## 审查摘要
- **review_found**: (未设置)
- **review_source**: (未设置)
- **review_status**: (未设置)
- **stage_1_status**: (未设置)
- **stage_2_status**: (未设置)
- **risk_level**: (未设置)
- **verdict**: (未设置)
- **degraded_mode**: (未设置)
- **files_reviewed**: 0

## 关键信息 (WAL协议收集)

### 修正记录
| 时间 | 原始理解 | 正确理解 |
|------|----------|----------|

### 用户偏好
- **风格偏好**:
- **技术偏好**:

### 决策记录
| 时间 | 决策内容 | 理由 |
|------|----------|------|

### 具体数值
| 类型 | 值 |
|------|---|

## 上下文进度

### 已完成步骤
- [ ]

### 当前步骤
-

### 遇到的问题
| 问题 | 尝试次数 | 解决方案 |
|------|----------|----------|
"""
        safe_write_text_locked(path, default_content)
        return True
    return False


def update_task_info(path: str, task: str, phase: str = "PLANNING") -> bool:
    """更新任务信息"""
    if not ensure_session_state_exists(path) and not os.path.exists(path):
        return False

    with open(path, encoding='utf-8') as f:
        content = f.read()

    # 更新任务描述
    pattern = r'(\*\*任务描述\*\*: )(.*)(\n)'
    if re.search(pattern, content):
        content = re.sub(pattern, f'\\1{task}\\3', content)
    else:
        content = re.sub(r'(\*\*任务描述\*\*: )', f'\\1{task}', content)

    # 更新阶段
    pattern = r'(\*\*阶段\*\*: )(.*)(\n)'
    content = re.sub(pattern, f'\\1{phase}\\3', content)

    safe_write_text_locked(path, content)

    return True


def add_correction(path: str, original: str, corrected: str) -> bool:
    """添加修正记录"""
    if not ensure_session_state_exists(path) and not os.path.exists(path):
        return False

    with open(path, encoding='utf-8') as f:
        content = f.read()

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_row = f"| {timestamp} | {original} | {corrected} |\n"

    # 在表格末尾添加新行
    # 找到最后一个 | 结尾的行
    pattern = r'(\| .+ \| .+ \| .+ \|\n)(### )'
    if re.search(pattern, content):
        content = re.sub(pattern, f'{new_row}\\2', content)
    else:
        # 如果表格为空或格式不对，追加
        content += new_row

    safe_write_text_locked(path, content)

    return True


def add_preference(path: str, preference_type: str, value: str) -> bool:
    """添加用户偏好"""
    if not ensure_session_state_exists(path) and not os.path.exists(path):
        return False

    with open(path, encoding='utf-8') as f:
        content = f.read()

    if preference_type == 'style':
        new_pref = f"- **{preference_type}偏好**: {value}"
    else:
        new_pref = f"- **{preference_type}偏好**: {value}"

    # 查找对应偏好的行并更新
    escaped_type = re.escape(preference_type)
    pattern = f'(\\*\\*{escaped_type}偏好\\*\\*: )(.*)(\n)'
    if re.search(pattern, content):
        content = re.sub(pattern, f'\\g<1>{value}\\3', content)
    else:
        # 如果找不到，追加
        content += f"\n{new_pref}\n"

    safe_write_text_locked(path, content)

    return True


def add_decision(path: str, decision: str, reason: str = "") -> bool:
    """添加决策记录"""
    if not ensure_session_state_exists(path) and not os.path.exists(path):
        return False

    with open(path, encoding='utf-8') as f:
        content = f.read()

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_row = f"| {timestamp} | {decision} | {reason} |\n"

    # 在表格末尾添加新行
    pattern = r'(\| .+ \| .+ \| .+ \|\n)(### )'
    if re.search(pattern, content):
        content = re.sub(pattern, f'{new_row}\\2', content)
    else:
        content += new_row

    safe_write_text_locked(path, content)

    return True


def add_value(path: str, value_type: str, value: str) -> bool:
    """添加具体数值"""
    if not ensure_session_state_exists(path) and not os.path.exists(path):
        return False

    with open(path, encoding='utf-8') as f:
        content = f.read()

    new_row = f"| {value_type} | {value} |\n"

    # 在表格末尾添加新行
    pattern = r'(\| .+ \| .+ \|\n)$'
    if re.search(pattern, content):
        content = re.sub(pattern, f'{new_row}', content)
    else:
        content += new_row

    safe_write_text_locked(path, content)

    return True


def update_resume_point(path: str, phase: str, progress: int) -> bool:
    """更新任务中断点信息"""
    # 验证进度范围
    if not isinstance(progress, int) or not (0 <= progress <= 100):
        import logging
        logging.warning(f"update_resume_point: 无效的进度值: {progress}, 期望 0-100")
        return False
    if not os.path.exists(path):
        return False

    with open(path, encoding='utf-8') as f:
        content = f.read()

    # 更新中断点
    pattern = r'(\*\*中断点\*\*: )(.*)(\n)'
    if re.search(pattern, content):
        content = re.sub(pattern, f'\\1{phase}\\3', content)
    else:
        # 如果字段不存在，先确保有阶段字段
        phase_pattern = r'(\*\*阶段\*\*: )([^\n]+)(\n)'
        if re.search(phase_pattern, content):
            content = re.sub(phase_pattern, f'\\1\\2\\3- **中断点**: {phase}\n', content)

    # 更新进度
    pattern = r'(\*\*进度\*\*: )(\d+)'
    if re.search(pattern, content):
        content = re.sub(pattern, f'\\g<1>{progress}', content)
    else:
        # 如果字段不存在，在中断点后添加
        pattern = r'(\*\*中断点\*\*: [^\n]+\n)'
        if re.search(pattern, content):
            content = re.sub(pattern, f'\\1- **进度**: {progress}%\n', content)

    safe_write_text_locked(path, content)

    return True


def update_runtime_profile(
    path: str,
    skill_policy: str,
    use_skill: bool,
    skill_activation_level: int,
    tokens_expected: int,
    profile_source: str,
) -> bool:
    """更新运行时画像到 SESSION-STATE.md。"""
    if not ensure_session_state_exists(path) and not os.path.exists(path):
        return False

    with open(path, encoding="utf-8") as f:
        content = f.read()

    section = (
        "## Skill 策略\n"
        f"- **skill_policy**: {skill_policy}\n"
        f"- **use_skill**: {str(use_skill)}\n"
        f"- **skill_activation_level**: {skill_activation_level}\n"
        f"- **tokens_expected**: {tokens_expected}\n"
        f"- **profile_source**: {profile_source}\n"
    )

    pattern = r"## Skill 策略\n(?:- \*\*skill_policy\*\*: .*\n- \*\*use_skill\*\*: .*\n- \*\*skill_activation_level\*\*: .*\n- \*\*tokens_expected\*\*: .*\n- \*\*profile_source\*\*: .*\n)?"
    if re.search(pattern, content):
        content = re.sub(pattern, section, content, count=1)
    else:
        insert_after = r"(\- \*\*优先级\*\*: .*\n)"
        if re.search(insert_after, content):
            content = re.sub(insert_after, r"\1\n" + section + "\n", content, count=1)
        else:
            content += "\n" + section + "\n"

    safe_write_text_locked(path, content)
    return True


def update_planning_summary(
    path: str,
    planning_summary: dict[str, Any] | None,
) -> bool:
    """更新计划摘要到 SESSION-STATE.md。"""
    if not ensure_session_state_exists(path) and not os.path.exists(path):
        return False

    with open(path, encoding="utf-8") as f:
        content = f.read()

    planning_summary = planning_summary or {}
    section = (
        "## 计划摘要\n"
        f"- **plan_source**: {planning_summary.get('plan_source', '(未设置)')}\n"
        f"- **plan_task_count**: {planning_summary.get('plan_task_count', 0)}\n"
        f"- **completed_task_count**: {planning_summary.get('completed_task_count', 0)}\n"
        f"- **in_progress_task_count**: {planning_summary.get('in_progress_task_count', 0)}\n"
        f"- **blocked_task_count**: {planning_summary.get('blocked_task_count', 0)}\n"
        f"- **ready_task_count**: {planning_summary.get('ready_task_count', 0)}\n"
        f"- **parallel_candidate_group_count**: {planning_summary.get('parallel_candidate_group_count', 0)}\n"
        f"- **parallel_ready_task_count**: {planning_summary.get('parallel_ready_task_count', 0)}\n"
        f"- **conflict_group_count**: {planning_summary.get('conflict_group_count', 0)}\n"
        f"- **worktree_recommended**: {planning_summary.get('worktree_recommended', '(未设置)')}\n"
        f"- **worktree_reason**: {planning_summary.get('worktree_reason', '(未设置)')}\n"
        f"- **plan_digest**: {planning_summary.get('plan_digest', '(未设置)')}\n"
    )

    pattern = r"## 计划摘要\n(?:- \*\*plan_source\*\*: .*\n- \*\*plan_task_count\*\*: .*\n- \*\*completed_task_count\*\*: .*\n- \*\*in_progress_task_count\*\*: .*\n- \*\*blocked_task_count\*\*: .*\n- \*\*ready_task_count\*\*: .*\n- \*\*parallel_candidate_group_count\*\*: .*\n- \*\*parallel_ready_task_count\*\*: .*\n- \*\*conflict_group_count\*\*: .*\n- \*\*worktree_recommended\*\*: .*\n- \*\*worktree_reason\*\*: .*\n- \*\*plan_digest\*\*: .*\n)?"
    if re.search(pattern, content):
        content = re.sub(pattern, section, content, count=1)
    else:
        insert_after = r"(\## Skill 策略\n(?:- \*\*skill_policy\*\*: .*\n- \*\*use_skill\*\*: .*\n- \*\*skill_activation_level\*\*: .*\n- \*\*tokens_expected\*\*: .*\n- \*\*profile_source\*\*: .*\n)?)"
        if re.search(insert_after, content):
            content = re.sub(insert_after, r"\1\n" + section + "\n", content, count=1)
        else:
            content += "\n" + section + "\n"

    safe_write_text_locked(path, content)
    return True


def get_planning_summary(path: str) -> dict[str, Any]:
    """从 SESSION-STATE.md 读取计划摘要。"""
    if not os.path.exists(path):
        return {}

    with open(path, encoding="utf-8") as f:
        content = f.read()

    pattern = (
        r"## 计划摘要\n"
        r"(?:- \*\*plan_source\*\*: (.*)\n"
        r"- \*\*plan_task_count\*\*: (\d+)\n"
        r"- \*\*completed_task_count\*\*: (\d+)\n"
        r"- \*\*in_progress_task_count\*\*: (\d+)\n"
        r"- \*\*blocked_task_count\*\*: (\d+)\n"
        r"- \*\*ready_task_count\*\*: (\d+)\n"
        r"- \*\*parallel_candidate_group_count\*\*: (\d+)\n"
        r"- \*\*parallel_ready_task_count\*\*: (\d+)\n"
        r"- \*\*conflict_group_count\*\*: (\d+)\n"
        r"- \*\*worktree_recommended\*\*: (.*)\n"
        r"- \*\*worktree_reason\*\*: (.*)\n"
        r"- \*\*plan_digest\*\*: (.*)\n)?"
    )
    match = re.search(pattern, content)
    if not match:
        return {}

    groups = match.groups()
    if not groups or len(groups) < 12 or groups[0] is None:
        return {}

    def _as_int(value: str | None) -> int:
        try:
            return int(str(value).strip())
        except Exception:
            return 0

    def _as_bool(value: str | None) -> bool:
        return str(value).strip().lower() in {"true", "1", "yes", "y"}

    return {
        "plan_source": str(groups[0]).strip(),
        "plan_task_count": _as_int(groups[1]),
        "completed_task_count": _as_int(groups[2]),
        "in_progress_task_count": _as_int(groups[3]),
        "blocked_task_count": _as_int(groups[4]),
        "ready_task_count": _as_int(groups[5]),
        "parallel_candidate_group_count": _as_int(groups[6]),
        "parallel_ready_task_count": _as_int(groups[7]),
        "conflict_group_count": _as_int(groups[8]),
        "worktree_recommended": _as_bool(groups[9]),
        "worktree_reason": str(groups[10]).strip(),
        "plan_digest": str(groups[11]).strip(),
    }


def update_thinking_summary(
    path: str,
    thinking_summary: dict[str, Any] | None,
) -> bool:
    """更新 THINKING 摘要到 SESSION-STATE.md。"""
    if not ensure_session_state_exists(path) and not os.path.exists(path):
        return False

    with open(path, encoding="utf-8") as f:
        content = f.read()

    thinking_summary = thinking_summary or {}
    section = (
        "## THINKING摘要\n"
        f"- **workflow_label**: {thinking_summary.get('workflow_label', '(未设置)')}\n"
        f"- **workflow**: {thinking_summary.get('workflow', '(未设置)')}\n"
        f"- **major_contradiction**: {thinking_summary.get('major_contradiction', '(未设置)')}\n"
        f"- **stage_judgment**: {thinking_summary.get('stage_judgment', '(未设置)')}\n"
        f"- **local_attack_point**: {thinking_summary.get('local_attack_point', '(未设置)')}\n"
        f"- **recommendation**: {thinking_summary.get('recommendation', '(未设置)')}\n"
        f"- **memory_hints_count**: {thinking_summary.get('memory_hints_count', 0)}\n"
    )

    pattern = r"## THINKING摘要\n(?:- \*\*workflow_label\*\*: .*\n- \*\*workflow\*\*: .*\n- \*\*major_contradiction\*\*: .*\n- \*\*stage_judgment\*\*: .*\n- \*\*local_attack_point\*\*: .*\n- \*\*recommendation\*\*: .*\n- \*\*memory_hints_count\*\*: .*\n)?"
    if re.search(pattern, content):
        content = re.sub(pattern, section, content, count=1)
    else:
        marker = "\n## 恢复摘要\n"
        if marker in content:
            content = content.replace(marker, f"\n{section}\n## 恢复摘要\n", 1)
        else:
            content += "\n" + section + "\n"

    safe_write_text_locked(path, content)
    return True


def get_thinking_summary(path: str) -> dict[str, Any]:
    """从 SESSION-STATE.md 读取 THINKING 摘要。"""
    if not os.path.exists(path):
        return {}

    with open(path, encoding="utf-8") as f:
        content = f.read()

    pattern = (
        r"## THINKING摘要\n"
        r"(?:- \*\*workflow_label\*\*: (.*)\n"
        r"- \*\*workflow\*\*: (.*)\n"
        r"- \*\*major_contradiction\*\*: (.*)\n"
        r"- \*\*stage_judgment\*\*: (.*)\n"
        r"- \*\*local_attack_point\*\*: (.*)\n"
        r"- \*\*recommendation\*\*: (.*)\n"
        r"- \*\*memory_hints_count\*\*: (\d+)\n)?"
    )
    match = re.search(pattern, content)
    if not match:
        return {}

    groups = match.groups()
    if not groups or len(groups) < 7 or groups[0] is None:
        return {}

    return {
        "workflow_label": groups[0].strip(),
        "workflow": groups[1].strip(),
        "major_contradiction": groups[2].strip(),
        "stage_judgment": groups[3].strip(),
        "local_attack_point": groups[4].strip(),
        "recommendation": groups[5].strip(),
        "memory_hints_count": int(groups[6]),
    }


def update_resume_summary(
    path: str,
    resume_from: str,
    next_phase: str | None,
    original_session_id: str,
    runtime_profile: dict[str, Any] | None = None,
    planning_summary: dict[str, Any] | None = None,
    thinking_summary: dict[str, Any] | None = None,
    failure_event_summary: dict[str, Any] | None = None,
) -> bool:
    """更新恢复摘要到 SESSION-STATE.md。"""
    if not ensure_session_state_exists(path) and not os.path.exists(path):
        return False

    with open(path, encoding="utf-8") as f:
        content = f.read()

    runtime_profile = runtime_profile or {}
    planning_summary = planning_summary or {}
    thinking_summary = thinking_summary or {}
    failure_event_summary = failure_event_summary or {}

    section = (
        "## 恢复摘要\n"
        f"- **original_session_id**: {original_session_id}\n"
        f"- **resume_from**: {resume_from}\n"
        f"- **next_phase**: {next_phase or '(unknown)'}\n"
        f"- **skill_policy**: {runtime_profile.get('skill_policy', '(未设置)')}\n"
        f"- **use_skill**: {runtime_profile.get('use_skill', '(未设置)')}\n"
        f"- **skill_activation_level**: {runtime_profile.get('skill_activation_level', '(未设置)')}\n"
        f"- **complexity**: {runtime_profile.get('complexity', '(未设置)')}\n"
        f"- **planning_plan_source**: {planning_summary.get('plan_source', '(未设置)')}\n"
        f"- **planning_plan_task_count**: {planning_summary.get('plan_task_count', 0)}\n"
        f"- **planning_ready_task_count**: {planning_summary.get('ready_task_count', 0)}\n"
        f"- **planning_worktree_recommended**: {planning_summary.get('worktree_recommended', '(未设置)')}\n"
        f"- **planning_plan_digest**: {planning_summary.get('plan_digest', '(未设置)')}\n"
        f"- **thinking_workflow_label**: {thinking_summary.get('workflow_label', '(未设置)')}\n"
        f"- **thinking_major_contradiction**: {thinking_summary.get('major_contradiction', '(未设置)')}\n"
        f"- **thinking_stage_judgment**: {thinking_summary.get('stage_judgment', '(未设置)')}\n"
        f"- **thinking_local_attack_point**: {thinking_summary.get('local_attack_point', '(未设置)')}\n"
        f"- **thinking_recommendation**: {thinking_summary.get('recommendation', '(未设置)')}\n"
        f"- **thinking_memory_hints_count**: {thinking_summary.get('memory_hints_count', 0)}\n"
        f"- **failure_event_count**: {failure_event_summary.get('failure_event_count', 0)}\n"
        f"- **escalation_event_count**: {failure_event_summary.get('escalation_event_count', 0)}\n"
    )

    pattern = r"## 恢复摘要\n(?:- \*\*original_session_id\*\*: .*\n- \*\*resume_from\*\*: .*\n- \*\*next_phase\*\*: .*\n- \*\*skill_policy\*\*: .*\n- \*\*use_skill\*\*: .*\n- \*\*skill_activation_level\*\*: .*\n- \*\*complexity\*\*: .*\n- \*\*planning_plan_source\*\*: .*\n- \*\*planning_plan_task_count\*\*: .*\n- \*\*planning_ready_task_count\*\*: .*\n- \*\*planning_worktree_recommended\*\*: .*\n- \*\*planning_plan_digest\*\*: .*\n- \*\*thinking_workflow_label\*\*: .*\n- \*\*thinking_major_contradiction\*\*: .*\n- \*\*thinking_stage_judgment\*\*: .*\n- \*\*thinking_local_attack_point\*\*: .*\n- \*\*thinking_recommendation\*\*: .*\n- \*\*thinking_memory_hints_count\*\*: .*\n- \*\*failure_event_count\*\*: .*\n- \*\*escalation_event_count\*\*: .*\n)?"
    if re.search(pattern, content):
        content = re.sub(pattern, section, content, count=1)
    else:
        insert_after = r"(\## Skill 策略\n(?:- \*\*skill_policy\*\*: .*\n- \*\*use_skill\*\*: .*\n- \*\*skill_activation_level\*\*: .*\n- \*\*tokens_expected\*\*: .*\n- \*\*profile_source\*\*: .*\n)?)"
        if re.search(insert_after, content):
            content = re.sub(insert_after, r"\1\n" + section + "\n", content, count=1)
        else:
            content += "\n" + section + "\n"

    safe_write_text_locked(path, content)
    return True


def update_review_summary(
    path: str,
    review_summary: dict[str, Any] | None,
) -> bool:
    """更新审查摘要到 SESSION-STATE.md。"""
    if not ensure_session_state_exists(path) and not os.path.exists(path):
        return False

    with open(path, encoding="utf-8") as f:
        content = f.read()

    review_summary = review_summary or {}
    section = (
        "## 审查摘要\n"
        f"- **review_found**: {review_summary.get('review_found', False)}\n"
        f"- **review_source**: {review_summary.get('review_source', '(未设置)')}\n"
        f"- **review_status**: {review_summary.get('review_status', '(未设置)')}\n"
        f"- **stage_1_status**: {review_summary.get('stage_1_status', '(未设置)')}\n"
        f"- **stage_2_status**: {review_summary.get('stage_2_status', '(未设置)')}\n"
        f"- **risk_level**: {review_summary.get('risk_level', '(未设置)')}\n"
        f"- **verdict**: {review_summary.get('verdict', '(未设置)')}\n"
        f"- **degraded_mode**: {review_summary.get('degraded_mode', False)}\n"
        f"- **files_reviewed**: {review_summary.get('files_reviewed', 0)}\n"
    )

    pattern = r"## 审查摘要\n(?:- \*\*review_found\*\*: .*\n- \*\*review_source\*\*: .*\n- \*\*review_status\*\*: .*\n- \*\*stage_1_status\*\*: .*\n- \*\*stage_2_status\*\*: .*\n- \*\*risk_level\*\*: .*\n- \*\*verdict\*\*: .*\n- \*\*degraded_mode\*\*: .*\n- \*\*files_reviewed\*\*: .*\n)?"
    if re.search(pattern, content):
        content = re.sub(pattern, section, content, count=1)
    else:
        insert_after = r"(\## 恢复摘要\n(?:- \*\*original_session_id\*\*: .*\n- \*\*resume_from\*\*: .*\n- \*\*next_phase\*\*: .*\n- \*\*skill_policy\*\*: .*\n- \*\*use_skill\*\*: .*\n- \*\*skill_activation_level\*\*: .*\n- \*\*complexity\*\*: .*\n- \*\*failure_event_count\*\*: .*\n- \*\*escalation_event_count\*\*: .*\n)?)"
        if re.search(insert_after, content):
            content = re.sub(insert_after, r"\1\n" + section + "\n", content, count=1)
        else:
            content += "\n" + section + "\n"

    safe_write_text_locked(path, content)
    return True


def get_info(path: str, key: str) -> Optional[str]:
    """获取特定信息"""
    if not os.path.exists(path):
        return None

    with open(path, encoding='utf-8') as f:
        content = f.read()

    if key == 'task':
        pattern = r'\*\*任务描述\*\*: (.+)'
        match = re.search(pattern, content)
        return match.group(1) if match else None
    elif key == 'phase':
        pattern = r'\*\*阶段\*\*: (.+)'
        match = re.search(pattern, content)
        return match.group(1) if match else None
    elif key == 'preferences':
        pattern = r'### 用户偏好\n(.*?)(?=\n##|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1) if match else None
    elif key == 'decisions':
        pattern = r'### 决策记录\n(.*?)(?=\n##|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1) if match else None

    return None


def check_idle_status(path: str, idle_threshold_minutes: int = 30) -> dict[str, Any]:
    """
    检查会话空闲状态

    Args:
        path: SESSION-STATE.md 路径
        idle_threshold_minutes: 空闲阈值（分钟）

    Returns:
        {
            "is_idle": True/False,
            "idle_minutes": N,
            "last_active": "ISO timestamp",
            "task_info": {"phase": "...", "progress": N}
        }
    """
    result: dict[str, Any] = {
        "is_idle": False,
        "idle_minutes": 0,
        "last_active": None,
        "task_info": {"phase": "UNKNOWN", "progress": 0}
    }

    if not os.path.exists(path):
        return result

    try:
        with open(path, encoding='utf-8') as f:
            content = f.read()

        # 解析最后活跃时间（从"开始时间"字段）
        start_time_pattern = r'\*\*开始时间\*\*: (.+)'
        match = re.search(start_time_pattern, content)
        if match:
            start_time_str = match.group(1).strip()
            try:
                last_active = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
                result["last_active"] = last_active.isoformat()

                # 计算空闲时间
                now = datetime.now()
                idle_delta = now - last_active
                idle_minutes = int(idle_delta.total_seconds() / 60)
                result["idle_minutes"] = idle_minutes
                result["is_idle"] = idle_minutes >= idle_threshold_minutes
            except ValueError:
                pass

        # 解析任务阶段
        phase_pattern = r'\*\*阶段\*\*: (.+)'
        match = re.search(phase_pattern, content)
        if match:
            result["task_info"]["phase"] = match.group(1).strip()

        # 解析进度
        progress_pattern = r'\*\*进度\*\*: (\d+)'
        match = re.search(progress_pattern, content)
        if match:
            result["task_info"]["progress"] = int(match.group(1))

    except (OSError, UnicodeDecodeError) as e:
        import logging
        logging.warning(f"check_idle_status: 解析失败: {e}")
        pass

    return result


def add_task_result(path: str, task_id: str, status: str,
                    duration_seconds: int, lessons: list,
                    next_actions: list) -> bool:
    """
    追加任务结果到历史记录

    Args:
        path: SESSION-STATE.md 路径（用于验证）
        task_id: 任务ID
        status: 任务状态 (success/partial/failed)
        duration_seconds: 任务耗时（秒）
        lessons: 经验教训列表
        next_actions: 下一步行动列表

    Returns:
        是否成功
    """
    if not _validate_path(path):
        return False

    # 获取项目根目录（session state 所在目录的父目录或同级）
    project_root = os.path.dirname(os.path.abspath(path))
    history_file = os.path.join(project_root, '.task_history.jsonl')

    # 构建记录
    record = {
        "timestamp": datetime.now().isoformat(),
        "task_id": task_id,
        "status": status,
        "duration_seconds": duration_seconds,
        "lessons": lessons,
        "next_actions": next_actions
    }

    try:
        safe_append_jsonl(history_file, record)
        return True
    except (OSError, TypeError) as e:
        import logging
        logging.warning(f"add_task_result: 写入失败: {e}")
        return False


def show_session_state(path: str = DEFAULT_SESSION_STATE) -> None:
    """显示当前 SESSION-STATE 内容"""
    if not os.path.exists(path):
        print(f"SESSION-STATE.md 不存在: {path}")
        print("使用 --op=init 初始化")
        return

    with open(path, encoding='utf-8') as f:
        print(f.read())


def main():
    parser = argparse.ArgumentParser(description='Memory Operations - 记忆操作工具')
    parser.add_argument('--path', default=DEFAULT_SESSION_STATE, help='SESSION-STATE 路径')
    parser.add_argument('--op', choices=['update', 'add', 'get', 'show', 'init', 'resume-point', 'idle-check', 'add-result'], required=True, help='操作类型')
    parser.add_argument('--key', help='更新的键 (task, phase, preferences, decisions)')
    parser.add_argument('--value', help='更新值')
    parser.add_argument('--type', help='添加类型 (correction, preference, decision, value)')
    parser.add_argument('--from', dest='from_val', help='原始值 (用于 correction)')
    parser.add_argument('--to', dest='to_val', help='目标值 (用于 correction)')
    parser.add_argument('--reason', default='', help='决策理由')
    parser.add_argument('--phase', help='中断点阶段 (用于 resume-point)')
    parser.add_argument('--progress', type=int, help='进度百分比 0-100 (用于 resume-point)')
    parser.add_argument('--task-id', help='任务ID (用于 add-result)')
    parser.add_argument('--status', help='任务状态 (用于 add-result): success/partial/failed')
    parser.add_argument('--duration', type=int, help='任务耗时秒 (用于 add-result)')
    parser.add_argument('--lessons', help='经验教训，逗号分隔 (用于 add-result)')
    parser.add_argument('--next-actions', help='下一步行动，逗号分隔 (用于 add-result)')
    parser.add_argument('--idle-threshold', type=int, default=30, help='空闲阈值分钟 (用于 idle-check)')

    args = parser.parse_args()

    if args.op == 'show':
        show_session_state(args.path)
    elif args.op == 'init':
        ensure_session_state_exists(args.path)
        print(f"已初始化: {args.path}")
    elif args.op == 'update':
        if not args.key or not args.value:
            print("错误: --key 和 --value 必须指定")
            return 1
        if args.key == 'task':
            update_task_info(args.path, args.value)
        elif args.key == 'phase':
            # 特殊处理 phase
            ensure_session_state_exists(args.path)
            with open(args.path, encoding='utf-8') as f:
                content = f.read()
            pattern = r'(\*\*阶段\*\*: )(.*)(\n)'
            content = re.sub(pattern, f'\\1{args.value}\\3', content)
            safe_write_text_locked(args.path, content)
        else:
            print(f"未知key: {args.key}")
            return 1
        print(f"已更新: {args.key} = {args.value}")
    elif args.op == 'add':
        if args.type == 'correction':
            if not args.from_val or not args.to_val:
                print("错误: --from 和 --to 必须指定")
                return 1
            add_correction(args.path, args.from_val, args.to_val)
            print(f"已添加修正: {args.from_val} -> {args.to_val}")
        elif args.type == 'preference':
            if not args.key or not args.value:
                print("错误: --key 和 --value 必须指定")
                return 1
            add_preference(args.path, args.key, args.value)
            print(f"已添加偏好: {args.key} = {args.value}")
        elif args.type == 'decision':
            if not args.value:
                print("错误: --value 必须指定")
                return 1
            add_decision(args.path, args.value, args.reason)
            print(f"已添加决策: {args.value}")
        elif args.type == 'value':
            if not args.key or not args.value:
                print("错误: --key 和 --value 必须指定")
                return 1
            add_value(args.path, args.key, args.value)
            print(f"已添加数值: {args.key} = {args.value}")
        else:
            print(f"未知类型: {args.type}")
            return 1
    elif args.op == 'get':
        if not args.key:
            print("错误: --key 必须指定")
            return 1
        result = get_info(args.path, args.key)
        if result:
            print(result)
        else:
            print(f"未找到: {args.key}")
    elif args.op == 'resume-point':
        if not args.phase or args.progress is None:
            print("错误: --phase 和 --progress 必须指定")
            return 1
        if not (0 <= args.progress <= 100):
            print("错误: --progress 必须在 0-100 范围内")
            return 1
        ensure_session_state_exists(args.path)
        if update_resume_point(args.path, args.phase, args.progress):
            print(f"已更新中断点: {args.phase}, 进度: {args.progress}%")
        else:
            print("更新中断点失败")
            return 1
    elif args.op == 'idle-check':
        result = check_idle_status(args.path, args.idle_threshold)
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.op == 'add-result':
        if not args.task_id or not args.status or args.duration is None:
            print("错误: --task-id, --status, --duration 必须指定")
            return 1
        lessons = []
        if args.lessons:
            lessons = [lesson.strip() for lesson in args.lessons.split(',') if lesson.strip()]
        next_actions = []
        if args.next_actions:
            next_actions = [a.strip() for a in args.next_actions.split(',') if a.strip()]
        if add_task_result(args.path, args.task_id, args.status, args.duration, lessons, next_actions):
            print(f"已记录任务结果: {args.task_id}")
        else:
            print("记录任务结果失败")
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
