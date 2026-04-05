#!/usr/bin/env python3
"""
Long-term Memory Operations 测试 - 测试 memory_longterm.py 的功能

覆盖:
- read_task_history - 读取任务历史
- generate_weekly_report - 生成周报
- _effective_confidence - 时间衰减置信度 (Sprint 1)
- add_to_index / search_index - 结构化索引读写 (Sprint 1)
- search_memory with intent - 意图感知检索 (Sprint 1+2)
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# 添加项目路径
_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts')
sys.path.insert(0, _SCRIPTS)

from memory_longterm import (
    _effective_confidence,
    add_experience,
    add_to_index,
    generate_weekly_report,
    read_task_history,
    search_index,
    search_memory,
)


# ── Sprint 1: _effective_confidence ──────────────────────────────────────────

class TestEffectiveConfidence:
    """MAGMA Temporal decay: effective = base × λ^days_old"""

    def test_zero_days_no_decay(self):
        today = datetime.now().strftime("%Y-%m-%d")
        eff = _effective_confidence(0.8, today)
        assert abs(eff - 0.8) < 0.01

    def test_seven_days_partial_decay(self):
        seven_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        eff = _effective_confidence(0.8, seven_ago)
        # λ=0.95^7 ≈ 0.698 → 0.8 × 0.698 ≈ 0.559
        assert 0.50 < eff < 0.62

    def test_thirty_days_heavy_decay(self):
        thirty_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        eff = _effective_confidence(0.8, thirty_ago)
        # λ=0.95^30 ≈ 0.215 → 0.8 × 0.215 ≈ 0.172
        assert eff < 0.25

    def test_confidence_never_negative(self):
        old = "2020-01-01"
        eff = _effective_confidence(0.9, old)
        assert eff >= 0

    def test_invalid_timestamp_returns_base(self):
        eff = _effective_confidence(0.7, "not-a-date")
        assert abs(eff - 0.7) < 0.001

    def test_empty_timestamp_returns_base(self):
        eff = _effective_confidence(0.6, "")
        assert abs(eff - 0.6) < 0.001

    def test_custom_decay_lambda(self):
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        fast = _effective_confidence(1.0, yesterday, decay=0.5)
        slow = _effective_confidence(1.0, yesterday, decay=0.99)
        assert fast < slow


# ── Sprint 1: add_to_index / search_index ─────────────────────────────────────

@pytest.fixture(autouse=True)
def tmp_workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield tmp_path


class TestAddToIndex:
    def test_creates_jsonl_file(self, tmp_path):
        add_to_index("experience", "test entry", confidence=0.7, scope="project")
        assert os.path.exists(".memory_index.jsonl")

    def test_entry_fields(self, tmp_path):
        add_to_index("pattern", "best practice note", confidence=0.8, scope="global")
        with open(".memory_index.jsonl") as f:
            entry = json.loads(f.read().strip())
        assert entry["type"] == "pattern"
        assert entry["text"] == "best practice note"
        assert entry["confidence"] == 0.8
        assert entry["scope"] == "global"
        assert "id" in entry
        assert "timestamp" in entry

    def test_confidence_clamped(self, tmp_path):
        add_to_index("experience", "test", confidence=1.5)  # > 0.9
        with open(".memory_index.jsonl") as f:
            entry = json.loads(f.read().strip())
        assert entry["confidence"] <= 0.9

        os.remove(".memory_index.jsonl")
        add_to_index("experience", "test", confidence=0.1)  # < 0.3
        with open(".memory_index.jsonl") as f:
            entry = json.loads(f.read().strip())
        assert entry["confidence"] >= 0.3

    def test_appends_multiple_entries(self, tmp_path):
        add_to_index("experience", "entry A", confidence=0.7)
        add_to_index("experience", "entry B", confidence=0.6)
        with open(".memory_index.jsonl") as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) == 2

    def test_returns_entry_id(self, tmp_path):
        eid = add_to_index("experience", "test", confidence=0.5)
        assert isinstance(eid, str)
        assert len(eid) > 0


class TestSearchIndex:
    def _add(self, text: str, confidence: float = 0.7, scope: str = "project",
             entry_type: str = "experience") -> None:
        add_to_index(entry_type, text, confidence=confidence, scope=scope)

    def test_finds_matching_entry(self, tmp_path):
        self._add("Python import error fix needed")
        results = search_index("import error")
        assert len(results) == 1

    def test_no_match_returns_empty(self, tmp_path):
        self._add("something unrelated")
        results = search_index("xyz123nonexistent")
        assert results == []

    def test_missing_index_returns_empty(self):
        results = search_index("anything")
        assert results == []

    def test_sorted_by_effective_confidence(self, tmp_path):
        # High confidence today vs low confidence today
        self._add("common keyword high", confidence=0.9)
        self._add("common keyword low", confidence=0.3)
        results = search_index("common keyword")
        assert len(results) == 2
        # Higher confidence should come first
        assert results[0]["confidence"] >= results[1]["confidence"]

    def test_scope_project_filter(self, tmp_path):
        # scope="project" in search_index filters by project_id (same repo),
        # NOT by the scope field value — both entries from this repo pass.
        self._add("shared note project scope", scope="project")
        self._add("shared note global scope", scope="global")
        results = search_index("shared note", scope="project")
        # Both entries live in same repo → both visible in project scope
        assert len(results) >= 1

    def test_scope_global_filter(self, tmp_path):
        self._add("global entry", scope="global")
        self._add("project entry", scope="project")
        results = search_index("entry", scope="global")
        assert all(r.get("scope") == "global" for r in results)

    def test_limit_respected(self, tmp_path):
        for i in range(10):
            self._add(f"target entry {i}", confidence=0.7)
        results = search_index("target entry", limit=3)
        assert len(results) <= 3

    def test_intent_debug_boost(self, tmp_path):
        """Entries with Trigger: and Signal: fields get boosted for debug intent."""
        self._add("Task:x Trigger:ImportError Mistake:y Fix:z Signal:ModuleNotFoundError",
                  confidence=0.5)
        self._add("unrelated entry with same keyword ImportError", confidence=0.7)
        results = search_index("ImportError", intent="debug")
        # The reflexion entry should score higher despite lower base confidence
        assert len(results) == 2
        reflexion_result = next(
            (r for r in results if "Trigger:" in r.get("text", "")), None
        )
        assert reflexion_result is not None

    def test_intent_plan_boost(self, tmp_path):
        """type=pattern entries get ×1.3 boost for plan intent.
        Pattern (conf=0.7 × 1.3 = 0.91) should outscore experience (conf=0.6 × 1.0 = 0.60).
        """
        self._add("best practice note", entry_type="pattern", confidence=0.7)
        self._add("best practice experience", entry_type="experience", confidence=0.6)
        results = search_index("best practice", intent="plan")
        assert len(results) == 2
        # Pattern entry should come first due to boost
        assert results[0]["type"] == "pattern"

    def test_result_contains_score(self, tmp_path):
        self._add("test entry for scoring")
        results = search_index("test entry")
        assert "_score" in results[0]
        assert results[0]["_score"] > 0


# ── Sprint 1+2: search_memory intent routing ─────────────────────────────────

class TestSearchMemoryIntent:
    def test_intent_debug_returns_results(self, tmp_path):
        add_to_index("experience",
                     "Task:debug Trigger:import error Fix:add import Signal:ModuleNotFoundError",
                     confidence=0.7)
        results = search_memory("import error", intent="debug")
        assert len(results) >= 1

    def test_intent_plan_prioritizes_patterns(self, tmp_path):
        add_to_index("pattern", "always use dependency injection", confidence=0.6)
        add_to_index("experience", "fixed bug with dependency injection", confidence=0.8)
        results = search_memory("dependency injection", intent="plan")
        assert len(results) >= 1
        # Pattern entry should appear (maybe first due to boost)
        texts = " ".join(results)
        assert "dependency injection" in texts.lower()

    def test_intent_auto_detects_debug(self, tmp_path):
        add_to_index("experience",
                     "Task:x Trigger:bug in auth Fix:fix null check Signal:NullPointerError",
                     confidence=0.7)
        # "error" in query → auto-detect as debug
        results = search_memory("NullPointerError", intent="auto")
        assert len(results) >= 1

    def test_limit_respected(self, tmp_path):
        for i in range(10):
            add_to_index("experience", f"test entry {i}", confidence=0.6)
        results = search_memory("test entry", limit=3)
        assert len(results) <= 3

    def test_fallback_to_memory_md(self, tmp_path):
        """When index is empty, falls back to MEMORY.md full-text search."""
        memory_md = tmp_path / "MEMORY.md"
        memory_md.write_text("## 核心经验\n- keyword fallback test entry\n")
        results = search_memory("fallback test", filepath=str(memory_md))
        assert any("fallback" in r.lower() for r in results)


class TestTaskHistory(unittest.TestCase):
    """测试 read_task_history 函数"""

    def setUp(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.history_file = os.path.join(self.temp_dir, '.task_history.jsonl')

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_read_empty_history(self):
        """Handle missing history file"""
        # 切换到临时目录，使默认路径解析到临时目录
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            records = read_task_history(limit=100)
            self.assertEqual(records, [])
        finally:
            os.chdir(original_cwd)

    def test_read_history_with_records(self):
        """Read history with multiple records"""
        # 写入测试数据
        records = [
            {
                "timestamp": datetime.now().isoformat(),
                "task_id": "task-001",
                "status": "success",
                "duration": 120
            },
            {
                "timestamp": datetime.now().isoformat(),
                "task_id": "task-002",
                "status": "failed",
                "duration": 60
            }
        ]

        with open(self.history_file, 'w', encoding='utf-8') as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')

        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            result = read_task_history(limit=100)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["task_id"], "task-001")
            self.assertEqual(result[1]["task_id"], "task-002")
        finally:
            os.chdir(original_cwd)

    def test_read_history_respects_limit(self):
        """Limit parameter works"""
        # 写入多条测试数据
        with open(self.history_file, 'w', encoding='utf-8') as f:
            for i in range(10):
                record = {
                    "timestamp": datetime.now().isoformat(),
                    "task_id": f"task-{i:03d}",
                    "status": "success"
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')

        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            result = read_task_history(limit=5)
            self.assertEqual(len(result), 5)
        finally:
            os.chdir(original_cwd)


class TestWeeklyReport(unittest.TestCase):
    """测试 generate_weekly_report 函数"""

    def setUp(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.history_file = os.path.join(self.temp_dir, '.task_history.jsonl')

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_history(self, records):
        """Helper: 写入历史记录"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')

    def test_weekly_report_no_data(self):
        """Handle empty history"""
        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            report = generate_weekly_report(days=7, output_format="text")
            self.assertIn("没有任务历史记录", report)
        finally:
            os.chdir(original_cwd)

    def test_weekly_report_with_data(self):
        """Generate report with task data"""
        records = [
            {
                "timestamp": datetime.now().isoformat(),
                "task_id": "task-001",
                "status": "completed",
                "duration": 120
            },
            {
                "timestamp": datetime.now().isoformat(),
                "task_id": "task-002",
                "status": "completed",
                "duration": 90
            }
        ]
        self._write_history(records)

        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            report = generate_weekly_report(days=7, output_format="text")
            # 验证报告包含统计数据
            self.assertIn("任务总数: 2", report)
            self.assertIn("完成数: 2", report)
            self.assertIn("成功率: 100.0%", report)
        finally:
            os.chdir(original_cwd)

    def test_weekly_report_calculates_stats(self):
        """Statistics calculated correctly"""
        records = [
            {
                "timestamp": datetime.now().isoformat(),
                "task_id": "task-001",
                "status": "completed",
                "duration": 100
            },
            {
                "timestamp": datetime.now().isoformat(),
                "task_id": "task-002",
                "status": "completed",
                "duration": 200
            },
            {
                "timestamp": datetime.now().isoformat(),
                "task_id": "task-003",
                "status": "failed",
                "duration": 50
            }
        ]
        self._write_history(records)

        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            report = generate_weekly_report(days=7, output_format="text")

            # 验证统计数据
            self.assertIn("任务总数: 3", report)
            self.assertIn("完成数: 2", report)
            self.assertIn("失败数: 1", report)
        finally:
            os.chdir(original_cwd)

    def test_weekly_report_json_format(self):
        """JSON output format works"""
        records = [
            {
                "timestamp": datetime.now().isoformat(),
                "task_id": "task-001",
                "status": "success",
                "duration": 120,
                "lesson": "Test lesson"
            }
        ]
        self._write_history(records)

        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            report = generate_weekly_report(days=7, output_format="json")

            # 验证是有效JSON
            data = json.loads(report)
            self.assertEqual(data["total_tasks"], 1)
            self.assertEqual(data["completed"], 1)
            self.assertEqual(data["failed"], 0)
            self.assertIn("lessons", data)
        finally:
            os.chdir(original_cwd)

    def test_weekly_report_old_records_excluded(self):
        """Records older than period are excluded"""
        # 写入一条最近的记录和一条旧的记录
        records = [
            {
                "timestamp": datetime.now().isoformat(),
                "task_id": "task-recent",
                "status": "success",
                "duration": 100
            },
            {
                "timestamp": (datetime.now() - timedelta(days=30)).isoformat(),
                "task_id": "task-old",
                "status": "success",
                "duration": 100
            }
        ]
        self._write_history(records)

        original_cwd = os.getcwd()
        try:
            os.chdir(self.temp_dir)
            report = generate_weekly_report(days=7, output_format="text")

            # 旧记录应该被排除，只统计最近的1条记录
            self.assertIn("任务总数: 1", report)
            self.assertNotIn("task-old", report)
        finally:
            os.chdir(original_cwd)


def run_tests():
    """运行所有测试"""
    unittest.main(module=__name__, exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()
