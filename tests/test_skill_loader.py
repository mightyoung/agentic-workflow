#!/usr/bin/env python3
"""
Tests for skill_loader module.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT / "scripts"))

from skill_loader import SkillLoader, load_skill  # noqa: E402


class TestSkillLoader(unittest.TestCase):
    """Tests for SkillLoader class."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.skills_dir = Path(self.temp_dir) / "skills"
        self.skills_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_all_skills_empty(self):
        """Test loading skills from empty directory."""
        loader = SkillLoader(str(self.skills_dir))
        skills = loader.load_all_skills()
        self.assertEqual(skills, {})

    def test_load_skill_nonexistent(self):
        """Test loading non-existent skill returns None."""
        loader = SkillLoader(str(self.skills_dir))
        skill = loader.load_skill("nonexistent")
        self.assertIsNone(skill)

    def test_parse_frontmatter_valid(self):
        """Test _parse_frontmatter with valid YAML frontmatter."""
        loader = SkillLoader(str(self.skills_dir))
        frontmatter = """---
name: test-skill
version: 1.0.0
status: implemented
description: A test skill
tags: [test, phase]
---"""
        metadata = loader._parse_frontmatter(frontmatter)
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata.name, "test-skill")
        self.assertEqual(metadata.version, "1.0.0")
        self.assertEqual(metadata.status, "implemented")
        self.assertEqual(metadata.description, "A test skill")
        self.assertEqual(metadata.tags, ["test", "phase"])

    def test_parse_frontmatter_empty_name(self):
        """Test _parse_frontmatter returns None when name is empty."""
        loader = SkillLoader(str(self.skills_dir))
        frontmatter = """---
version: 1.0.0
---"""
        metadata = loader._parse_frontmatter(frontmatter)
        self.assertIsNone(metadata)

    def test_extract_sections(self):
        """Test _extract_sections parses markdown correctly."""
        loader = SkillLoader(str(self.skills_dir))
        markdown = """# Header 1

Content 1

## Section A

Content A

## Section B

Content B"""
        sections = loader._extract_sections(markdown)
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections["Section A"], "Content A")
        self.assertEqual(sections["Section B"], "Content B")

    def test_extract_sections_empty(self):
        """Test _extract_sections with no sections."""
        loader = SkillLoader(str(self.skills_dir))
        markdown = "No sections here"
        sections = loader._extract_sections(markdown)
        self.assertEqual(sections, {})


class TestModuleLevelFunctions(unittest.TestCase):
    """Tests for module-level functions."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.skills_dir = Path(self.temp_dir) / "skills"
        self.skills_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_skill_returns_none(self):
        """Test load_skill returns None for non-existent skill."""
        result = load_skill("nonexistent", str(self.skills_dir))
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
