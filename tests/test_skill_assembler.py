"""Tests for skill_assembler — tiered skill prompt assembly."""

from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import skill_assembler  # noqa: E402


class TestLoadTiers(unittest.TestCase):
    """Test tier loading from file system."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.skills_dir = Path(self.tmpdir) / "skills"
        # Create a test phase directory with tier files
        phase_dir = self.skills_dir / "executing"
        phase_dir.mkdir(parents=True)
        (phase_dir / "tier_core.md").write_text("<!-- tier:25% -->\nIron Law: test first")
        (phase_dir / "tier_process.md").write_text("<!-- tier:50% -->\n1. Read plan\n2. Write test")
        (phase_dir / "tier_full.md").write_text("<!-- tier:75% -->\n## Full methodology\nTDD cycle")
        (phase_dir / "tier_reference.md").write_text("<!-- tier:100% -->\n## Examples\nSample code")

    def _patch_skills_dir(self):
        return patch.object(skill_assembler, "_skills_dir", return_value=self.skills_dir)

    def test_level_0_returns_empty(self):
        with self._patch_skills_dir():
            result = skill_assembler.load_tiers("EXECUTING", 0)
        self.assertEqual(result, [])

    def test_level_25_loads_core_only(self):
        with self._patch_skills_dir():
            result = skill_assembler.load_tiers("EXECUTING", 25)
        self.assertEqual(len(result), 1)
        self.assertIn("Iron Law", result[0])

    def test_level_50_loads_core_and_process(self):
        with self._patch_skills_dir():
            result = skill_assembler.load_tiers("EXECUTING", 50)
        self.assertEqual(len(result), 2)
        self.assertIn("Iron Law", result[0])
        self.assertIn("Read plan", result[1])

    def test_level_75_loads_three_tiers(self):
        with self._patch_skills_dir():
            result = skill_assembler.load_tiers("EXECUTING", 75)
        self.assertEqual(len(result), 3)

    def test_level_100_loads_all_four_tiers(self):
        with self._patch_skills_dir():
            result = skill_assembler.load_tiers("EXECUTING", 100)
        self.assertEqual(len(result), 4)
        self.assertIn("Examples", result[3])

    def test_level_30_loads_only_core(self):
        """Levels between thresholds load only the lower tier."""
        with self._patch_skills_dir():
            result = skill_assembler.load_tiers("EXECUTING", 30)
        self.assertEqual(len(result), 1)

    def test_unknown_phase_returns_empty(self):
        with self._patch_skills_dir():
            result = skill_assembler.load_tiers("NONEXISTENT", 100)
        self.assertEqual(result, [])

    def test_missing_tier_file_skipped_gracefully(self):
        """If tier_process.md is missing, level 50 still loads tier_core."""
        phase_dir = self.skills_dir / "executing"
        (phase_dir / "tier_process.md").unlink()
        with self._patch_skills_dir():
            result = skill_assembler.load_tiers("EXECUTING", 50)
        # Should have core only (process file is missing)
        self.assertEqual(len(result), 1)
        self.assertIn("Iron Law", result[0])


class TestMergeTiers(unittest.TestCase):
    """Test tier merging."""

    def test_merge_empty(self):
        self.assertEqual(skill_assembler.merge_tiers([]), "")

    def test_merge_single(self):
        self.assertEqual(skill_assembler.merge_tiers(["hello"]), "hello")

    def test_merge_multiple_uses_double_newline(self):
        result = skill_assembler.merge_tiers(["a", "b", "c"])
        self.assertEqual(result, "a\n\nb\n\nc")


class TestEstimateTokens(unittest.TestCase):
    """Test token estimation."""

    def test_empty_string_returns_zero(self):
        self.assertEqual(skill_assembler.estimate_tokens(""), 0)

    def test_short_string(self):
        tokens = skill_assembler.estimate_tokens("hello world")
        self.assertGreater(tokens, 0)
        self.assertLess(tokens, 10)

    def test_proportional_to_length(self):
        short = skill_assembler.estimate_tokens("a" * 100)
        long = skill_assembler.estimate_tokens("a" * 1000)
        self.assertGreater(long, short)


class TestFormatAdapters(unittest.TestCase):
    """Test format adapters."""

    def test_markdown_passthrough(self):
        adapter = skill_assembler.MarkdownAdapter()
        result = adapter.format("## Hello", "EXECUTING")
        self.assertEqual(result, "## Hello")

    def test_xml_wraps_in_tags(self):
        adapter = skill_assembler.XMLAdapter()
        result = adapter.format("content", "EXECUTING")
        self.assertIn("<skill-context", result)
        self.assertIn('phase="EXECUTING"', result)
        self.assertIn("content", result)
        self.assertIn("</skill-context>", result)

    def test_plain_strips_markdown(self):
        adapter = skill_assembler.PlainAdapter()
        result = adapter.format("## Header\n**bold** text\n```python\ncode\n```", "TEST")
        self.assertNotIn("##", result)
        self.assertNotIn("**", result)
        self.assertNotIn("```", result)
        self.assertIn("bold", result)
        self.assertIn("text", result)

    def test_get_adapter_default(self):
        adapter = skill_assembler.get_adapter()
        self.assertIsInstance(adapter, skill_assembler.MarkdownAdapter)

    def test_get_adapter_unknown_falls_back(self):
        adapter = skill_assembler.get_adapter("unknown_format")
        self.assertIsInstance(adapter, skill_assembler.MarkdownAdapter)


class TestAssembleSkillPrompt(unittest.TestCase):
    """Test the main assembly function."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.skills_dir = Path(self.tmpdir) / "skills"
        phase_dir = self.skills_dir / "executing"
        phase_dir.mkdir(parents=True)
        (phase_dir / "tier_core.md").write_text("Core: test first")
        (phase_dir / "tier_process.md").write_text("Process: 1. plan 2. test 3. code")
        (phase_dir / "tier_full.md").write_text("Full: complete TDD methodology")

    def _patch_skills_dir(self):
        return patch.object(skill_assembler, "_skills_dir", return_value=self.skills_dir)

    def test_level_0_returns_empty(self):
        with self._patch_skills_dir():
            prompt, tokens = skill_assembler.assemble_skill_prompt("EXECUTING", 0)
        self.assertEqual(prompt, "")
        self.assertEqual(tokens, 0)

    def test_level_50_returns_core_and_process(self):
        with self._patch_skills_dir():
            prompt, tokens = skill_assembler.assemble_skill_prompt("EXECUTING", 50)
        self.assertIn("Core: test first", prompt)
        self.assertIn("Process:", prompt)
        self.assertGreater(tokens, 0)

    def test_xml_format(self):
        with self._patch_skills_dir():
            prompt, tokens = skill_assembler.assemble_skill_prompt("EXECUTING", 25, "xml")
        self.assertIn("<skill-context", prompt)
        self.assertIn("Core: test first", prompt)

    def test_nonexistent_phase_returns_empty(self):
        with self._patch_skills_dir():
            prompt, tokens = skill_assembler.assemble_skill_prompt("NONEXISTENT", 50)
        self.assertEqual(prompt, "")
        self.assertEqual(tokens, 0)


class TestTierSummary(unittest.TestCase):
    """Test tier_summary inspection."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.skills_dir = Path(self.tmpdir) / "skills"
        phase_dir = self.skills_dir / "executing"
        phase_dir.mkdir(parents=True)
        (phase_dir / "tier_core.md").write_text("x" * 350)  # ~100 tokens
        (phase_dir / "tier_process.md").write_text("y" * 1400)  # ~400 tokens

    def _patch_skills_dir(self):
        return patch.object(skill_assembler, "_skills_dir", return_value=self.skills_dir)

    def test_summary_shows_cumulative_tokens(self):
        with self._patch_skills_dir():
            summary = skill_assembler.tier_summary("EXECUTING")
        self.assertIn("25%", summary)
        self.assertIn("50%", summary)
        # 50% should be larger than 25% (cumulative)
        self.assertGreater(summary["50%"], summary["25%"])

    def test_unknown_phase_returns_empty(self):
        with self._patch_skills_dir():
            summary = skill_assembler.tier_summary("NONEXISTENT")
        self.assertEqual(summary, {})


class TestBuildSkillContextIntegration(unittest.TestCase):
    """Test that runtime_profile.build_skill_context delegates to assembler."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.skills_dir = Path(self.tmpdir) / "skills"
        phase_dir = self.skills_dir / "executing"
        phase_dir.mkdir(parents=True)
        (phase_dir / "tier_core.md").write_text("TIER_CORE_CONTENT")
        (phase_dir / "tier_process.md").write_text("TIER_PROCESS_CONTENT")

    def _patch_skills_dir(self):
        return patch.object(skill_assembler, "_skills_dir", return_value=self.skills_dir)

    def test_with_tier_files_uses_assembler(self):
        """When tier files exist, build_skill_context should use them."""
        import runtime_profile
        with self._patch_skills_dir():
            prompt, tokens = runtime_profile.build_skill_context("EXECUTING", "M", activation_level=50)
        self.assertIn("TIER_CORE_CONTENT", prompt)
        self.assertIn("TIER_PROCESS_CONTENT", prompt)

    def test_without_tier_files_falls_back(self):
        """When tier files don't exist, should fall back to PHASE_PROMPTS."""
        import runtime_profile
        empty_dir = Path(self.tmpdir) / "empty_skills"
        empty_dir.mkdir(parents=True)
        with patch.object(skill_assembler, "_skills_dir", return_value=empty_dir):
            prompt, tokens = runtime_profile.build_skill_context("EXECUTING", "M", activation_level=50)
        # Should contain legacy PHASE_PROMPTS content
        self.assertIn("原则", prompt)

    def test_activation_level_none_infers_from_complexity(self):
        """When activation_level is None, should infer from complexity."""
        import runtime_profile
        with self._patch_skills_dir():
            prompt_xs, _ = runtime_profile.build_skill_context("EXECUTING", "XS")
            prompt_l, _ = runtime_profile.build_skill_context("EXECUTING", "L")
        # XS should get 25% (core only), L should get 75% (core+process+full)
        # Both should at least have core content
        self.assertIn("TIER_CORE_CONTENT", prompt_xs)
        self.assertIn("TIER_CORE_CONTENT", prompt_l)


if __name__ == "__main__":
    unittest.main()
