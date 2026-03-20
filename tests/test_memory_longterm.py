#!/usr/bin/env python3
"""
Long-term Memory Operations 测试 - 测试 memory_longterm.py 的功能

覆盖:
- read_task_history - 读取任务历史
- generate_weekly_report - 生成周报
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

from memory_longterm import (
    read_task_history,
    generate_weekly_report,
    DEFAULT_MEMORY_FILE
)


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
