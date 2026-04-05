#!/usr/bin/env python3
"""
Reflexion - Self-Reflection for Workflow Error Recovery

Lightweight reflexion pattern for analyzing error patterns and generating
dynamic retry hints based on actual error content.

Usage:
    from reflexion import ReflexionEngine, reflect_on_errors

    engine = ReflexionEngine()
    hint = engine.generate_hint(error_type="test_failure", error="AssertionError: email not found")
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# Error pattern extractors - map regex patterns to hint generators
ERROR_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Test failures - specific assertions
    (re.compile(r"assert.*\(?['\"](\w+(?:\.\w+)*)['\"]?\s*not\s*found", re.I), "check if '{0}' is in test fixture data"),
    (re.compile(r"assert.*['\"](\w+)['\"]\s*==", re.I), "verify test fixture has correct '{0}' value"),
    (re.compile(r"AssertionError:\s*(.+?)(?:\n|$)", re.I), "examine assertion: '{0}' - is the expected value correct?"),
    (re.compile(r"assertEqual\([^,]+,\s*([^)]+)\)", re.I), "check assertEqual argument order (expected vs actual)"),
    (re.compile(r"expected\s+(\w+)\s+but\s+got\s+(\w+)", re.I), "expected '{1}' but got '{2}' - check test setup"),

    # Import/Module errors
    (re.compile(r"ModuleNotFoundError:\s*No\s+module\s+named\s+['\"](\w+)['\"]", re.I), "install missing module: pip install {0}"),
    (re.compile(r"ImportError:\s*cannot\s+import\s+name\s+['\"](\w+)['\"]", re.I), "check if '{0}' is correctly imported from its module"),
    (re.compile(r"No\s+module\s+named\s+['\"](\w+)['\"]", re.I), "module '{0}' not found - check PYTHONPATH or install"),

    # Syntax errors
    (re.compile(r"SyntaxError:\s*(.+?)(?:\n|$)", re.I), "syntax error: {0} - check parentheses/brackets balance"),

    # Type errors
    (re.compile(r"TypeError:\s*(?:.*?\b)?(\w+)\s+\+\s+.*?(\w+)", re.I), "type mismatch: cannot concatenate '{0}' + '{1}' - convert types"),
    (re.compile(r"TypeError:\s*(?:.*?\b)?(\w+)\s*\(\)\s*is\s*not\s*iterable", re.I), "'{0}' is not iterable - check if it's a list/dict/string"),
    (re.compile(r"TypeError:\s*'([^']+)'\s+object\s+is\s+not\s+subscriptable", re.I), "'{0}' is not subscriptable - it may be a primitive type, not a collection"),

    # Name errors
    (re.compile(r"NameError:\s*name\s+['\"](\w+)['\"]\s+is\s+not\s+defined", re.I), "'{0}' is not defined - check spelling or import"),

    # File/path errors
    (re.compile(r"FileNotFoundError:\s*(.+?)(?:\n|$)", re.I), "file not found: {0} - check path is correct"),
    (re.compile(r"No\s+such\s+file\s+or\s+directory:\s*['\"]?([^\'\"\n]+)['\"]?", re.I), "path not found: {0} - verify file exists at that location"),

    # JSON/data errors
    (re.compile(r"JSONDecodeError:\s*(.+?)(?:\n|$)", re.I), "JSON parse error: {0} - check for trailing commas or quotes"),
    (re.compile(r"KeyError:\s*['\"](\w+)['\"]", re.I), "KeyError: '{0}' - key not found in dict, check keys()"),

    # Quality gate failures
    (re.compile(r"quality.*gate.*fail|gate.*quality.*fail", re.I), "run: python3 scripts/quality_gate.py --workdir . to see which checks failed"),
    (re.compile(r"test.*fail|pytest.*fail|fail.*test", re.I), "run: pytest -v to see which specific tests failed"),
]


@dataclass
class ReflexionResult:
    """Result of reflexion analysis"""
    hint: str  # Dynamic retry hint
    pattern: str | None  # Which pattern matched (if any)
    reflection: str  # Human-readable reflection
    is_repeated: bool  # True if same error happened before


class ReflexionEngine:
    """
    Lightweight reflexion engine for workflow error recovery.

    Analyzes error messages to extract specific patterns and generate
    context-aware retry hints instead of generic static messages.
    """

    def __init__(self):
        self.error_history: list[dict[str, Any]] = []

    def reflect(
        self,
        error: str,
        error_type: str,
        context: dict[str, Any] | None = None,
    ) -> ReflexionResult:
        """
        Analyze an error and generate a dynamic reflection.

        Args:
            error: The error message string
            error_type: Classification of error type (from classify_error)
            context: Optional context dict with phase, retry_count, etc.

        Returns:
            ReflexionResult with hint, pattern, reflection, and is_repeated
        """
        context = context or {}
        retry_count = context.get("retry_count", 0)

        # Check for repeated errors
        is_repeated = self._is_repeated_error(error)

        # Record this error
        self.error_history.append({
            "error": error,
            "error_type": error_type,
            "timestamp": datetime.now().isoformat(),
            "retry_count": retry_count,
        })
        # Keep only last 10
        if len(self.error_history) > 10:
            self.error_history = self.error_history[-10:]

        # Try to match error patterns
        hint, pattern_name = self._extract_hint(error)

        # Build reflection string
        if is_repeated:
            reflection = f"Repeated {error_type} (attempt {retry_count + 1}): {error[:100]}"
        else:
            reflection = f"New {error_type}: {error[:100]}"

        return ReflexionResult(
            hint=hint,
            pattern=pattern_name,
            reflection=reflection,
            is_repeated=is_repeated,
        )

    def _is_repeated_error(self, error: str) -> bool:
        """Check if this error pattern has occurred before"""
        # Normalize error for comparison (truncate, lowercase)
        normalized = error[:100].lower()
        for past in self.error_history[-5:]:
            past_normalized = past["error"][:100].lower()
            if normalized == past_normalized:
                return True
            # Also check if same error type and very similar
            if past["error_type"] == "test_failure" and "assert" in normalized and "assert" in past_normalized:
                return True
        return False

    def _extract_hint(self, error: str) -> tuple[str, str | None]:
        """Extract a context-aware hint from the error message"""
        for pattern, hint_template in ERROR_PATTERNS:
            match = pattern.search(error)
            if match:
                try:
                    hint = hint_template.format(*match.groups())
                except (IndexError, KeyError):
                    hint = hint_template.format(*match.groups(), **{})
                return hint, pattern.pattern[:50]
        return "", None


def reflect_on_errors(
    error: str,
    error_type: str,
    context: dict[str, Any] | None = None,
) -> ReflexionResult:
    """
    Standalone function for reflecting on workflow errors.

    This is the primary entry point for handle_workflow_failure to use
    instead of static retry hints.

    Args:
        error: The error message
        error_type: Error classification (test_failure, syntax_error, etc.)
        context: Optional dict with phase, retry_count, session_id

    Returns:
        ReflexionResult with dynamic hint based on error analysis
    """
    engine = ReflexionEngine()
    return engine.reflect(error, error_type, context)
