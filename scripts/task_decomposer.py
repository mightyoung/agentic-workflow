#!/usr/bin/env python3
"""
Task Decomposer - 任务分解器

从"模板生成"升级为真正的任务分解：
- 自动生成任务ID (T{timestamp}-{counter})
- 自动检测任务依赖
- 自动分配优先级
- 追踪owned files
- 检测文件冲突
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from safe_io import safe_write_json


@dataclass
class DecomposedTask:
    """分解后的任务"""
    task_id: str
    title: str
    description: str = ""
    status: str = "backlog"
    priority: str = "P1"
    owned_files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    verification: str = ""
    created_at: str = ""
    completed_at: Optional[str] = None
    progress: int = 0
    phase: str = "EXECUTING"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "owned_files": self.owned_files,
            "dependencies": self.dependencies,
            "verification": self.verification,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "progress": self.progress,
            "phase": self.phase,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DecomposedTask:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# 文件模式 - 用于检测任务可能涉及的文件
FILE_PATTERNS = {
    "test": [r"_test\.py$", r"test_.+\.py$", r"tests?/.+\.py$"],
    "source": [r"\.py$", r"\.js$", r"\.ts$", r"\.go$", r"\.rs$", r"\.java$"],
    "config": [r"\.json$", r"\.yaml$", r"\.yml$", r"\.toml$", r"\.ini$", r"\.env"],
    "docs": [r"\.md$", r"\.txt$", r"\.rst$", r"\.pdf$"],
    "db": [r"\.sql$", r"migrations?/", r"schema"],
}


def detect_file_types(text: str) -> Set[str]:
    """从文本中检测文件类型"""
    found = set()
    text_lower = text.lower()

    for file_type, patterns in FILE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                found.add(file_type)

    return found


def extract_owned_files(text: str) -> List[str]:
    """从文本中提取可能涉及的文件"""
    files = set()

    # 匹配引号内的文件路径
    path_patterns = [
        r'["\']([a-zA-Z0-9_\-./]+\.(py|js|ts|go|rs|java|json|yaml|yml|md|txt))["\']',
        r'`([a-zA-Z0-9_\-./]+\.(py|js|ts|go|rs|java|json|yaml|yml|md|txt))`',
        r'(?:file|path)[:\s]+([a-zA-Z0-9_\-./]+)',
    ]

    for pattern in path_patterns:
        matches = re.findall(pattern, text)
        files.update(matches)

    # 移除不合理的路径
    filtered = []
    for f in files:
        if not f.startswith(".") and "/" not in f and "\\" not in f:
            if len(f) > 3:
                filtered.append(f)

    return list(files)


def suggest_verification(task: DecomposedTask) -> str:
    """根据任务内容建议验证方式"""
    title_lower = task.title.lower()
    desc_lower = task.description.lower()
    combined = title_lower + " " + desc_lower

    # 基于关键词推断验证方式
    if any(k in combined for k in ["test", "测试", "单元测试"]):
        return f"pytest tests/test_{task.task_id.lower()}.py -v"
    if any(k in combined for k in ["api", "endpoint", "接口"]):
        return "curl localhost:PORT/api/test"
    if any(k in combined for k in ["build", "编译", "打包"]):
        return f"python3 -m py_compile {task.owned_files[0] if task.owned_files else 'main.py'}"
    if any(k in combined for k in ["deploy", "部署"]):
        return "kubectl apply -f deployment.yaml"
    if any(k in combined for k in ["config", "配置"]):
        return f"cat {task.owned_files[0] if task.owned_files else 'config.json'} | python3 -m json.tool"

    # 无法推断验证方式 - 返回空字符串，让任务状态反映这一点
    # 调用方应该检查 verification 是否为空，并据此设置任务状态
    return ""


def generate_task_id(counter: int, base_timestamp: Optional[str] = None) -> str:
    """生成任务ID"""
    ts = base_timestamp or datetime.now().strftime("%Y%m%d%H%M%S")
    return f"T{ts}-{counter:03d}"


def detect_dependencies(
    tasks: List[DecomposedTask],
    all_text: str,
) -> List[DecomposedTask]:
    """
    检测任务之间的依赖关系

    基于:
    1. 文件引用关系
    2. 任务标题关键词
    3. 任务描述中的引用
    """
    # 构建文件->任务的映射
    file_to_tasks: Dict[str, List[str]] = {}
    for task in tasks:
        for f in task.owned_files:
            normalized = f.lower().replace("\\", "/")
            if normalized not in file_to_tasks:
                file_to_tasks[normalized] = []
            file_to_tasks[normalized].append(task.task_id)

    # 关键词依赖推断
    dependency_rules = {
        "setup": [],
        "config": ["setup"],
        "test": ["implementation", "source", "config"],
        "integration": ["implementation", "test"],
        "deploy": ["implementation", "test", "config"],
        "api": ["model", "schema", "config"],
        "model": ["schema", "config"],
        "database": ["config", "model"],
        "frontend": ["api", "model"],
        "backend": ["model", "database", "api"],
    }

    # 检测隐含依赖
    for task in tasks:
        title_lower = task.title.lower()
        desc_lower = task.description.lower()
        combined = title_lower + " " + desc_lower

        # 基于关键词规则推断
        for keyword, deps in dependency_rules.items():
            if keyword in combined:
                for dep in deps:
                    for other_task in tasks:
                        if other_task.task_id == task.task_id:
                            continue
                        other_lower = other_task.title.lower()
                        if dep in other_lower and other_task.task_id not in task.dependencies:
                            task.dependencies.append(other_task.task_id)

    return tasks


def detect_file_conflicts(tasks: List[DecomposedTask]) -> List[Dict[str, Any]]:
    """
    检测文件冲突

    同一文件被多个任务修改可能需要串行执行
    """
    file_tasks: Dict[str, List[str]] = {}

    for task in tasks:
        for f in task.owned_files:
            if f not in file_tasks:
                file_tasks[f] = []
            file_tasks[f].append(task.task_id)

    conflicts = []
    for file_path, task_ids in file_tasks.items():
        if len(task_ids) > 1:
            conflicts.append({
                "file": file_path,
                "tasks": task_ids,
                "severity": "high" if len(task_ids) > 2 else "medium",
                "suggestion": "Consider serializing these tasks or combining them",
            })

    return conflicts


def auto_priority(task: DecomposedTask, index: int, total: int) -> str:
    """
    基于任务位置和内容自动分配优先级

    Args:
        task: 任务
        index: 在列表中的位置
        total: 总任务数
    """
    title_lower = task.title.lower()
    desc_lower = task.description.lower()
    combined = title_lower + " " + desc_lower

    # 核心任务P0
    core_keywords = ["core", "main", "principal", "essential", "核心", "主要", "必须"]
    if any(k in combined for k in core_keywords):
        return "P0"

    # 设置/配置P1
    setup_keywords = ["setup", "config", "install", "init", "initialize", "安装", "配置", "初始化"]
    if any(k in combined for k in setup_keywords):
        return "P1"

    # 测试/文档P2
    support_keywords = ["test", "doc", "readme", "example", "test", "测试", "文档"]
    if any(k in combined for k in support_keywords):
        return "P2"

    # 前20%任务优先
    if index < total * 0.2:
        return "P0"
    if index < total * 0.5:
        return "P1"

    return "P2"


def decompose(
    prompt: str,
    base_timestamp: Optional[str] = None,
    existing_files: Optional[List[str]] = None,
) -> List[DecomposedTask]:
    """
    分解任务

    Args:
        prompt: 用户需求描述
        base_timestamp: 可选的时间戳基础
        existing_files: 已存在的文件列表（用于检测冲突）

    Returns:
        分解后的任务列表
    """
    ts = base_timestamp or datetime.now().strftime("%Y%m%d%H%M%S")
    tasks: List[DecomposedTask] = []

    # 简单的基于关键词的任务拆分
    # 实际实现应该使用LLM进行更智能的拆分
    sections = _split_into_sections(prompt)

    for i, section in enumerate(sections):
        task_id = generate_task_id(i, ts)
        title = _extract_title(section)
        description = section

        owned_files = extract_owned_files(section)

        task = DecomposedTask(
            task_id=task_id,
            title=title or f"Task {task_id}",
            description=description,
            owned_files=owned_files,
            created_at=datetime.now().isoformat(),
            phase="EXECUTING",
        )

        task.verification = suggest_verification(task)
        task.priority = auto_priority(task, i, len(sections))

        tasks.append(task)

    # 检测依赖
    tasks = detect_dependencies(tasks, prompt)

    # 检测文件冲突
    conflicts = detect_file_conflicts(tasks)
    if conflicts:
        # 记录冲突但不自动解决
        pass

    return tasks


def _split_into_sections(prompt: str) -> List[str]:
    """
    将prompt拆分成多个可独立执行的部分

    简单实现：基于段落和分隔符拆分
    实际应该使用LLM
    """
    # 移除多余空白
    prompt = re.sub(r'\s+', ' ', prompt).strip()

    # 尝试按句子拆分
    sentences = re.split(r'[。；\n]', prompt)

    sections = []
    current_section = ""

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue

        # 如果句子太短或包含关键词，添加到当前section
        keywords = ["并且", "同时", "另外", "此外", "还有", "and", "also", "then"]
        if len(sent) < 50 or any(k in sent.lower() for k in keywords):
            current_section += sent + " "
        else:
            if current_section:
                sections.append(current_section.strip())
            current_section = sent + " "

    if current_section:
        sections.append(current_section.strip())

    # 如果拆分太少或太多，按更细粒度拆分
    if len(sections) < 2:
        # 按逗号拆分
        parts = re.split(r'[,，]', prompt)
        if len(parts) >= 2:
            sections = [p.strip() for p in parts if p.strip()]
        else:
            sections = [prompt]

    return sections


def _extract_title(section: str) -> str:
    """从section中提取标题"""
    # 移除常见前缀
    section = re.sub(r'^(实现|开发|创建|编写|完成|修复|添加|设计|配置|测试|编写)\s*', '', section)

    # 取前50字符
    title = section[:50]
    if len(section) > 50:
        title += "..."

    return title


def render_task_plan(tasks: List[DecomposedTask], prompt: str) -> str:
    """
    将任务渲染为task_plan.md格式
    """
    lines = [
        "# Task Plan",
        "",
        "## Summary",
        "",
        f"{prompt}",
        "",
        "## Goals",
        "",
        "- [ ] 完成所有分解任务",
        "",
        "## Task Breakdown",
        "",
    ]

    # 按优先级分组
    by_priority: Dict[str, List[DecomposedTask]] = {"P0": [], "P1": [], "P2": [], "P3": []}
    for task in tasks:
        p = task.priority if task.priority in by_priority else "P2"
        by_priority[p].append(task)

    for priority in ["P0", "P1", "P2", "P3"]:
        priority_tasks = by_priority.get(priority, [])
        if not priority_tasks:
            continue

        lines.append(f"### {priority}")
        lines.append("")
        for task in priority_tasks:
            deps_str = f" (depends on: {', '.join(task.dependencies)})" if task.dependencies else ""
            lines.append(f"- [ ] {task.task_id}: {task.title}{deps_str}")
            if task.description:
                lines.append(f"  - {task.description}")
            if task.owned_files:
                lines.append(f"  - owned_files: {', '.join(task.owned_files)}")
            if task.verification:
                lines.append(f"  - verification: `{task.verification}`")
            lines.append("")

    lines.append("## Risks")
    lines.append("")
    lines.append("- [ ] 待评估")
    lines.append("")
    lines.append("## Verification")
    lines.append("")
    lines.append("- [ ] 所有P0任务完成")
    lines.append("- [ ] 所有P1任务完成")
    lines.append("- [ ] 端到端测试通过")

    return "\n".join(lines)


def save_tasks_json(tasks: List[DecomposedTask], workdir: str, session_id: str) -> Path:
    """保存任务为JSON格式"""
    path = Path(workdir) / f".tasks_{session_id}.json"

    data = {
        "version": "1.0",
        "session_id": session_id,
        "updated_at": datetime.now().isoformat(),
        "tasks": [t.to_dict() for t in tasks],
    }

    safe_write_json(path, data)

    return path


def load_tasks_json(workdir: str, session_id: str) -> List[DecomposedTask]:
    """加载JSON格式的任务"""
    path = Path(workdir) / f".tasks_{session_id}.json"
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return [DecomposedTask.from_dict(t) for t in data.get("tasks", [])]


def extract_user_stories(spec_content: str) -> List[Dict[str, str]]:
    """
    Extract user stories from spec.md content.

    Returns list of dicts with keys: id, title, as_a, i_want, so_that, acceptance_criteria
    """
    stories = []
    # Match ### Story N: Title pattern
    story_pattern = re.compile(r"### Story (\d+):\s*([^\n]+)")
    # Match acceptance criteria blocks
    acceptance_pattern = re.compile(r"\*\*Acceptance Criteria:\*\*\s*\n((?:\s*-\s*[^\n]+\n)+)", re.MULTILINE)
    # Match As a / I want / So that
    story_block_pattern = re.compile(
        r"### Story (\d+):\s*([^\n]+)\n"
        r"\*\*As a\*\*\s+([^\n]+)\n"
        r"\*\*I want\*\*\s+([^\n]+)\n"
        r"\*\*So that\*\*\s+([^\n]+)",
        re.MULTILINE
    )

    # Find all story blocks
    for match in story_block_pattern.finditer(spec_content):
        story_id = match.group(1)
        title = match.group(2).strip()
        as_a = match.group(3).strip()
        i_want = match.group(4).strip()
        so_that = match.group(5).strip()

        # Find acceptance criteria after this story
        story_start = match.end()
        next_story_match = story_pattern.search(spec_content, match.end())
        story_end = next_story_match.start() if next_story_match else len(spec_content)
        story_text = spec_content[story_start:story_end]

        acceptance_criteria = []
        for criteria_match in acceptance_pattern.finditer(story_text):
            criteria_lines = criteria_match.group(1).strip().split("\n")
            for line in criteria_lines:
                # Extract criterion text
                criterion = re.sub(r"^\s*-\s*", "", line).strip()
                criterion = re.sub(r"^\[?\s*[xX ]\s*\]?\s*", "", criterion).strip()
                if criterion and criterion != "[verifiable outcome]":
                    acceptance_criteria.append(criterion)

        stories.append({
            "id": story_id,
            "title": title,
            "as_a": as_a,
            "i_want": i_want,
            "so_that": so_that,
            "acceptance_criteria": acceptance_criteria,
        })

    return stories


def decompose_from_spec(workdir: str, feature_id: str = "default") -> List[DecomposedTask]:
    """
    Decompose tasks from spec.md using user story based splitting.

    Creates tasks organized by:
    - Setup tasks (infrastructure)
    - Foundational tasks (shared components)
    - Per-user-story tasks
    - Polish tasks (docs, finalization)

    Args:
        workdir: Working directory
        feature_id: Feature identifier for spec directory

    Returns:
        List of DecomposedTask organized by user stories
    """
    spec_path = Path(workdir) / ".specs" / feature_id / "spec.md"
    if not spec_path.exists():
        # Fall back to simple decomposition
        return decompose(f"Implement feature from {spec_path}")

    spec_content = spec_path.read_text(encoding="utf-8")
    stories = extract_user_stories(spec_content)

    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    tasks: List[DecomposedTask] = []

    # Counter for task IDs
    counter = 1

    # Create Setup tasks
    setup_keywords = ["setup", "install", "initialize", "configuration", "环境", "安装", "初始化"]
    has_setup = any(k in spec_content.lower() for k in setup_keywords)
    if has_setup:
        task_id = f"T{ts}-{counter:03d}"
        counter += 1
        tasks.append(DecomposedTask(
            task_id=task_id,
            title="Setup and Initialization",
            description="Setup development environment and dependencies",
            status="backlog",
            priority="P0",
            owned_files=["requirements.txt", "pyproject.toml", ".env"],
            verification="pip install -r requirements.txt",
            created_at=datetime.now().isoformat(),
            phase="EXECUTING",
        ))

    # Create Foundational tasks (shared components)
    foundational_keywords = ["model", "schema", "database", "core", "shared", "common"]
    has_foundational = any(k in spec_content.lower() for k in foundational_keywords)
    if has_foundational:
        task_id = f"T{ts}-{counter:03d}"
        counter += 1
        tasks.append(DecomposedTask(
            task_id=task_id,
            title="Foundational Components",
            description="Implement shared/core components needed by all features",
            status="backlog",
            priority="P0",
            owned_files=["src/core/", "src/shared/"],
            verification="pytest tests/test_core.py -v",
            created_at=datetime.now().isoformat(),
            phase="EXECUTING",
        ))

    # Create tasks for each user story
    for story in stories:
        story_id = story["id"]
        story_title = story["title"]

        # Story implementation task
        task_id = f"T{ts}-{counter:03d}"
        counter += 1
        files = f"src/features/story_{story_id}/"
        tasks.append(DecomposedTask(
            task_id=f"US{story_id}-1",
            title=f"User Story {story_id}: {story_title}",
            description=f"As a {story['as_a']}, I want {story['i_want']} so that {story['so_that']}",
            status="backlog",
            priority="P1",
            owned_files=[files],
            verification=f"pytest tests/features/story_{story_id}/ -v",
            created_at=datetime.now().isoformat(),
            phase="EXECUTING",
        ))

        # Add acceptance criteria as subtasks
        for i, criteria in enumerate(story["acceptance_criteria"][:3], start=2):
            task_id = f"T{ts}-{counter:03d}"
            counter += 1
            tasks.append(DecomposedTask(
                task_id=f"US{story_id}-{i}",
                title=f"Acceptance: {criteria[:50]}",
                description=criteria,
                status="backlog",
                priority="P1",
                owned_files=[files],
                verification=f"pytest tests/features/story_{story_id}/ -v",
                created_at=datetime.now().isoformat(),
                phase="EXECUTING",
                dependencies=[f"US{story_id}-1"] if i > 1 else [],
            ))

    # Create Polish tasks
    polish_keywords = ["docs", "readme", "documentation", "example", "polish"]
    has_polish = any(k in spec_content.lower() for k in polish_keywords)
    if has_polish or len(stories) > 0:
        task_id = f"T{ts}-{counter:03d}"
        counter += 1
        tasks.append(DecomposedTask(
            task_id=task_id,
            title="Documentation and Polish",
            description="Finalize documentation, examples, and polish",
            status="backlog",
            priority="P2",
            owned_files=["README.md", "docs/"],
            verification="pytest tests/ -v",
            created_at=datetime.now().isoformat(),
            phase="EXECUTING",
        ))

    # Add dependencies between foundational and story tasks
    found_idx = None
    for i, t in enumerate(tasks):
        if t.title == "Foundational Components":
            found_idx = i
            break

    for i, t in enumerate(tasks):
        if t.title.startswith("User Story"):
            if found_idx is not None and not t.dependencies:
                t.dependencies.append(tasks[found_idx].task_id)
        elif t.title == "Documentation and Polish":
            # Polish depends on all story tasks
            for other in tasks:
                if other.title.startswith("User Story"):
                    if other.task_id not in t.dependencies:
                        t.dependencies.append(other.task_id)

    return tasks


def generate_tasks_md(tasks: List[DecomposedTask], spec_path: str, session_id: str, feature_id: str) -> str:
    """
    Generate tasks.md content following spec-kit template.

    Args:
        tasks: List of DecomposedTask
        spec_path: Path to source spec.md
        session_id: Session identifier
        feature_id: Feature identifier

    Returns:
        tasks.md content as string
    """
    lines = [
        "# Tasks",
        "",
        "> **Provenance Header**",
        "> Generated-By: agentic-workflow",
        f"> Session: {session_id}",
        f"> Source-Spec: {spec_path}",
        f"> Timestamp: {datetime.now().isoformat()}",
        "",
        "---",
        "",
    ]

    # Group tasks by category
    setup_tasks = [t for t in tasks if "setup" in t.title.lower()]
    found_tasks = [t for t in tasks if "foundational" in t.title.lower() or "core" in t.title.lower()]
    story_tasks = [t for t in tasks if t.task_id.startswith("US")]
    polish_tasks = [t for t in tasks if "polish" in t.title.lower() or "documentation" in t.title.lower()]

    if setup_tasks:
        lines.append("## Setup\n")
        for task in setup_tasks:
            lines.append(f"- [ ] **{task.task_id}:** {task.title}")
            lines.append(f"  - **Files:** `{', '.join(task.owned_files)}`")
            lines.append(f"  - **Verification:** `[P]` {task.verification}")
            if task.dependencies:
                lines.append(f"  - **Blocked-By:** {', '.join(task.dependencies)}")
            lines.append("")

    if found_tasks:
        lines.append("## Foundational\n")
        for task in found_tasks:
            lines.append(f"- [ ] **{task.task_id}:** {task.title}")
            lines.append(f"  - **Files:** `{', '.join(task.owned_files)}`")
            lines.append(f"  - **Verification:** `[P]` {task.verification}")
            if task.dependencies:
                lines.append(f"  - **Blocked-By:** {', '.join(task.dependencies)}")
            lines.append("")

    # Group story tasks by story ID
    story_groups: Dict[str, List[DecomposedTask]] = {}
    for task in story_tasks:
        story_match = re.match(r"US(\d+)", task.task_id)
        if story_match:
            story_num = story_match.group(1)
            if story_num not in story_groups:
                story_groups[story_num] = []
            story_groups[story_num].append(task)

    for story_num in sorted(story_groups.keys(), key=int):
        story_tasks_in_group = story_groups[story_num]
        lines.append(f"## User Story {story_num}\n")
        for task in story_tasks_in_group:
            marker = "[P]" if task.priority == "P1" else ""
            lines.append(f"- [ ] **{task.task_id}:** {task.title} {marker}".strip())
            lines.append(f"  - **Files:** `{', '.join(task.owned_files)}`")
            lines.append(f"  - **Verification:** {task.verification}")
            if task.dependencies:
                lines.append(f"  - **Blocked-By:** {', '.join(task.dependencies)}")
            if task.description and len(task.description) > 10:
                lines.append(f"  - **Acceptance:** {task.description[:100]}")
            lines.append("")

    if polish_tasks:
        lines.append("## Polish\n")
        for task in polish_tasks:
            lines.append(f"- [ ] **{task.task_id}:** {task.title}")
            lines.append(f"  - **Files:** `{', '.join(task.owned_files)}`")
            lines.append(f"  - **Verification:** {task.verification}")
            if task.dependencies:
                lines.append(f"  - **Blocked-By:** {', '.join(task.dependencies)}")
            lines.append("")

    lines.append("---\n")
    lines.append("\n## Task Provenance\n")
    lines.append("| Task ID | Source | Story | Created |")
    lines.append("|---------|--------|-------|---------|")
    for task in tasks:
        source = "spec" if task.task_id.startswith("US") else "auto"
        story = f"US-{task.task_id.split('-')[0][2:]}" if task.task_id.startswith("US") else "-"
        lines.append(f"| {task.task_id} | {source} | {story} | {task.created_at[:10]} |")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Task Decomposer")
    parser.add_argument("--prompt", required=True, help="task description")
    parser.add_argument("--workdir", default=".", help="workspace directory")
    parser.add_argument("--session-id", help="session id for saving tasks")
    parser.add_argument("--output", choices=["json", "markdown"], default="markdown", help="output format")
    parser.add_argument("--timestamp", help="base timestamp for task IDs")
    parser.add_argument("--from-spec", action="store_true", help="decompose from spec.md instead of prompt")
    parser.add_argument("--feature-id", default="default", help="feature id for spec directory")
    args = parser.parse_args()

    if args.from_spec:
        tasks = decompose_from_spec(args.workdir, args.feature_id)
    else:
        tasks = decompose(args.prompt, base_timestamp=args.timestamp)

    if args.output == "json":
        print(json.dumps([t.to_dict() for t in tasks], ensure_ascii=False, indent=2))
    else:
        print(render_task_plan(tasks, args.prompt))

    if args.session_id:
        path = save_tasks_json(tasks, args.workdir, args.session_id)
        print(f"\nTasks saved to: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
