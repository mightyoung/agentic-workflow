"""Tests for model_profiles — LLM capability registry and skill tier routing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import model_profiles  # noqa: E402
from model_profiles import (  # noqa: E402
    ModelProfile,
    get_profile,
    list_models,
    register_model,
    resolve_activation_level,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_profile(
    *,
    family: str = "test",
    model_id: str = "test-model",
    capability_score: int = 80,
    default_tier: int = 25,
    fmt: str = "markdown",
    context_window: int = 128_000,
    cost_in: float = 1.0,
    cost_out: float = 5.0,
) -> ModelProfile:
    return ModelProfile(
        family=family,
        model_id=model_id,
        capability_score=capability_score,
        default_tier=default_tier,
        format=fmt,
        context_window=context_window,
        cost_per_1k_input=cost_in,
        cost_per_1k_output=cost_out,
    )


# ---------------------------------------------------------------------------
# TestGetProfile
# ---------------------------------------------------------------------------

class TestGetProfile(unittest.TestCase):
    """Test get_profile lookup logic."""

    def test_exact_match_sonnet(self):
        profile = get_profile("claude-sonnet-4-6")
        self.assertEqual(profile.model_id, "claude-sonnet-4-6")
        self.assertEqual(profile.family, "claude")
        self.assertEqual(profile.capability_score, 90)

    def test_exact_match_opus(self):
        profile = get_profile("claude-opus-4-6")
        self.assertEqual(profile.model_id, "claude-opus-4-6")
        self.assertEqual(profile.capability_score, 95)

    def test_alias_lookup_sonnet_dated(self):
        """Dated alias 'claude-sonnet-4-6-20250414' resolves to canonical sonnet profile."""
        profile = get_profile("claude-sonnet-4-6-20250414")
        self.assertEqual(profile.model_id, "claude-sonnet-4-6")
        self.assertEqual(profile.capability_score, 90)

    def test_alias_lookup_opus_dated(self):
        profile = get_profile("claude-opus-4-6-20250414")
        self.assertEqual(profile.model_id, "claude-opus-4-6")

    def test_prefix_match_returns_longer_key(self):
        """'claude-sonnet-4' is a prefix of 'claude-sonnet-4-6' and should match."""
        profile = get_profile("claude-sonnet-4")
        # Should return some claude-sonnet profile, not the fallback
        self.assertEqual(profile.family, "claude")
        self.assertIn("sonnet", profile.model_id)

    def test_unknown_model_returns_fallback(self):
        profile = get_profile("totally-unknown-model-xyz-9999")
        self.assertEqual(profile.model_id, "unknown")
        self.assertEqual(profile.family, "unknown")

    def test_none_returns_fallback(self):
        with patch.dict("os.environ", {}, clear=True):
            # Remove AGENTIC_WORKFLOW_MODEL if set
            import os
            os.environ.pop("AGENTIC_WORKFLOW_MODEL", None)
            profile = get_profile(None)
        self.assertEqual(profile.model_id, "unknown")

    def test_empty_string_returns_fallback(self):
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("AGENTIC_WORKFLOW_MODEL", None)
            profile = get_profile("")
        self.assertEqual(profile.model_id, "unknown")

    def test_env_var_fallback_used_when_no_explicit_id(self):
        """When model_id is None, AGENTIC_WORKFLOW_MODEL env var is used."""
        with patch.dict("os.environ", {"AGENTIC_WORKFLOW_MODEL": "claude-haiku-4-5"}):
            profile = get_profile(None)
        self.assertEqual(profile.model_id, "claude-haiku-4-5")

    def test_env_var_overridden_by_explicit_id(self):
        """An explicit model_id takes precedence over env var."""
        with patch.dict("os.environ", {"AGENTIC_WORKFLOW_MODEL": "claude-haiku-4-5"}):
            profile = get_profile("claude-opus-4-6")
        self.assertEqual(profile.model_id, "claude-opus-4-6")


# ---------------------------------------------------------------------------
# TestResolveActivationLevel
# ---------------------------------------------------------------------------

class TestResolveActivationLevel(unittest.TestCase):
    """Test resolve_activation_level formula."""

    def setUp(self):
        self._strong = _make_profile(capability_score=90, default_tier=25)
        self._weak = _make_profile(capability_score=60, default_tier=75)
        self._mid = _make_profile(capability_score=80, default_tier=50)

    # --- Default tier from model profile ---

    def test_default_tier_is_base_for_m_complexity(self):
        level = resolve_activation_level("EXECUTING", "M", self._strong)
        # base=25, complexity=0, phase=0, failures=0 → 25
        self.assertEqual(level, 25)

    def test_default_tier_weak_model(self):
        level = resolve_activation_level("EXECUTING", "M", self._weak)
        # base=75, complexity=0, phase=0, failures=0 → 75
        self.assertEqual(level, 75)

    # --- Complexity boost ---

    def test_xs_complexity_reduces_level(self):
        level = resolve_activation_level("EXECUTING", "XS", self._strong)
        # base=25, complexity=-25 → 0
        self.assertEqual(level, 0)

    def test_l_complexity_increases_level(self):
        level = resolve_activation_level("EXECUTING", "L", self._strong)
        # base=25, complexity=+25 → 50
        self.assertEqual(level, 50)

    def test_xl_complexity_same_as_l(self):
        level_l = resolve_activation_level("EXECUTING", "L", self._mid)
        level_xl = resolve_activation_level("EXECUTING", "XL", self._mid)
        self.assertEqual(level_l, level_xl)

    def test_s_and_m_complexity_no_boost(self):
        level_s = resolve_activation_level("EXECUTING", "S", self._strong)
        level_m = resolve_activation_level("EXECUTING", "M", self._strong)
        self.assertEqual(level_s, level_m)

    # --- Phase adjustment ---

    def test_thinking_phase_strong_model_gets_minus_25(self):
        level = resolve_activation_level("THINKING", "M", self._strong)
        # base=25, complexity=0, phase=-25 (strong model) → 0
        self.assertEqual(level, 0)

    def test_thinking_phase_weak_model_no_adjustment(self):
        level = resolve_activation_level("THINKING", "M", self._weak)
        # base=75, complexity=0, phase=0 (weak model, cap_score < 85) → 75
        self.assertEqual(level, 75)

    def test_research_phase_strong_model_gets_minus_25(self):
        level = resolve_activation_level("RESEARCH", "M", self._strong)
        self.assertEqual(level, 0)

    def test_planning_phase_strong_model_gets_minus_25(self):
        level = resolve_activation_level("PLANNING", "M", self._strong)
        self.assertEqual(level, 0)

    def test_executing_phase_no_phase_adjustment(self):
        level = resolve_activation_level("EXECUTING", "M", self._strong)
        # base=25, no adjustments → 25
        self.assertEqual(level, 25)

    def test_debugging_phase_no_phase_adjustment(self):
        level = resolve_activation_level("DEBUGGING", "M", self._strong)
        self.assertEqual(level, 25)

    # --- Failure escalation ---

    def test_one_failure_adds_25(self):
        level = resolve_activation_level("EXECUTING", "M", self._strong, failure_count=1)
        # base=25 + 25 = 50
        self.assertEqual(level, 50)

    def test_two_failures_adds_50(self):
        level = resolve_activation_level("EXECUTING", "M", self._strong, failure_count=2)
        # base=25 + 50 = 75
        self.assertEqual(level, 75)

    def test_three_failures_capped_at_75(self):
        level = resolve_activation_level("EXECUTING", "M", self._strong, failure_count=3)
        # base=25 + 75 = 100
        self.assertEqual(level, 100)

    def test_many_failures_failure_boost_capped_at_75(self):
        level_3 = resolve_activation_level("EXECUTING", "M", self._strong, failure_count=3)
        level_10 = resolve_activation_level("EXECUTING", "M", self._strong, failure_count=10)
        # Failure boost is capped at 75, so both should be the same
        self.assertEqual(level_3, level_10)

    # --- Combined effects ---

    def test_combined_xl_plus_two_failures(self):
        level = resolve_activation_level("EXECUTING", "XL", self._strong, failure_count=2)
        # base=25, complexity=+25, phase=0, failure=+50 → 100
        self.assertEqual(level, 100)

    def test_combined_thinking_xs_strong(self):
        level = resolve_activation_level("THINKING", "XS", self._strong)
        # base=25, complexity=-25, phase=-25 → -25 → clamped to 0
        self.assertEqual(level, 0)

    # --- Clamping ---

    def test_clamped_to_zero(self):
        very_capable = _make_profile(capability_score=95, default_tier=0)
        level = resolve_activation_level("THINKING", "XS", very_capable)
        # base=0, complexity=-25, phase=-25 → -50 → clamped 0
        self.assertEqual(level, 0)

    def test_clamped_to_100(self):
        very_weak = _make_profile(capability_score=50, default_tier=100)
        level = resolve_activation_level("EXECUTING", "XL", very_weak, failure_count=3)
        # Would exceed 100: clamped to 100
        self.assertEqual(level, 100)

    # --- None / empty phase and complexity ---

    def test_none_profile_uses_fallback(self):
        level = resolve_activation_level("EXECUTING", "M", None)
        fallback_tier = model_profiles._FALLBACK.default_tier
        self.assertEqual(level, fallback_tier)

    def test_empty_phase_treated_as_unknown(self):
        level = resolve_activation_level("", "M", self._strong)
        # No phase adjustment for unknown phase
        self.assertEqual(level, self._strong.default_tier)

    def test_none_phase_treated_as_empty(self):
        level = resolve_activation_level(None, "M", self._strong)
        self.assertEqual(level, self._strong.default_tier)

    def test_empty_complexity_no_boost(self):
        level_empty = resolve_activation_level("EXECUTING", "", self._strong)
        level_m = resolve_activation_level("EXECUTING", "M", self._strong)
        self.assertEqual(level_empty, level_m)

    def test_none_complexity_no_boost(self):
        level = resolve_activation_level("EXECUTING", None, self._strong)
        self.assertEqual(level, self._strong.default_tier)


# ---------------------------------------------------------------------------
# TestListModels
# ---------------------------------------------------------------------------

class TestListModels(unittest.TestCase):
    """Test list_models filtering and deduplication."""

    def test_returns_all_models_without_filter(self):
        models = list_models()
        self.assertGreater(len(models), 0)
        families = {m.family for m in models}
        # Registry contains claude, openai, google, local families
        self.assertIn("claude", families)
        self.assertIn("openai", families)

    def test_family_filter_returns_only_claude(self):
        models = list_models(family="claude")
        self.assertTrue(all(m.family == "claude" for m in models))
        self.assertGreater(len(models), 0)

    def test_family_filter_returns_only_local(self):
        models = list_models(family="local")
        self.assertTrue(all(m.family == "local" for m in models))

    def test_no_duplicates_from_aliases(self):
        """Aliases share model_id with canonical entries; list_models should deduplicate."""
        models = list_models()
        model_ids = [m.model_id for m in models]
        self.assertEqual(len(model_ids), len(set(model_ids)),
                         "list_models returned duplicate model_id entries")

    def test_unknown_family_returns_empty(self):
        models = list_models(family="nonexistent_family")
        self.assertEqual(models, [])

    def test_results_sorted_by_capability_score_desc(self):
        models = list_models()
        scores = [m.capability_score for m in models]
        self.assertEqual(scores, sorted(scores, reverse=True))


# ---------------------------------------------------------------------------
# TestRegisterModel
# ---------------------------------------------------------------------------

class TestRegisterModel(unittest.TestCase):
    """Test register_model for runtime additions and overrides."""

    def tearDown(self):
        # Clean up any test entries added to the global registry
        model_profiles._REGISTRY.pop("test-register-new", None)
        model_profiles._REGISTRY.pop("test-register-override", None)

    def test_new_model_registered_and_retrievable(self):
        new_profile = _make_profile(
            family="test",
            model_id="test-register-new",
            capability_score=55,
            default_tier=60,
        )
        register_model("test-register-new", new_profile)
        retrieved = get_profile("test-register-new")
        self.assertEqual(retrieved.model_id, "test-register-new")
        self.assertEqual(retrieved.capability_score, 55)
        self.assertEqual(retrieved.family, "test")

    def test_override_existing_model(self):
        original = get_profile("claude-haiku-4-5")
        overriding = _make_profile(
            family="claude",
            model_id="claude-haiku-4-5",
            capability_score=99,
            default_tier=0,
        )
        register_model("test-register-override", overriding)
        retrieved = get_profile("test-register-override")
        self.assertEqual(retrieved.capability_score, 99)
        # Original haiku entry is unchanged
        self.assertEqual(get_profile("claude-haiku-4-5").capability_score,
                         original.capability_score)


# ---------------------------------------------------------------------------
# TestIntegration
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):
    """Integration tests combining get_profile and resolve_activation_level."""

    def test_get_profile_then_resolve_sonnet_executing_m(self):
        profile = get_profile("claude-sonnet-4-6")
        level = resolve_activation_level("EXECUTING", "M", profile)
        # sonnet: default_tier=25, complexity=0, phase=0 → 25
        self.assertEqual(level, 25)

    def test_get_profile_then_resolve_haiku_executing_l(self):
        profile = get_profile("claude-haiku-4-5")
        level = resolve_activation_level("EXECUTING", "L", profile)
        # haiku: default_tier=50, complexity=+25, phase=0 → 75
        self.assertEqual(level, 75)

    def test_get_profile_then_resolve_opus_thinking_m(self):
        profile = get_profile("claude-opus-4-6")
        level = resolve_activation_level("THINKING", "M", profile)
        # opus: default_tier=0, complexity=0, phase=-25 (cap=95>=85) → -25 → clamped 0
        self.assertEqual(level, 0)

    def test_build_skill_context_integration(self):
        """When runtime_profile is importable, verify it accepts model profile."""
        try:
            import runtime_profile  # noqa: F401
        except ImportError:
            self.skipTest("runtime_profile not importable in this environment")

        profile = get_profile("claude-sonnet-4-6")
        level = resolve_activation_level("EXECUTING", "M", profile)
        # Should be able to call build_skill_context with the resolved level
        result = runtime_profile.build_skill_context("EXECUTING", "M", activation_level=level)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        prompt, tokens = result
        self.assertIsInstance(prompt, str)
        self.assertIsInstance(tokens, int)

    def test_fallback_profile_produces_valid_activation_level(self):
        """Unknown model should return a usable profile and valid activation level."""
        profile = get_profile("unknown-model-xyz")
        self.assertEqual(profile.family, "unknown")
        level = resolve_activation_level("EXECUTING", "M", profile)
        self.assertGreaterEqual(level, 0)
        self.assertLessEqual(level, 100)


if __name__ == "__main__":
    unittest.main()
