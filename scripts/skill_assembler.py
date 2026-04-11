#!/usr/bin/env python3
"""
Skill Assembler — gradient-based skill prompt injection.

Replaces the flat PHASE_PROMPTS dict with a tiered file-based system:
  - tier_core.md     (25%) — method skeleton + iron law (~100 tokens)
  - tier_process.md  (50%) — key steps + decision points (~400 tokens)
  - tier_full.md     (75%) — full methodology (~1000 tokens)
  - tier_reference.md(100%) — examples + edge cases (~2000 tokens)

Each activation_level loads the corresponding tiers cumulatively.

Usage:
    from skill_assembler import assemble_skill_prompt

    prompt, token_est = assemble_skill_prompt(
        phase="EXECUTING",
        activation_level=50,
    )
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

# Tier definitions: (level_threshold, filename, description)
TIERS = [
    (25, "tier_core.md", "method skeleton + iron law"),
    (50, "tier_process.md", "key steps + decision points"),
    (75, "tier_full.md", "full methodology"),
    (100, "tier_reference.md", "examples + edge cases"),
]

# Phase name normalization
_PHASE_DIR_MAP: dict[str, str] = {
    "EXECUTING": "executing",
    "DEBUGGING": "debugging",
    "THINKING": "thinking",
    "PLANNING": "planning",
    "REVIEWING": "reviewing",
    "RESEARCH": "research",
    "REFINING": "refining",
    "EXPLORING": "exploring",
    "COMPLETE": "complete",
    "OFFICE_HOURS": "office-hours",
}

# Rough token-per-char ratio for estimation (conservative)
_CHARS_PER_TOKEN = 3.5


def _skills_dir() -> Path:
    """Resolve the skills directory relative to this script."""
    return Path(__file__).resolve().parent.parent / "skills"


def _load_tier_file(phase_dir: str, tier_filename: str) -> str | None:
    """Load a single tier file, returning None if not found."""
    path = _skills_dir() / phase_dir / tier_filename
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def load_tiers(phase: str, activation_level: int) -> list[str]:
    """Load tier contents up to the given activation level.

    Args:
        phase: Phase name (e.g., "EXECUTING")
        activation_level: 0-100, determines which tiers to include

    Returns:
        List of tier content strings, ordered from core to reference.
    """
    phase_upper = (phase or "").upper()
    phase_dir = _PHASE_DIR_MAP.get(phase_upper)
    if not phase_dir:
        return []

    activation_level = max(0, min(100, activation_level))
    contents: list[str] = []

    for threshold, filename, _desc in TIERS:
        if activation_level < threshold:
            break
        content = _load_tier_file(phase_dir, filename)
        if content:
            contents.append(content)

    return contents


def merge_tiers(tier_contents: list[str]) -> str:
    """Merge tier contents with minimal separators."""
    return "\n\n".join(tier_contents)


def estimate_tokens(text: str) -> int:
    """Rough token count estimate from character count."""
    if not text:
        return 0
    return max(1, int(len(text) / _CHARS_PER_TOKEN))


# ---------------------------------------------------------------------------
# Format adapters — extensible for multi-LLM support (Phase 2)
# ---------------------------------------------------------------------------

class FormatAdapter(Protocol):
    """Protocol for LLM-specific prompt formatting."""

    def format(self, content: str, phase: str) -> str:
        """Format skill content for a specific LLM family."""
        ...


class MarkdownAdapter:
    """Default adapter — passes through markdown as-is.

    Works well for Claude, GPT-4, Gemini Pro.
    """

    def format(self, content: str, phase: str) -> str:
        return content


class XMLAdapter:
    """Wraps content in XML tags — better for some instruction-following models."""

    def format(self, content: str, phase: str) -> str:
        return f"<skill-context phase=\"{phase}\">\n{content}\n</skill-context>"


class PlainAdapter:
    """Strips markdown formatting — for local/smaller models."""

    def format(self, content: str, phase: str) -> str:
        import re
        # Remove markdown headers
        text = re.sub(r"^#{1,6}\s+", "", content, flags=re.MULTILINE)
        # Remove bold/italic markers
        text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
        # Remove code block markers
        text = re.sub(r"```[\w]*\n?", "", text)
        # Remove HTML comments
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        return text.strip()


# Adapter registry
_ADAPTERS: dict[str, FormatAdapter] = {
    "markdown": MarkdownAdapter(),
    "xml": XMLAdapter(),
    "plain": PlainAdapter(),
}


def get_adapter(format_name: str = "markdown") -> FormatAdapter:
    """Get a format adapter by name, defaulting to markdown."""
    return _ADAPTERS.get(format_name, _ADAPTERS["markdown"])


# ---------------------------------------------------------------------------
# Main assembly function
# ---------------------------------------------------------------------------

def assemble_skill_prompt(
    phase: str,
    activation_level: int,
    format_name: str = "markdown",
    model_id: str | None = None,
) -> tuple[str, int]:
    """Assemble a skill prompt from tiered files.

    Args:
        phase: Phase name (e.g., "EXECUTING")
        activation_level: 0-100, determines tier depth
        format_name: Output format ("markdown", "xml", "plain").
            If "auto", resolves from model_profiles using model_id.
        model_id: Optional model identifier for auto format/level resolution.

    Returns:
        (formatted_prompt, estimated_tokens)
    """
    # Auto-resolve format from model profile when requested
    if format_name == "auto" and model_id:
        try:
            from model_profiles import get_profile
            profile = get_profile(model_id)
            format_name = profile.format
        except (ImportError, Exception):
            format_name = "markdown"

    if activation_level <= 0:
        return "", 0

    tier_contents = load_tiers(phase, activation_level)
    if not tier_contents:
        return "", 0

    merged = merge_tiers(tier_contents)
    adapter = get_adapter(format_name)
    formatted = adapter.format(merged, phase)
    tokens = estimate_tokens(formatted)

    return formatted, tokens


def available_phases() -> list[str]:
    """Return list of phases that have tier files."""
    skills_dir = _skills_dir()
    phases = []
    for phase_upper, phase_dir in sorted(_PHASE_DIR_MAP.items()):
        tier_path = skills_dir / phase_dir / "tier_core.md"
        if tier_path.is_file():
            phases.append(phase_upper)
    return phases


def tier_summary(phase: str) -> dict[str, int]:
    """Return token estimates for each tier of a phase."""
    phase_upper = (phase or "").upper()
    phase_dir = _PHASE_DIR_MAP.get(phase_upper)
    if not phase_dir:
        return {}

    result: dict[str, int] = {}
    cumulative = ""
    for threshold, filename, desc in TIERS:
        content = _load_tier_file(phase_dir, filename)
        if content:
            cumulative = cumulative + "\n\n" + content if cumulative else content
            result[f"{threshold}%"] = estimate_tokens(cumulative)
        else:
            result[f"{threshold}%"] = result.get(f"{threshold - 25}%", 0)

    return result


# ---------------------------------------------------------------------------
# CLI for inspection
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Skill Assembler — inspect tier content")
    parser.add_argument("--phase", required=True, help="Phase name (e.g., EXECUTING)")
    parser.add_argument("--level", type=int, default=50, help="Activation level (0-100)")
    parser.add_argument("--format", default="markdown", choices=["markdown", "xml", "plain"])
    parser.add_argument("--op", default="assemble", choices=["assemble", "summary", "phases"])
    args = parser.parse_args()

    if args.op == "phases":
        print(json.dumps(available_phases(), indent=2))
    elif args.op == "summary":
        print(json.dumps(tier_summary(args.phase), indent=2))
    else:
        prompt, tokens = assemble_skill_prompt(args.phase, args.level, args.format)
        if prompt:
            print(prompt)
            print(f"\n--- Estimated tokens: {tokens} ---")
        else:
            print(f"No tier content found for phase={args.phase} level={args.level}")


if __name__ == "__main__":
    main()
