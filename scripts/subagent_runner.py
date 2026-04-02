#!/usr/bin/env python3
"""
SubAgent Runner - Real AI Subagent Spawning

Spawns real AI subagents using skill prompts + Claude CLI.
This connects skill_loader prompts to actual AI execution.

Usage:
    from subagent_runner import SubAgentRunner, SubAgentResult

    runner = SubAgentRunner(workdir=".", skills_dir="skills")

    # Run a thinking subagent
    result = runner.run(
        phase="THINKING",
        task="分析这个REST API架构设计",
        session_id="abc123"
    )

    if result.success:
        print(result.output)
    else:
        print(f"Error: {result.error}")

    # Run with custom prompt override
    result = runner.run(
        phase="DEBUGGING",
        task="修复登录bug",
        session_id="abc123",
        prompt_override="Focus on authentication issues..."
    )
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from skill_loader import SkillPromptFormatter, load_skill


@dataclass
class SubAgentResult:
    """Result from a subagent execution"""
    success: bool
    output: str = ""
    error: str = ""
    phase: str = ""
    session_id: str = ""
    duration_seconds: float = 0.0
    artifacts: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SubAgentRunner:
    """
    Spawns real AI subagents using skill prompts.

    Uses Claude CLI (claude -p) for AI execution when available,
    with graceful fallback to skill-formatted prompts only.
    """

    def __init__(
        self,
        workdir: str = ".",
        skills_dir: str = "skills",
        claude_bin: str = "claude",  # Path to claude CLI
        timeout: int = 120,  # seconds
    ):
        self.workdir = Path(workdir)
        self.skills_dir = Path(skills_dir)
        self.claude_bin = claude_bin
        self.timeout = timeout
        self._claude_available: bool | None = None

    def check_claude_available(self) -> bool:
        """Check if Claude CLI is available"""
        if self._claude_available is not None:
            return self._claude_available
        try:
            result = subprocess.run(
                [self.claude_bin, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            self._claude_available = result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            self._claude_available = False
        return self._claude_available

    def run(
        self,
        phase: str,
        task: str,
        session_id: str = "",
        context: dict[str, Any] | None = None,
        prompt_override: str | None = None,
        output_file: str | None = None,
    ) -> SubAgentResult:
        """
        Run a subagent for the given phase and task.

        Args:
            phase: Phase name (e.g., "THINKING", "DEBUGGING")
            task: Task description
            session_id: Session ID for artifact naming
            context: Additional context dict
            prompt_override: Override the default skill prompt
            output_file: Optional file path to write output

        Returns:
            SubAgentResult with execution results
        """
        start_time = datetime.now()
        phase_upper = phase.upper()
        session_id = session_id or f"sub{start_time.strftime('%Y%m%d%H%M%S')}"

        # Build the prompt
        if prompt_override:
            prompt = prompt_override
        else:
            skill = load_skill(phase_upper, str(self.skills_dir))
            if skill:
                formatter = SkillPromptFormatter(skill)
                prompt = formatter.format(
                    task=task,
                    session_id=session_id,
                    context=context or {},
                )
            else:
                # Fallback if skill not found
                prompt = f"# {phase_upper} Phase\n\n## Task\n{task}\n\nPlease analyze and provide recommendations."

        # Check if Claude CLI is available
        if self.check_claude_available():
            return self._run_with_claude(
                prompt, phase_upper, session_id, output_file, start_time
            )
        else:
            return self._run_fallback(
                prompt, phase_upper, session_id, output_file, start_time
            )

    def _run_with_claude(
        self,
        prompt: str,
        phase: str,
        session_id: str,
        output_file: str | None,
        start_time: datetime,
    ) -> SubAgentResult:
        """Run using Claude CLI"""
        duration = 0.0
        error = ""

        try:
            # Write prompt to temp file (Claude CLI accepts input via stdin)
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.md',
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(prompt)
                prompt_file = f.name

            try:
                # Run Claude CLI with the prompt
                result = subprocess.run(
                    [self.claude_bin, "-p", prompt_file],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=str(self.workdir),
                )

                if result.returncode == 0:
                    output = result.stdout
                    success = True
                else:
                    output = ""
                    error = result.stderr or f"Claude CLI exited with code {result.returncode}"
                    success = False

            finally:
                # Clean up temp file
                Path(prompt_file).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            output = ""
            error = f"Claude CLI timed out after {self.timeout}s"
            success = False
        except Exception as e:
            output = ""
            error = str(e)
            success = False

        duration = (datetime.now() - start_time).total_seconds()

        # Write output to file if specified
        output_path = None
        if output_file and output:
            output_path = self.workdir / output_file
            output_path.write_text(output, encoding='utf-8')

        artifacts = [str(output_path)] if output_path else []

        return SubAgentResult(
            success=success,
            output=output,
            error=error,
            phase=phase,
            session_id=session_id,
            duration_seconds=duration,
            artifacts=artifacts,
            metadata={"claude_used": True},
        )

    def _run_fallback(
        self,
        prompt: str,
        phase: str,
        session_id: str,
        output_file: str | None,
        start_time: datetime,
    ) -> SubAgentResult:
        """
        Fallback when Claude CLI is not available.

        Writes the skill prompt to a file for manual review,
        does NOT generate AI output.
        """
        duration = (datetime.now() - start_time).total_seconds()

        # Write prompt to artifact file
        prompt_artifact = self.workdir / f"subagent_prompt_{phase.lower()}_{session_id}.md"
        prompt_artifact.write_text(prompt, encoding='utf-8')

        output = (
            f"# SubAgent Runner - Claude CLI Not Available\n\n"
            f"Phase: {phase}\n"
            f"Session: {session_id}\n\n"
            f"The skill prompt has been written to:\n{prompt_artifact}\n\n"
            f"To execute this subagent, run:\n"
            f"  claude -p {prompt_artifact}\n\n"
            f"Or install Claude CLI: https://docs.anthropic.com/claude-cli"
        )

        return SubAgentResult(
            success=False,
            output=output,
            error="Claude CLI not available",
            phase=phase,
            session_id=session_id,
            duration_seconds=duration,
            artifacts=[str(prompt_artifact)],
            metadata={
                "claude_used": False,
                "fallback": True,
                "prompt_artifact": str(prompt_artifact),
            },
        )

    def run_parallel(
        self,
        tasks: list[dict[str, Any]],
        phase: str,
        session_id: str = "",
    ) -> list[SubAgentResult]:
        """
        Run multiple subagents in parallel.

        Args:
            tasks: List of {"task": str, "context": dict, "output_file": str}
            phase: Phase name
            session_id: Base session ID

        Returns:
            List of SubAgentResult
        """
        results = []
        for i, t in enumerate(tasks):
            task_id = f"{session_id}_{i}" if session_id else f"task_{i}"
            result = self.run(
                phase=phase,
                task=t["task"],
                session_id=task_id,
                context=t.get("context"),
                output_file=t.get("output_file"),
            )
            results.append(result)
        return results


def run_subagent(
    phase: str,
    task: str,
    workdir: str = ".",
    skills_dir: str = "skills",
    session_id: str = "",
    **kwargs: Any,
) -> SubAgentResult:
    """
    Convenience function to run a single subagent.

    Usage:
        result = run_subagent("THINKING", "分析这个架构设计")
    """
    runner = SubAgentRunner(workdir=workdir, skills_dir=skills_dir)
    return runner.run(
        phase=phase,
        task=task,
        session_id=session_id,
        **kwargs,
    )


# CLI entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SubAgent Runner CLI")
    parser.add_argument("--phase", required=True, help="Phase name (e.g., THINKING, DEBUGGING)")
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--workdir", default=".", help="Working directory")
    parser.add_argument("--skills-dir", default="skills", help="Skills directory")
    parser.add_argument("--session-id", default="", help="Session ID")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--check", action="store_true", help="Check Claude CLI availability")

    args = parser.parse_args()

    runner = SubAgentRunner(workdir=args.workdir, skills_dir=args.skills_dir)

    if args.check:
        available = runner.check_claude_available()
        print(f"Claude CLI available: {available}")
        raise SystemExit(0 if available else 1)

    result = runner.run(
        phase=args.phase,
        task=args.task,
        session_id=args.session_id,
        output_file=args.output,
    )

    print(f"Success: {result.success}")
    print(f"Phase: {result.phase}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    if result.error:
        print(f"Error: {result.error}")
    if result.artifacts:
        print(f"Artifacts: {result.artifacts}")
    print()
    print("=" * 60)
    print(result.output[:2000] if result.output else "(no output)")
    if len(result.output) > 2000:
        print(f"... ({len(result.output) - 2000} more characters)")
