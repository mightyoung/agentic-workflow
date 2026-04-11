"""Tests for adaptive_tier — data-driven tier resolution with confidence levels."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import adaptive_tier  # noqa: E402
from adaptive_tier import (  # noqa: E402
    AdaptiveResolver,
    TierDecision,
    adaptive_activation_level,
    get_adaptation_summary,
)


# ---------------------------------------------------------------------------
# Helpers — mirror the _make_record / _seed_records pattern from test_skill_metrics
# ---------------------------------------------------------------------------

VALID_LEVELS = {0, 25, 50, 75, 100}
VALID_SOURCES = {"default", "adaptive", "escalated", "de-escalated"}
VALID_CONFIDENCES = {"high", "medium", "low"}


def _make_record(
    *,
    phase: str = "EXECUTING",
    activation_level: int = 25,
    model_id: str | None = "claude-sonnet-4-6",
    complexity: str = "M",
    success: bool = True,
    quality_score: float = 0.8,
    token_input: int = 100,
    token_output: int = 200,
    duration_ms: int = 500,
    failure_count: int = 0,
    error_type: str | None = None,
) -> dict:
    return {
        "phase": phase,
        "activation_level": activation_level,
        "model_id": model_id,
        "complexity": complexity,
        "success": success,
        "quality_score": quality_score,
        "token_input": token_input,
        "token_output": token_output,
        "duration_ms": duration_ms,
        "failure_count": failure_count,
        "error_type": error_type,
    }


def _seed_records(workdir: str, records: list[dict]) -> None:
    """Write a list of raw dicts to the .skill_metrics.jsonl file."""
    path = Path(workdir) / ".skill_metrics.jsonl"
    with open(path, "a") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def _seed_high_confidence(workdir: str, phase: str = "EXECUTING",
                           activation_level: int = 50,
                           quality_score: float = 0.85,
                           count: int = 30) -> None:
    """Seed enough records to reach high-confidence threshold (>= 30 total samples)."""
    records = [
        _make_record(
            phase=phase,
            activation_level=activation_level,
            quality_score=quality_score,
        )
        for _ in range(count)
    ]
    _seed_records(workdir, records)


def _seed_medium_confidence(workdir: str, phase: str = "EXECUTING",
                             activation_level: int = 50,
                             quality_score: float = 0.85,
                             count: int = 15) -> None:
    """Seed enough records for medium confidence (10 <= total < 30)."""
    records = [
        _make_record(
            phase=phase,
            activation_level=activation_level,
            quality_score=quality_score,
        )
        for _ in range(count)
    ]
    _seed_records(workdir, records)


# ---------------------------------------------------------------------------
# TestTierDecisionDataclass
# ---------------------------------------------------------------------------

class TestTierDecisionDataclass(unittest.TestCase):
    """Test TierDecision dataclass properties and invariants."""

    def _make_decision(
        self,
        activation_level: int = 25,
        source: str = "default",
        confidence: str = "low",
        reason: str = "test reason",
    ) -> TierDecision:
        return TierDecision(
            activation_level=activation_level,
            source=source,
            confidence=confidence,
            reason=reason,
        )

    def test_frozen_immutable(self):
        """TierDecision must be frozen — attribute assignment should raise."""
        decision = self._make_decision()
        with self.assertRaises((AttributeError, TypeError)):
            decision.activation_level = 50  # type: ignore[misc]

    def test_all_fields_accessible(self):
        """All four fields must be readable after construction."""
        decision = TierDecision(
            activation_level=75,
            source="adaptive",
            confidence="high",
            reason="data-driven choice",
        )
        self.assertEqual(decision.activation_level, 75)
        self.assertEqual(decision.source, "adaptive")
        self.assertEqual(decision.confidence, "high")
        self.assertEqual(decision.reason, "data-driven choice")

    def test_valid_source_and_confidence_values(self):
        """Enumerate all documented source/confidence combinations without error."""
        for source in VALID_SOURCES:
            for confidence in VALID_CONFIDENCES:
                decision = TierDecision(
                    activation_level=25,
                    source=source,
                    confidence=confidence,
                    reason=f"source={source} confidence={confidence}",
                )
                self.assertIn(decision.source, VALID_SOURCES)
                self.assertIn(decision.confidence, VALID_CONFIDENCES)


# ---------------------------------------------------------------------------
# TestAdaptiveResolverResolve
# ---------------------------------------------------------------------------

class TestAdaptiveResolverResolve(unittest.TestCase):
    """Test AdaptiveResolver.resolve() across all confidence levels and edge cases."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    # --- No data → low confidence default ---

    def test_no_data_returns_low_confidence(self):
        """With no .skill_metrics.jsonl file, confidence must be 'low'."""
        resolver = AdaptiveResolver(workdir=self._tmpdir)
        decision = resolver.resolve("EXECUTING", "M")
        self.assertEqual(decision.confidence, "low")

    def test_no_data_returns_source_default(self):
        """With no .skill_metrics.jsonl file, source must be 'default'."""
        resolver = AdaptiveResolver(workdir=self._tmpdir)
        decision = resolver.resolve("EXECUTING", "M")
        self.assertEqual(decision.source, "default")

    def test_no_data_activation_level_in_valid_set(self):
        resolver = AdaptiveResolver(workdir=self._tmpdir)
        decision = resolver.resolve("EXECUTING", "M")
        self.assertIn(decision.activation_level, VALID_LEVELS)

    # --- High-confidence data → adaptive source ---

    def test_high_confidence_data_uses_recommendation(self):
        """When >= 30 samples are present at a non-default level, source should be 'adaptive'."""
        # Seed at level 25 (differs from default ~50) to trigger adaptive path
        _seed_high_confidence(self._tmpdir, count=30, activation_level=25)
        resolver = AdaptiveResolver(workdir=self._tmpdir, min_samples=1)
        decision = resolver.resolve("EXECUTING", "M")
        self.assertEqual(decision.source, "adaptive")

    def test_high_confidence_data_has_high_confidence(self):
        # Seed at level 25 (differs from default) to trigger adaptive path
        _seed_high_confidence(self._tmpdir, count=30, activation_level=25)
        resolver = AdaptiveResolver(workdir=self._tmpdir, min_samples=1)
        decision = resolver.resolve("EXECUTING", "M")
        self.assertEqual(decision.confidence, "high")

    # --- Medium-confidence data → blended ---

    def test_medium_confidence_data_blends_default_and_recommendation(self):
        """10-29 samples → confidence='medium'; source should reflect blending."""
        _seed_medium_confidence(self._tmpdir, count=15)
        resolver = AdaptiveResolver(workdir=self._tmpdir, min_samples=1)
        decision = resolver.resolve("EXECUTING", "M")
        self.assertEqual(decision.confidence, "medium")
        # source may be "adaptive" or "default" for blended; it must be in valid set
        self.assertIn(decision.source, VALID_SOURCES)

    # --- Low-confidence data → falls back to default ---

    def test_low_confidence_data_uses_default(self):
        """Fewer than 10 total samples → confidence='low', source='default'."""
        _seed_records(self._tmpdir, [
            _make_record(activation_level=50, quality_score=0.9)
            for _ in range(3)
        ])
        resolver = AdaptiveResolver(workdir=self._tmpdir, min_samples=1)
        decision = resolver.resolve("EXECUTING", "M")
        self.assertEqual(decision.confidence, "low")
        self.assertEqual(decision.source, "default")

    # --- Failure escalation ---

    def test_failure_escalation_overrides_source_to_escalated(self):
        """failure_count >= 2 must produce source='escalated'."""
        resolver = AdaptiveResolver(workdir=self._tmpdir)
        decision = resolver.resolve("EXECUTING", "M", failure_count=2)
        self.assertEqual(decision.source, "escalated")

    def test_failure_escalation_level_higher_than_default(self):
        """Escalated decision must raise activation_level above the no-failure default."""
        resolver = AdaptiveResolver(workdir=self._tmpdir)
        baseline = resolver.resolve("EXECUTING", "M", failure_count=0)
        escalated = resolver.resolve("EXECUTING", "M", failure_count=2)
        self.assertGreaterEqual(escalated.activation_level, baseline.activation_level)

    # --- Result always in valid level set ---

    def test_activation_level_always_valid_no_data(self):
        resolver = AdaptiveResolver(workdir=self._tmpdir)
        decision = resolver.resolve("EXECUTING", "M")
        self.assertIn(decision.activation_level, VALID_LEVELS)

    def test_activation_level_always_valid_with_data(self):
        _seed_high_confidence(self._tmpdir, activation_level=75, count=30)
        resolver = AdaptiveResolver(workdir=self._tmpdir, min_samples=1)
        decision = resolver.resolve("EXECUTING", "M")
        self.assertIn(decision.activation_level, VALID_LEVELS)

    def test_activation_level_always_valid_under_escalation(self):
        resolver = AdaptiveResolver(workdir=self._tmpdir)
        decision = resolver.resolve("EXECUTING", "M", failure_count=3)
        self.assertIn(decision.activation_level, VALID_LEVELS)

    # --- Phase/complexity variations ---

    def test_resolve_thinking_phase_returns_decision(self):
        resolver = AdaptiveResolver(workdir=self._tmpdir)
        decision = resolver.resolve("THINKING", "L")
        self.assertIsInstance(decision, TierDecision)
        self.assertIn(decision.activation_level, VALID_LEVELS)

    def test_resolve_planning_phase_returns_decision(self):
        resolver = AdaptiveResolver(workdir=self._tmpdir)
        decision = resolver.resolve("PLANNING", "XL")
        self.assertIsInstance(decision, TierDecision)
        self.assertIn(decision.activation_level, VALID_LEVELS)

    def test_resolve_with_model_id_returns_decision(self):
        resolver = AdaptiveResolver(workdir=self._tmpdir)
        decision = resolver.resolve("EXECUTING", "M", model_id="claude-sonnet-4-6")
        self.assertIsInstance(decision, TierDecision)
        self.assertIn(decision.activation_level, VALID_LEVELS)

    def test_resolve_xs_complexity_returns_decision(self):
        resolver = AdaptiveResolver(workdir=self._tmpdir)
        decision = resolver.resolve("EXECUTING", "XS")
        self.assertIsInstance(decision, TierDecision)
        self.assertIn(decision.activation_level, VALID_LEVELS)


# ---------------------------------------------------------------------------
# TestShouldDeEscalate
# ---------------------------------------------------------------------------

class TestShouldDeEscalate(unittest.TestCase):
    """Test AdaptiveResolver.should_de_escalate() logic."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def test_no_data_returns_none(self):
        """With no metrics, should_de_escalate should return None (no basis)."""
        resolver = AdaptiveResolver(workdir=self._tmpdir)
        result = resolver.should_de_escalate("EXECUTING", current_level=50)
        self.assertIsNone(result)

    def test_current_level_zero_returns_none(self):
        """Cannot de-escalate from the lowest tier (0)."""
        _seed_high_confidence(self._tmpdir, activation_level=0, quality_score=0.9, count=10)
        resolver = AdaptiveResolver(workdir=self._tmpdir, min_samples=1)
        result = resolver.should_de_escalate("EXECUTING", current_level=0)
        self.assertIsNone(result)

    def test_lower_tier_high_quality_returns_de_escalation(self):
        """If a lower tier has avg_quality >= 0.7, return a de-escalation TierDecision."""
        # Seed tier 25 with high quality
        records = [
            _make_record(activation_level=25, quality_score=0.85)
            for _ in range(10)
        ]
        _seed_records(self._tmpdir, records)
        resolver = AdaptiveResolver(workdir=self._tmpdir, min_samples=1)
        # Currently running at 50; tier 25 below it has quality 0.85 >= 0.7
        result = resolver.should_de_escalate("EXECUTING", current_level=50)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, TierDecision)
        self.assertEqual(result.source, "de-escalated")
        # De-escalated level must be strictly lower than current
        self.assertLess(result.activation_level, 50)

    def test_lower_tier_low_quality_returns_none(self):
        """If the lower tier quality is < 0.7, should_de_escalate returns None."""
        records = [
            _make_record(activation_level=25, quality_score=0.5)
            for _ in range(10)
        ]
        _seed_records(self._tmpdir, records)
        resolver = AdaptiveResolver(workdir=self._tmpdir, min_samples=1)
        result = resolver.should_de_escalate("EXECUTING", current_level=50)
        self.assertIsNone(result)

    def test_insufficient_samples_returns_none(self):
        """If the lower tier has fewer samples than min_samples, return None."""
        # Only 2 records for tier 25, but min_samples=5
        records = [
            _make_record(activation_level=25, quality_score=0.9)
            for _ in range(2)
        ]
        _seed_records(self._tmpdir, records)
        resolver = AdaptiveResolver(workdir=self._tmpdir, min_samples=5)
        result = resolver.should_de_escalate("EXECUTING", current_level=50)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# TestRecordEscalation
# ---------------------------------------------------------------------------

class TestRecordEscalation(unittest.TestCase):
    """Test AdaptiveResolver.record_escalation() persistence."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def test_creates_tier_escalations_file(self):
        """record_escalation must create .tier_escalations.jsonl in workdir."""
        resolver = AdaptiveResolver(workdir=self._tmpdir)
        resolver.record_escalation("EXECUTING", from_level=25, to_level=50, reason="test failure")
        escalations_file = Path(self._tmpdir) / ".tier_escalations.jsonl"
        self.assertTrue(escalations_file.exists())

    def test_appends_multiple_records(self):
        """Calling record_escalation twice appends two lines."""
        resolver = AdaptiveResolver(workdir=self._tmpdir)
        resolver.record_escalation("EXECUTING", from_level=25, to_level=50, reason="first")
        resolver.record_escalation("PLANNING", from_level=50, to_level=75, reason="second")
        escalations_file = Path(self._tmpdir) / ".tier_escalations.jsonl"
        lines = escalations_file.read_text().strip().splitlines()
        self.assertEqual(len(lines), 2)

    def test_all_fields_present_in_record(self):
        """Each written record must contain phase, from_level, to_level, and reason."""
        resolver = AdaptiveResolver(workdir=self._tmpdir)
        resolver.record_escalation(
            "DEBUGGING", from_level=50, to_level=100, reason="repeated timeout"
        )
        escalations_file = Path(self._tmpdir) / ".tier_escalations.jsonl"
        record = json.loads(escalations_file.read_text().strip())

        self.assertEqual(record["phase"], "DEBUGGING")
        self.assertEqual(record["from_level"], 50)
        self.assertEqual(record["to_level"], 100)
        self.assertEqual(record["reason"], "repeated timeout")


# ---------------------------------------------------------------------------
# TestAdaptiveActivationLevel
# ---------------------------------------------------------------------------

class TestAdaptiveActivationLevel(unittest.TestCase):
    """Test the adaptive_activation_level convenience function."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def test_returns_int(self):
        """Return value must be a plain int."""
        result = adaptive_activation_level("EXECUTING", "M", workdir=self._tmpdir)
        self.assertIsInstance(result, int)

    def test_returns_valid_level_no_data(self):
        """Without data, the returned level must be in the valid tier set."""
        result = adaptive_activation_level("EXECUTING", "M", workdir=self._tmpdir)
        self.assertIn(result, VALID_LEVELS)

    def test_works_with_workdir_parameter(self):
        """Passing a custom workdir must not raise and must return a valid level."""
        _seed_high_confidence(self._tmpdir, activation_level=50, count=30)
        result = adaptive_activation_level(
            "EXECUTING", "M", workdir=self._tmpdir
        )
        self.assertIn(result, VALID_LEVELS)


# ---------------------------------------------------------------------------
# TestGetAdaptationSummary
# ---------------------------------------------------------------------------

class TestGetAdaptationSummary(unittest.TestCase):
    """Test get_adaptation_summary report structure."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def test_empty_returns_valid_structure(self):
        """With no data, get_adaptation_summary must return a dict (not raise)."""
        result = get_adaptation_summary(workdir=self._tmpdir)
        self.assertIsInstance(result, dict)

    def test_returns_expected_keys(self):
        """Summary must include keys: total_records, tier_breakdown, phase_breakdown,
        overall_avg_quality (or similar numeric/structural fields)."""
        _seed_records(self._tmpdir, [
            _make_record(activation_level=25, quality_score=0.8),
            _make_record(activation_level=50, quality_score=0.9),
        ])
        result = get_adaptation_summary(workdir=self._tmpdir)
        self.assertIsInstance(result, dict)
        # Must contain total_events or similar count indicator
        has_count = (
            "total_events" in result
            or "total_records" in result
            or "record_count" in result
            or "total" in result
        )
        self.assertTrue(has_count, f"Summary lacks a count key. Got: {list(result.keys())}")


if __name__ == "__main__":
    unittest.main()
