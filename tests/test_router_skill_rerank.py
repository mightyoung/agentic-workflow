#!/usr/bin/env python3
"""
Tests for SkillRouter-style reranking in router.py.
"""

import tempfile
import unittest
from pathlib import Path
import sys

from router_helpers import load_router_module


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

ROUTER = load_router_module()


def _write_skill(root: Path, name: str, body: str) -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "skill.md").write_text(body, encoding="utf-8")


class TestRouterSkillRerank(unittest.TestCase):
    def test_rerank_prefers_full_skill_body_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)
            _write_skill(
                skills_dir,
                "planning",
                """---
name: planning
version: 1.0.0
status: implemented
description: Planning skill
tags: [phase]
---

# PLANNING

## Overview
请查一下这个计划，先拆解步骤并定义验收标准。

## Core Process
- 请查一下这个计划
- 拆解步骤
- 定义验收标准
""",
            )
            _write_skill(
                skills_dir,
                "research",
                """---
name: research
version: 1.0.0
status: implemented
description: Research skill
tags: [phase]
---

# RESEARCH

## Overview
Research skill focuses on evidence gathering and comparison.

## Core Process
- Gather evidence
- 收集证据
- 形成建议
""",
            )

            prompt = "请查一下这个计划"
            without_rerank = ROUTER.route(prompt, use_skill_rerank=False, skills_dir=str(skills_dir))
            with_rerank = ROUTER.route(prompt, use_skill_rerank=True, skills_dir=str(skills_dir))

            self.assertEqual(without_rerank[0], "STAGE")
            self.assertEqual(without_rerank[1], "RESEARCH")
            self.assertEqual(with_rerank[0], "STAGE")
            self.assertEqual(with_rerank[1], "PLANNING")
            self.assertGreaterEqual(with_rerank[2], without_rerank[2])


if __name__ == "__main__":
    unittest.main()
