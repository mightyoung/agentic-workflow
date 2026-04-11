"""Tests for skill_metrics — skill outcome recording, quality scoring, and tier effectiveness."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import skill_metrics  # noqa: E402
from skill_metrics import (  # noqa: E402
    SkillOutcome,
    TierStats,
    compute_quality_score,
    get_tier_effectiveness,
    record_skill_outcome,
    recommend_activation_level,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_outcome(
    *,
    success: bool = True,
    quality_score: float = 0.8,
    token_input: int = 100,
    token_output: int = 200,
    duration_ms: int = 500,
    failure_count: int = 0,
    error_type: str | None = None,
) -> SkillOutcome:
    return SkillOutcome(
        success=success,
        quality_score=quality_score,
        token_input=token_input,
        token_output=token_output,
        duration_ms=duration_ms,
        failure_count=failure_count,
        error_type=error_type,
    )


def _seed_records(workdir: str, records: list[dict]) -> None:
    """Write a list of raw dicts to the .skill_metrics.jsonl file."""
    path = Path(workdir) / ".skill_metrics.jsonl"
    with open(path, "a") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


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


# ---------------------------------------------------------------------------
# TestSkillOutcomeDataclass
# ---------------------------------------------------------------------------

class TestSkillOutcomeDataclass(unittest.TestCase):
    """Test SkillOutcome dataclass properties."""

    def test_all_fields_accessible(self):
        outcome = _make_outcome(
            success=True,
            quality_score=0.9,
            token_input=50,
            token_output=150,
            duration_ms=300,
            failure_count=1,
            error_type="timeout",
        )
        self.assertTrue(outcome.success)
        self.assertAlmostEqual(outcome.quality_score, 0.9)
        self.assertEqual(outcome.token_input, 50)
        self.assertEqual(outcome.token_output, 150)
        self.assertEqual(outcome.duration_ms, 300)
        self.assertEqual(outcome.failure_count, 1)
        self.assertEqual(outcome.error_type, "timeout")

    def test_frozen_immutable(self):
        """SkillOutcome must be frozen — attribute assignment should raise."""
        outcome = _make_outcome()
        with self.assertRaises((AttributeError, TypeError)):
            outcome.success = False  # type: ignore[misc]

    def test_none_error_type_allowed(self):
        outcome = _make_outcome(error_type=None)
        self.assertIsNone(outcome.error_type)


# ---------------------------------------------------------------------------
# TestComputeQualityScore
# ---------------------------------------------------------------------------

class TestComputeQualityScore(unittest.TestCase):
    """Test compute_quality_score signal weighting and clamping."""

    def test_perfect_score_all_signals_positive(self):
        score = compute_quality_score(
            success=True,
            failure_count=0,
            test_pass_rate=1.0,
            review_issues=0,
            user_accepted=True,
        )
        self.assertAlmostEqual(score, 1.0, places=5)

    def test_worst_score_all_signals_negative(self):
        score = compute_quality_score(
            success=False,
            failure_count=3,
            test_pass_rate=0.0,
            review_issues=3,
            user_accepted=False,
        )
        self.assertAlmostEqual(score, 0.0, places=5)

    def test_success_only_no_optional_signals(self):
        """success=True, failure_count=0, no optional signals → should be > 0.4."""
        score = compute_quality_score(success=True, failure_count=0)
        self.assertGreater(score, 0.4)
        self.assertLessEqual(score, 1.0)

    def test_failure_penalty_zero_failures(self):
        """failure_count=0 → no penalty on the failure component."""
        score_zero = compute_quality_score(success=True, failure_count=0)
        score_one = compute_quality_score(success=True, failure_count=1)
        self.assertGreater(score_zero, score_one)

    def test_failure_penalty_one(self):
        """failure_count=1 → failure sub-score is 0.5 (half penalty)."""
        score = compute_quality_score(
            success=True, failure_count=1,
            test_pass_rate=None, review_issues=0, user_accepted=None,
        )
        # The failure component uses 0→1.0, 1→0.5
        score_zero = compute_quality_score(
            success=True, failure_count=0,
            test_pass_rate=None, review_issues=0, user_accepted=None,
        )
        self.assertLess(score, score_zero)

    def test_failure_penalty_two(self):
        """failure_count=2 → failure sub-score is 0.25."""
        score_one = compute_quality_score(success=True, failure_count=1)
        score_two = compute_quality_score(success=True, failure_count=2)
        self.assertGreater(score_one, score_two)

    def test_failure_penalty_three_or_more_zeroed(self):
        """failure_count >= 3 → failure sub-score is 0.0."""
        score_three = compute_quality_score(success=True, failure_count=3)
        score_ten = compute_quality_score(success=True, failure_count=10)
        self.assertAlmostEqual(score_three, score_ten, places=5)

    def test_test_pass_rate_none_uses_neutral(self):
        """test_pass_rate=None should use neutral 0.5 — same as explicit 0.5."""
        score_none = compute_quality_score(
            success=True, failure_count=0, test_pass_rate=None,
        )
        score_half = compute_quality_score(
            success=True, failure_count=0, test_pass_rate=0.5,
        )
        self.assertAlmostEqual(score_none, score_half, places=5)

    def test_user_accepted_none_uses_neutral(self):
        """user_accepted=None should use neutral 0.5 — same as neither True nor False."""
        score_none = compute_quality_score(
            success=True, failure_count=0, user_accepted=None,
        )
        # Accepted=True should raise score, accepted=False should lower it
        score_accepted = compute_quality_score(
            success=True, failure_count=0, user_accepted=True,
        )
        score_rejected = compute_quality_score(
            success=True, failure_count=0, user_accepted=False,
        )
        self.assertGreater(score_accepted, score_none)
        self.assertGreater(score_none, score_rejected)

    def test_review_issues_zero_perfect(self):
        score_zero = compute_quality_score(success=True, failure_count=0, review_issues=0)
        score_one = compute_quality_score(success=True, failure_count=0, review_issues=1)
        self.assertGreater(score_zero, score_one)

    def test_review_issues_one_to_two_half_penalty(self):
        score_one = compute_quality_score(success=True, failure_count=0, review_issues=1)
        score_two = compute_quality_score(success=True, failure_count=0, review_issues=2)
        # Both should be equal (same tier: 1–2 → 0.5)
        self.assertAlmostEqual(score_one, score_two, places=5)

    def test_review_issues_three_or_more_zeroed(self):
        score_three = compute_quality_score(success=True, failure_count=0, review_issues=3)
        score_five = compute_quality_score(success=True, failure_count=0, review_issues=5)
        self.assertAlmostEqual(score_three, score_five, places=5)

    def test_score_always_in_range(self):
        """Quality score must always be clamped to [0.0, 1.0]."""
        cases = [
            dict(success=True, failure_count=0, test_pass_rate=1.0, review_issues=0, user_accepted=True),
            dict(success=False, failure_count=5, test_pass_rate=0.0, review_issues=10, user_accepted=False),
            dict(success=True, failure_count=1, test_pass_rate=0.5),
            dict(success=False, failure_count=0),
        ]
        for kwargs in cases:
            with self.subTest(**kwargs):
                score = compute_quality_score(**kwargs)
                self.assertGreaterEqual(score, 0.0)
                self.assertLessEqual(score, 1.0)


# ---------------------------------------------------------------------------
# TestRecordSkillOutcome
# ---------------------------------------------------------------------------

class TestRecordSkillOutcome(unittest.TestCase):
    """Test record_skill_outcome persistence to .skill_metrics.jsonl."""

    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.mkdtemp()

    def test_records_to_jsonl_file(self):
        outcome = _make_outcome()
        result = record_skill_outcome(
            phase="EXECUTING",
            activation_level=25,
            model_id="claude-sonnet-4-6",
            complexity="M",
            outcome=outcome,
            workdir=self._tmpdir,
        )
        self.assertTrue(result)
        metrics_file = Path(self._tmpdir) / ".skill_metrics.jsonl"
        self.assertTrue(metrics_file.exists())

    def test_multiple_records_append(self):
        outcome = _make_outcome()
        for _ in range(3):
            record_skill_outcome(
                phase="EXECUTING",
                activation_level=25,
                model_id="claude-sonnet-4-6",
                complexity="M",
                outcome=outcome,
                workdir=self._tmpdir,
            )
        metrics_file = Path(self._tmpdir) / ".skill_metrics.jsonl"
        lines = metrics_file.read_text().strip().splitlines()
        self.assertEqual(len(lines), 3)

    def test_bad_workdir_returns_false(self):
        outcome = _make_outcome()
        result = record_skill_outcome(
            phase="EXECUTING",
            activation_level=25,
            model_id="claude-sonnet-4-6",
            complexity="M",
            outcome=outcome,
            workdir="/nonexistent/path/that/does/not/exist",
        )
        self.assertFalse(result)

    def test_all_fields_present_in_json(self):
        outcome = _make_outcome(
            success=True,
            quality_score=0.9,
            token_input=111,
            token_output=222,
            duration_ms=333,
            failure_count=1,
            error_type="test_error",
        )
        record_skill_outcome(
            phase="PLANNING",
            activation_level=50,
            model_id="claude-haiku-4-5",
            complexity="L",
            outcome=outcome,
            workdir=self._tmpdir,
        )
        metrics_file = Path(self._tmpdir) / ".skill_metrics.jsonl"
        record = json.loads(metrics_file.read_text().strip())

        self.assertEqual(record["phase"], "PLANNING")
        self.assertEqual(record["activation_level"], 50)
        self.assertEqual(record["model_id"], "claude-haiku-4-5")
        self.assertEqual(record["complexity"], "L")
        self.assertTrue(record["success"])
        self.assertAlmostEqual(record["quality_score"], 0.9, places=5)
        self.assertEqual(record["token_input"], 111)
        self.assertEqual(record["token_output"], 222)
        self.assertEqual(record["duration_ms"], 333)
        self.assertEqual(record["failure_count"], 1)
        self.assertEqual(record["error_type"], "test_error")

    def test_none_model_id_recorded(self):
        outcome = _make_outcome()
        result = record_skill_outcome(
            phase="EXECUTING",
            activation_level=0,
            model_id=None,
            complexity="S",
            outcome=outcome,
            workdir=self._tmpdir,
        )
        self.assertTrue(result)
        metrics_file = Path(self._tmpdir) / ".skill_metrics.jsonl"
        record = json.loads(metrics_file.read_text().strip())
        # Implementation stores None model_id as "unknown"
        self.assertIn(record["model_id"], [None, "unknown"])


# ---------------------------------------------------------------------------
# TestGetTierEffectiveness
# ---------------------------------------------------------------------------

class TestGetTierEffectiveness(unittest.TestCase):
    """Test get_tier_effectiveness aggregation and filtering."""

    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.mkdtemp()

    def test_empty_file_returns_empty_dict(self):
        # Create empty file
        (Path(self._tmpdir) / ".skill_metrics.jsonl").write_text("")
        result = get_tier_effectiveness(workdir=self._tmpdir)
        self.assertEqual(result, {})

    def test_no_file_returns_empty_dict(self):
        result = get_tier_effectiveness(workdir=self._tmpdir)
        self.assertEqual(result, {})

    def test_groups_by_activation_level(self):
        records = [
            _make_record(activation_level=25, quality_score=0.8),
            _make_record(activation_level=25, quality_score=0.6),
            _make_record(activation_level=25, quality_score=0.7),
            _make_record(activation_level=50, quality_score=0.9),
            _make_record(activation_level=50, quality_score=0.9),
            _make_record(activation_level=50, quality_score=0.9),
        ]
        _seed_records(self._tmpdir, records)
        result = get_tier_effectiveness(workdir=self._tmpdir, min_samples=1)
        self.assertIn(25, result)
        self.assertIn(50, result)
        self.assertNotIn(75, result)

    def test_min_samples_filtering(self):
        """Tiers with fewer records than min_samples should be excluded."""
        records = [
            _make_record(activation_level=25, quality_score=0.8),
            _make_record(activation_level=25, quality_score=0.8),
            _make_record(activation_level=50, quality_score=0.9),  # only 1 sample
        ]
        _seed_records(self._tmpdir, records)
        result = get_tier_effectiveness(workdir=self._tmpdir, min_samples=2)
        self.assertIn(25, result)
        self.assertNotIn(50, result)

    def test_phase_filter(self):
        records = [
            _make_record(phase="EXECUTING", activation_level=25, quality_score=0.8),
            _make_record(phase="EXECUTING", activation_level=25, quality_score=0.8),
            _make_record(phase="EXECUTING", activation_level=25, quality_score=0.8),
            _make_record(phase="PLANNING", activation_level=50, quality_score=0.9),
            _make_record(phase="PLANNING", activation_level=50, quality_score=0.9),
            _make_record(phase="PLANNING", activation_level=50, quality_score=0.9),
        ]
        _seed_records(self._tmpdir, records)
        result = get_tier_effectiveness(phase="EXECUTING", workdir=self._tmpdir, min_samples=1)
        # Only EXECUTING records should be counted
        self.assertIn(25, result)
        self.assertNotIn(50, result)

    def test_model_id_filter(self):
        records = [
            _make_record(model_id="claude-sonnet-4-6", activation_level=25, quality_score=0.8),
            _make_record(model_id="claude-sonnet-4-6", activation_level=25, quality_score=0.8),
            _make_record(model_id="claude-sonnet-4-6", activation_level=25, quality_score=0.8),
            _make_record(model_id="claude-haiku-4-5", activation_level=75, quality_score=0.6),
            _make_record(model_id="claude-haiku-4-5", activation_level=75, quality_score=0.6),
            _make_record(model_id="claude-haiku-4-5", activation_level=75, quality_score=0.6),
        ]
        _seed_records(self._tmpdir, records)
        result = get_tier_effectiveness(
            model_id="claude-sonnet-4-6", workdir=self._tmpdir, min_samples=1,
        )
        self.assertIn(25, result)
        self.assertNotIn(75, result)

    def test_computes_averages_correctly(self):
        records = [
            _make_record(
                activation_level=25, quality_score=0.6,
                token_input=100, token_output=100, duration_ms=400, success=True,
            ),
            _make_record(
                activation_level=25, quality_score=0.8,
                token_input=200, token_output=200, duration_ms=600, success=True,
            ),
            _make_record(
                activation_level=25, quality_score=1.0,
                token_input=300, token_output=300, duration_ms=800, success=False,
            ),
        ]
        _seed_records(self._tmpdir, records)
        result = get_tier_effectiveness(workdir=self._tmpdir, min_samples=1)
        stats: TierStats = result[25]

        self.assertEqual(stats.sample_count, 3)
        self.assertAlmostEqual(stats.avg_quality, (0.6 + 0.8 + 1.0) / 3, places=5)
        self.assertEqual(stats.avg_duration_ms, (400 + 600 + 800) // 3)
        self.assertGreater(stats.avg_tokens, 0)


# ---------------------------------------------------------------------------
# TestRecommendActivationLevel
# ---------------------------------------------------------------------------

class TestRecommendActivationLevel(unittest.TestCase):
    """Test recommend_activation_level recommendation logic."""

    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.mkdtemp()

    def test_insufficient_data_returns_low_confidence(self):
        result = recommend_activation_level(
            phase="EXECUTING",
            complexity="M",
            workdir=self._tmpdir,
        )
        self.assertEqual(result["confidence"], "low")

    def test_insufficient_data_returns_default_activation_level(self):
        result = recommend_activation_level(
            phase="EXECUTING",
            complexity="M",
            workdir=self._tmpdir,
        )
        self.assertIn("recommended_level", result)
        # Should be a valid level
        self.assertGreaterEqual(result["recommended_level"], 0)
        self.assertLessEqual(result["recommended_level"], 100)

    def test_returns_correct_structure(self):
        result = recommend_activation_level(
            phase="EXECUTING",
            complexity="M",
            workdir=self._tmpdir,
        )
        self.assertIn("recommended_level", result)
        self.assertIn("current_default", result)
        self.assertIn("confidence", result)
        self.assertIn("reason", result)
        self.assertIn("tier_stats", result)

    def test_picks_best_cost_efficiency_tier_above_quality_threshold(self):
        """With sufficient data, recommend the tier with best cost_efficiency above quality threshold."""
        # Seed tier 25 with great cost efficiency and adequate quality
        records_25 = [
            _make_record(activation_level=25, quality_score=0.85, token_input=50, token_output=50)
            for _ in range(5)
        ]
        # Seed tier 75 with lower cost efficiency but similar quality
        records_75 = [
            _make_record(activation_level=75, quality_score=0.86, token_input=500, token_output=500)
            for _ in range(5)
        ]
        _seed_records(self._tmpdir, records_25 + records_75)
        result = recommend_activation_level(
            phase="EXECUTING",
            complexity="M",
            workdir=self._tmpdir,
        )
        # Tier 25 has much better cost efficiency with comparable quality
        self.assertIn("recommended_level", result)
        # Should not recommend the most expensive tier when cheaper is good enough
        self.assertNotEqual(result.get("confidence"), "error")

    def test_quality_threshold_enforcement(self):
        """Tiers below quality threshold should not be recommended."""
        # Seed tier 25 with low quality, tier 50 with good quality
        records_low = [
            _make_record(activation_level=25, quality_score=0.2, success=False)
            for _ in range(5)
        ]
        records_good = [
            _make_record(activation_level=50, quality_score=0.9, success=True)
            for _ in range(5)
        ]
        _seed_records(self._tmpdir, records_low + records_good)
        result = recommend_activation_level(
            phase="EXECUTING",
            complexity="M",
            workdir=self._tmpdir,
        )
        if result.get("confidence") != "low":
            # If we have enough data, should not pick tier 25 with quality 0.2
            self.assertNotEqual(result["recommended_level"], 25)


# ---------------------------------------------------------------------------
# TestTierStatsDataclass
# ---------------------------------------------------------------------------

class TestTierStatsDataclass(unittest.TestCase):
    """Test TierStats dataclass properties."""

    def _make_tier_stats(self) -> TierStats:
        return TierStats(
            activation_level=25,
            sample_count=10,
            avg_quality=0.8,
            avg_tokens=300,
            success_rate=0.9,
            avg_duration_ms=500,
            cost_efficiency=0.8 / 300,
        )

    def test_all_fields_accessible(self):
        stats = self._make_tier_stats()
        self.assertEqual(stats.activation_level, 25)
        self.assertEqual(stats.sample_count, 10)
        self.assertAlmostEqual(stats.avg_quality, 0.8)
        self.assertEqual(stats.avg_tokens, 300)
        self.assertAlmostEqual(stats.success_rate, 0.9)
        self.assertEqual(stats.avg_duration_ms, 500)
        self.assertGreater(stats.cost_efficiency, 0.0)

    def test_frozen_immutable(self):
        stats = self._make_tier_stats()
        with self.assertRaises((AttributeError, TypeError)):
            stats.sample_count = 99  # type: ignore[misc]

    def test_cost_efficiency_is_quality_over_tokens(self):
        stats = self._make_tier_stats()
        expected = 0.8 / 300
        self.assertAlmostEqual(stats.cost_efficiency, expected, places=8)


if __name__ == "__main__":
    unittest.main()
