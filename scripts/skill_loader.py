#!/usr/bin/env python3
"""
Skill Loader - Skill.md to Executable Prompt Template

Loads skill.md files and converts them into executable prompt templates
that can guide AI behavior during workflow phases.

Usage:
    from skill_loader import SkillLoader

    loader = SkillLoader(skills_dir="skills")
    skill = loader.load_skill("thinking")

    # Get formatted prompt for current context
    prompt = skill.get_phase_prompt(
        task="实现 REST API",
        context={"errors": [], "files": []},
        session_id="abc123"
    )

    # Check if exit criteria are met
    can_exit = skill.check_exit_criteria(
        artifacts=["findings.md"],
        decisions=["选择方案A"]
    )
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Template variable pattern: {{variable_name}}
TEMPLATE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


@dataclass
class SkillMetadata:
    """Parsed YAML frontmatter from skill.md"""
    name: str
    version: str
    status: str  # "implemented", "experimental", "planned"
    description: str
    tags: list[str] = field(default_factory=list)
    requires: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExitCriteria:
    """Machine-readable exit criteria"""
    conditions: list[str] = field(default_factory=list)  # Human-readable conditions
    # For programmatic checking, each condition can have a check function
    required_artifacts: list[str] = field(default_factory=list)
    required_decisions: int = 0  # Minimum number of decisions to have made


@dataclass
class Skill:
    """
    Loaded skill with executable prompt template.

    Attributes:
        metadata: Parsed frontmatter
        phase_name: Name of the phase (e.g., "THINKING", "DEBUGGING")
        overview: The ## Overview section content
        entry_criteria: Human-readable entry criteria
        exit_criteria: Structured exit criteria
        core_process: The ## Core Process section content
        phase_prompt_template: Template string for the main prompt
        completion_template: Template for completion report
        raw_content: Original markdown content
    """
    metadata: SkillMetadata
    phase_name: str
    overview: str
    entry_criteria: str
    exit_criteria: ExitCriteria
    core_process: str
    phase_prompt_template: str
    completion_template: str
    raw_content: str


class SkillLoader:
    """
    Loads and parses skill.md files into executable Skill objects.

    The loader understands the skill.md format:
    - YAML frontmatter with metadata
    - Markdown sections (## headers)
    - Template variables in {{variable}} format
    """

    SKILL_FILE = "skill.md"
    SKILLS_DIR = "skills"

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)

    def load_skill(self, phase_name: str) -> Skill | None:
        """
        Load a skill by phase name.

        Args:
            phase_name: Name like "thinking", "debugging", "planning"

        Returns:
            Skill object or None if not found
        """
        skill_path = self.skills_dir / phase_name.lower() / self.SKILL_FILE
        if not skill_path.exists():
            return None

        content = skill_path.read_text(encoding="utf-8")
        return self.parse_skill_md(phase_name.upper(), content)

    def load_all_skills(self) -> dict[str, Skill]:
        """Load all available skills."""
        skills: dict[str, Skill] = {}
        if not self.skills_dir.exists():
            return skills

        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / self.SKILL_FILE).exists():
                skill = self.load_skill(skill_dir.name)
                if skill:
                    skills[skill.phase_name] = skill

        return skills

    def parse_skill_md(self, phase_name: str, content: str) -> Skill | None:
        """
        Parse skill.md content into a Skill object.

        Args:
            phase_name: Phase name (e.g., "THINKING")
            content: Raw markdown content

        Returns:
            Parsed Skill or None if parsing fails
        """
        # Split frontmatter from content
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        frontmatter = parts[1].strip()
        markdown = parts[2].strip()

        # Parse YAML frontmatter
        metadata = self._parse_frontmatter(frontmatter)
        if not metadata:
            return None

        # Parse markdown sections
        sections = self._extract_sections(markdown)

        # Extract key sections
        overview = sections.get("Overview", "")
        entry_criteria = sections.get("Entry Criteria", sections.get("Entry Criteria\n" + "-" * 20, ""))
        core_process = sections.get("Core Process", "")
        completion_template = sections.get("Completion Status Protocol", sections.get("Output Format", ""))

        # Build phase prompt template from Core Process
        phase_prompt = self._build_phase_prompt_template(
            phase_name, overview, core_process, sections
        )

        # Parse exit criteria
        exit_criteria = self._parse_exit_criteria(sections.get("Exit Criteria", ""))

        return Skill(
            metadata=metadata,
            phase_name=phase_name,
            overview=overview,
            entry_criteria=entry_criteria,
            exit_criteria=exit_criteria,
            core_process=core_process,
            phase_prompt_template=phase_prompt,
            completion_template=completion_template,
            raw_content=markdown,
        )

    def _parse_frontmatter(self, frontmatter: str) -> SkillMetadata | None:
        """Parse YAML frontmatter into SkillMetadata."""
        metadata: dict[str, Any] = {
            "name": "",
            "version": "1.0.0",
            "status": "unknown",
            "description": "",
            "tags": [],
            "requires": {},
        }

        for line in frontmatter.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if ":|" in line:
                # Multiline value
                key = line.split(":|")[0].strip()
                # Get value from next lines (indented)
                continue
            elif ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip().strip("'\"")

                if key == "name":
                    metadata["name"] = value
                elif key == "version":
                    metadata["version"] = value
                elif key == "status":
                    metadata["status"] = value
                elif key == "description":
                    metadata["description"] = value
                elif key == "tags":
                    # Parse list like [phase, thinking, expert-reasoning]
                    if value.startswith("["):
                        tags_str = value.strip("[]")
                        metadata["tags"] = [t.strip() for t in tags_str.split(",")]
                elif key == "requires":
                    # Skip complex requires parsing for now
                    pass

        if not metadata["name"]:
            return None

        return SkillMetadata(
            name=metadata["name"],
            version=metadata["version"],
            status=metadata["status"],
            description=metadata["description"],
            tags=metadata["tags"],
            requires=metadata["requires"],
        )

    def _extract_sections(self, markdown: str) -> dict[str, str]:
        """Extract ## headers and their content as sections."""
        sections: dict[str, str] = {}
        current_section: str | None = None
        current_content: list[str] = []

        for line in markdown.split("\n"):
            if line.startswith("## "):
                # Save previous section
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()

                # Start new section
                current_section = line[3:].strip()
                current_content = []
            elif current_section is not None:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _build_phase_prompt_template(
        self,
        phase_name: str,
        overview: str,
        core_process: str,
        sections: dict[str, str],
    ) -> str:
        """
        Build a prompt template from skill sections.

        Template variables:
            {{task}} - The task description
            {{session_id}} - Current session ID
            {{context}} - Additional context dict
            {{artifacts}} - Related artifacts
            {{decisions}} - Recent decisions
        """
        parts = [
            f"# {phase_name} Phase",
            "",
            "## Overview",
            overview,
            "",
        ]

        # Add entry criteria
        entry = sections.get("Entry Criteria", "")
        if entry:
            parts.extend(["## Entry Criteria", entry, ""])

        # Add core process
        if core_process:
            parts.extend(["## Core Process", core_process, ""])

        # Add key subsections from Core Process
        for step_num in range(1, 7):
            step_key = f"Step {step_num}"
            if step_key in sections:
                parts.extend([f"### {step_key}", sections[step_key], ""])

        # Add PUA激励 if present
        pua = sections.get("PUA 激励引擎", "")
        if pua:
            parts.extend(["## PUA 激励引擎", pua, ""])

        # Add completion format
        completion = sections.get("Completion Status Protocol", "")
        if completion:
            parts.extend(["## Completion Protocol", completion, ""])

        return "\n".join(parts)

    def _parse_exit_criteria(self, text: str) -> ExitCriteria:
        """
        Parse exit criteria text into structured ExitCriteria.

        Currently extracts simple patterns. Can be extended for more complex parsing.
        """
        conditions = []
        required_artifacts = []
        required_decisions = 0

        # Extract lines that look like criteria
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Lines starting with - or containing "must" or "should"
            if line.startswith("-") or "must" in line.lower() or "should" in line.lower():
                conditions.append(line)

            # Look for artifact mentions
            if "artifacts" in line.lower() or "file" in line.lower():
                # Try to extract artifact names
                matches = re.findall(r"`([^`]+)`", line)
                required_artifacts.extend(matches)

        return ExitCriteria(
            conditions=conditions,
            required_artifacts=required_artifacts,
            required_decisions=required_decisions,
        )


class SkillPromptFormatter:
    """
    Formats skill prompts with actual context values.

    Usage:
        formatter = SkillPromptFormatter(skill)
        prompt = formatter.format(
            task="实现 REST API",
            session_id="abc123",
            context={"errors": [], "files": ["src/api.py"]},
            artifacts=["findings.md"],
            decisions=["选择方案A"],
        )
    """

    def __init__(self, skill: Skill):
        self.skill = skill

    def format(
        self,
        task: str,
        session_id: str = "",
        context: dict[str, Any] | None = None,
        artifacts: list[str] | None = None,
        decisions: list[str] | None = None,
        **extra_vars: Any,
    ) -> str:
        """
        Format the skill's phase prompt template with actual values.

        Args:
            task: The task description
            session_id: Current session ID
            context: Additional context dict
            artifacts: List of artifact names/paths
            decisions: List of decision strings
            **extra_vars: Additional variables to substitute

        Returns:
            Formatted prompt string
        """
        context = context or {}
        artifacts = artifacts or []
        decisions = decisions or []

        # Build substitution dict
        substitutions = {
            "task": task,
            "session_id": session_id,
            "context": self._format_context(context),
            "artifacts": self._format_list(artifacts),
            "decisions": self._format_list(decisions),
            "timestamp": datetime.now().isoformat(),
        }
        substitutions.update(extra_vars)

        # Substitute template variables
        prompt = self.skill.phase_prompt_template

        for match in TEMPLATE_PATTERN.finditer(prompt):
            var_name = match.group(1)
            if var_name in substitutions:
                prompt = prompt.replace(match.group(0), str(substitutions[var_name]))

        return prompt

    def _format_context(self, context: dict[str, Any]) -> str:
        """Format context dict as readable string."""
        if not context:
            return "No additional context"
        parts = []
        for key, value in context.items():
            parts.append(f"- {key}: {value}")
        return "\n".join(parts) if parts else "No additional context"

    def _format_list(self, items: list[str]) -> str:
        """Format list as readable string."""
        if not items:
            return "None"
        return "\n".join(f"- {item}" for item in items)


def load_skill(phase: str, skills_dir: str = "skills") -> Skill | None:
    """
    Convenience function to load a skill by phase name.

    Args:
        phase: Phase name (e.g., "THINKING", "thinking")
        skills_dir: Path to skills directory

    Returns:
        Skill object or None
    """
    loader = SkillLoader(skills_dir)
    return loader.load_skill(phase.upper().replace("-", "_"))


def format_skill_prompt(
    phase: str,
    task: str,
    session_id: str = "",
    context: dict[str, Any] | None = None,
    skills_dir: str = "skills",
    **extra_vars: Any,
) -> str | None:
    """
    Convenience function to load and format a skill prompt in one call.

    Args:
        phase: Phase name
        task: Task description
        session_id: Session ID
        context: Additional context
        skills_dir: Path to skills directory
        **extra_vars: Additional template variables

    Returns:
        Formatted prompt or None if skill not found
    """
    skill = load_skill(phase, skills_dir)
    if not skill:
        return None

    formatter = SkillPromptFormatter(skill)
    return formatter.format(
        task=task,
        session_id=session_id,
        context=context,
        **extra_vars,
    )


# CLI entry point for testing
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Skill Loader CLI")
    parser.add_argument("--phase", required=True, help="Phase name (e.g., thinking)")
    parser.add_argument("--task", default="测试任务", help="Task description")
    parser.add_argument("--session-id", default="test-session", help="Session ID")
    parser.add_argument("--skills-dir", default="skills", help="Skills directory")
    parser.add_argument("--list", action="store_true", help="List all available skills")
    parser.add_argument("--show-prompt", action="store_true", help="Show formatted prompt")

    args = parser.parse_args()

    loader = SkillLoader(args.skills_dir)

    if args.list:
        skills = loader.load_all_skills()
        print(json.dumps(
            {name: {"version": s.metadata.version, "status": s.metadata.status}
             for name, s in skills.items()},
            indent=2,
            ensure_ascii=False,
        )
        )
    else:
        skill = loader.load_skill(args.phase)
        if not skill:
            print(f"Skill not found: {args.phase}")
            raise SystemExit(1)

        print(f"Loaded: {skill.metadata.name} v{skill.metadata.version}")
        print(f"Status: {skill.metadata.status}")
        print(f"Description: {skill.metadata.description}")
        print()

        if args.show_prompt:
            formatter = SkillPromptFormatter(skill)
            prompt = formatter.format(
                task=args.task,
                session_id=args.session_id,
            )
            print(prompt)
