#!/usr/bin/env python3
"""
Model Profiles — LLM capability registry for skill tier routing.

Maps model identifiers to capability scores, default activation tiers,
and prompt format preferences. Used by skill_assembler and runtime_profile
to adapt skill injection depth to the target LLM.

Usage:
    from model_profiles import get_profile, resolve_activation_level

    profile = get_profile("claude-sonnet-4-6")
    level = resolve_activation_level("EXECUTING", "M", profile)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelProfile:
    """Immutable LLM capability profile."""

    family: str            # "claude", "openai", "google", "local"
    model_id: str          # canonical model identifier
    capability_score: int  # 0-100, higher = more capable
    default_tier: int      # default activation_level for this model
    format: str            # preferred prompt format: "markdown", "xml", "plain"
    context_window: int    # max tokens (informational, not enforced here)
    cost_per_1k_input: float   # USD per 1K input tokens (for ROI analysis)
    cost_per_1k_output: float  # USD per 1K output tokens


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, ModelProfile] = {
    # --- Claude family ---
    "claude-opus-4-6": ModelProfile(
        family="claude", model_id="claude-opus-4-6",
        capability_score=95, default_tier=0, format="markdown",
        context_window=200_000, cost_per_1k_input=15.0, cost_per_1k_output=75.0,
    ),
    "claude-sonnet-4-6": ModelProfile(
        family="claude", model_id="claude-sonnet-4-6",
        capability_score=90, default_tier=25, format="markdown",
        context_window=200_000, cost_per_1k_input=3.0, cost_per_1k_output=15.0,
    ),
    "claude-haiku-4-5": ModelProfile(
        family="claude", model_id="claude-haiku-4-5",
        capability_score=75, default_tier=50, format="markdown",
        context_window=200_000, cost_per_1k_input=0.80, cost_per_1k_output=4.0,
    ),
    # Aliases for common ID variants
    "claude-opus-4-6-20250414": ModelProfile(
        family="claude", model_id="claude-opus-4-6",
        capability_score=95, default_tier=0, format="markdown",
        context_window=200_000, cost_per_1k_input=15.0, cost_per_1k_output=75.0,
    ),
    "claude-sonnet-4-6-20250414": ModelProfile(
        family="claude", model_id="claude-sonnet-4-6",
        capability_score=90, default_tier=25, format="markdown",
        context_window=200_000, cost_per_1k_input=3.0, cost_per_1k_output=15.0,
    ),
    "claude-haiku-4-5-20251001": ModelProfile(
        family="claude", model_id="claude-haiku-4-5",
        capability_score=75, default_tier=50, format="markdown",
        context_window=200_000, cost_per_1k_input=0.80, cost_per_1k_output=4.0,
    ),

    # --- OpenAI family ---
    "gpt-4o": ModelProfile(
        family="openai", model_id="gpt-4o",
        capability_score=88, default_tier=25, format="markdown",
        context_window=128_000, cost_per_1k_input=2.50, cost_per_1k_output=10.0,
    ),
    "gpt-4o-mini": ModelProfile(
        family="openai", model_id="gpt-4o-mini",
        capability_score=70, default_tier=50, format="markdown",
        context_window=128_000, cost_per_1k_input=0.15, cost_per_1k_output=0.60,
    ),
    "o3": ModelProfile(
        family="openai", model_id="o3",
        capability_score=92, default_tier=0, format="markdown",
        context_window=200_000, cost_per_1k_input=10.0, cost_per_1k_output=40.0,
    ),
    "o3-mini": ModelProfile(
        family="openai", model_id="o3-mini",
        capability_score=78, default_tier=50, format="markdown",
        context_window=200_000, cost_per_1k_input=1.10, cost_per_1k_output=4.40,
    ),
    "o4-mini": ModelProfile(
        family="openai", model_id="o4-mini",
        capability_score=82, default_tier=25, format="markdown",
        context_window=200_000, cost_per_1k_input=1.10, cost_per_1k_output=4.40,
    ),

    # --- Google family ---
    "gemini-2.5-pro": ModelProfile(
        family="google", model_id="gemini-2.5-pro",
        capability_score=88, default_tier=25, format="markdown",
        context_window=1_000_000, cost_per_1k_input=1.25, cost_per_1k_output=10.0,
    ),
    "gemini-2.5-flash": ModelProfile(
        family="google", model_id="gemini-2.5-flash",
        capability_score=72, default_tier=50, format="markdown",
        context_window=1_000_000, cost_per_1k_input=0.15, cost_per_1k_output=0.60,
    ),

    # --- Local / open-weight models ---
    "llama-3.1-70b": ModelProfile(
        family="local", model_id="llama-3.1-70b",
        capability_score=60, default_tier=75, format="plain",
        context_window=128_000, cost_per_1k_input=0.0, cost_per_1k_output=0.0,
    ),
    "qwen-2.5-72b": ModelProfile(
        family="local", model_id="qwen-2.5-72b",
        capability_score=62, default_tier=75, format="plain",
        context_window=128_000, cost_per_1k_input=0.0, cost_per_1k_output=0.0,
    ),
    "deepseek-v3": ModelProfile(
        family="local", model_id="deepseek-v3",
        capability_score=65, default_tier=75, format="markdown",
        context_window=128_000, cost_per_1k_input=0.0, cost_per_1k_output=0.0,
    ),
    "deepseek-r1": ModelProfile(
        family="local", model_id="deepseek-r1",
        capability_score=72, default_tier=50, format="markdown",
        context_window=128_000, cost_per_1k_input=0.0, cost_per_1k_output=0.0,
    ),
}

# Fallback profile for unknown models
_FALLBACK = ModelProfile(
    family="unknown", model_id="unknown",
    capability_score=70, default_tier=50, format="markdown",
    context_window=128_000, cost_per_1k_input=1.0, cost_per_1k_output=5.0,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_profile(model_id: str | None = None) -> ModelProfile:
    """Look up a model profile by ID.

    Falls back to env var AGENTIC_WORKFLOW_MODEL, then to a safe default.
    """
    model_id = model_id or os.environ.get("AGENTIC_WORKFLOW_MODEL", "")
    if not model_id:
        return _FALLBACK

    # Exact match
    if model_id in _REGISTRY:
        return _REGISTRY[model_id]

    # Prefix match (e.g., "claude-sonnet-4" matches "claude-sonnet-4-6")
    model_lower = model_id.lower()
    for key, profile in _REGISTRY.items():
        if key.startswith(model_lower) or model_lower.startswith(key):
            return profile

    return _FALLBACK


def resolve_activation_level(
    phase: str,
    complexity: str,
    profile: ModelProfile | None = None,
    failure_count: int = 0,
) -> int:
    """Compute activation level from model capability + task complexity + failure history.

    The formula balances three signals:
    1. Model default_tier (weaker models get more guidance)
    2. Task complexity (harder tasks get more guidance)
    3. Failure escalation (repeated failures step up)
    """
    if profile is None:
        profile = _FALLBACK

    phase = (phase or "").upper()
    complexity = (complexity or "").upper()

    # Start from model's default tier
    base = profile.default_tier

    # Complexity adjustment
    complexity_boost = {
        "XS": -25,  # Simple tasks can use less
        "S": 0,
        "M": 0,
        "L": 25,
        "XL": 25,
    }.get(complexity, 0)

    # Phase-specific adjustment
    # THINKING/RESEARCH/PLANNING: these phases benefit less from skill injection
    # for strong models, but weak models still need guidance
    phase_adjustment = 0
    if phase in {"THINKING", "RESEARCH", "PLANNING"}:
        if profile.capability_score >= 85:
            phase_adjustment = -25  # Strong models need less guidance here
    elif phase in {"EXECUTING", "DEBUGGING"}:
        # Execution phases always benefit from structured guidance
        phase_adjustment = 0

    # Failure escalation: +25 per failure, up to +75
    failure_boost = min(75, failure_count * 25)

    level = base + complexity_boost + phase_adjustment + failure_boost

    # Clamp to valid range [0, 100]
    return max(0, min(100, level))


def list_models(family: str | None = None) -> list[ModelProfile]:
    """List all registered model profiles, optionally filtered by family."""
    seen: set[str] = set()
    result: list[ModelProfile] = []
    for profile in _REGISTRY.values():
        if profile.model_id in seen:
            continue
        if family and profile.family != family:
            continue
        seen.add(profile.model_id)
        result.append(profile)
    result.sort(key=lambda p: (-p.capability_score, p.model_id))
    return result


def register_model(model_id: str, profile: ModelProfile) -> None:
    """Register or override a model profile at runtime."""
    _REGISTRY[model_id] = profile


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Model Profiles — inspect LLM capability registry")
    parser.add_argument("--op", default="list", choices=["list", "get", "resolve"])
    parser.add_argument("--model", default=None, help="Model ID")
    parser.add_argument("--family", default=None, help="Filter by family")
    parser.add_argument("--phase", default="EXECUTING")
    parser.add_argument("--complexity", default="M")
    parser.add_argument("--failures", type=int, default=0)
    args = parser.parse_args()

    if args.op == "list":
        models = list_models(args.family)
        for m in models:
            print(f"  {m.model_id:30s}  cap={m.capability_score:3d}  tier={m.default_tier:3d}  fmt={m.format:10s}  ${m.cost_per_1k_input:.2f}/{m.cost_per_1k_output:.2f}")
    elif args.op == "get":
        p = get_profile(args.model)
        print(json.dumps({
            "model_id": p.model_id, "family": p.family,
            "capability_score": p.capability_score, "default_tier": p.default_tier,
            "format": p.format, "context_window": p.context_window,
        }, indent=2))
    elif args.op == "resolve":
        p = get_profile(args.model)
        level = resolve_activation_level(args.phase, args.complexity, p, args.failures)
        print(f"model={p.model_id} phase={args.phase} complexity={args.complexity} "
              f"failures={args.failures} → activation_level={level}")


if __name__ == "__main__":
    main()
