#!/usr/bin/env python3
"""
Task Tracker 测试 - 测试 task_tracker.py 的功能

覆盖:
- 任务创建
- 任务计时和预算控制
- 状态更新
- 质量门禁跟踪
- 数据迁移
"""

import os
import sys
import json
import tempfile
import unittest

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

from task_tracker import (
    load_tracker,
    create_task,
    start_task,
    update_status,
    check_task_budget,
    update_quality_gate,
    get_task,
    list_tasks,
    record_step_failure,
    check_circuit_state,
    reset_circuit
)


class TestTaskTracker(unittest.TestCase):
    """Task Tracker 核心功能测试"""

    def setUp(self):
        """每个测试前创建临时文件"""
        self.temp_file = tempfile.mktemp(suffix='.json')
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    # ==================== 创建和加载测试 ====================

    def test_create_task(self):
        """测试任务创建"""
        result = create_task(
            'T001', '测试任务',
            path=self.temp_file,
            budget_seconds=60
        )
        self.assertTrue(result)

        # 验证任务已创建
        tracker = load_tracker(self.temp_file)
        self.assertEqual(len(tracker['tasks']), 1)
        self.assertEqual(tracker['tasks'][0]['id'], 'T001')

    def test_create_duplicate_task(self):
        """测试重复创建任务"""
        create_task('T001', '任务1', path=self.temp_file)
        result = create_task('T001', '任务2', path=self.temp_file)
        self.assertFalse(result)

    def test_load_tracker_new_file(self):
        """测试加载不存在的文件"""
        tracker = load_tracker('/nonexistent/path.json')
        self.assertEqual(tracker['tasks'], [])
        self.assertEqual(tracker['version'], '1.0')

    def test_load_tracker_with_migration(self):
        """测试旧数据迁移"""
        # 创建旧格式数据
        old_data = {
            "tasks": [{
                "id": "TOLD",
                "description": "旧任务",
                "status": "pending",
                "priority": "P2",
                "dependencies": [],
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "progress": 0,
                "issues": []
            }],
            "version": "1.0"
        }
        with open(self.temp_file, 'w') as f:
            json.dump(old_data, f)

        # 加载应该触发迁移
        tracker = load_tracker(self.temp_file)
        task = tracker['tasks'][0]

        # 验证新字段已添加
        self.assertEqual(task['id'], 'TOLD')
        self.assertEqual(task['budget_seconds'], 300)  # 默认值
        self.assertEqual(task['time_spent_seconds'], 0)
        self.assertIsNone(task['started_at'])
        self.assertIsNone(task['quality_gates_passed'])

    # ==================== 计时和预算测试 ====================

    def test_start_task(self):
        """测试启动任务"""
        create_task('T001', '测试任务', path=self.temp_file)
        result = start_task('T001', self.temp_file)
        self.assertTrue(result)

        # 验证 started_at 已设置
        task = get_task('T001', self.temp_file)
        self.assertIsNotNone(task['started_at'])
        self.assertEqual(task['status'], 'in_progress')

    def test_start_already_started(self):
        """测试重复启动任务"""
        create_task('T001', '测试任务', path=self.temp_file)
        start_task('T001', self.temp_file)
        result = start_task('T001', self.temp_file)
        self.assertFalse(result)

    def test_check_budget_not_started(self):
        """测试未启动任务的预算"""
        create_task('T001', '测试任务', budget_seconds=60, path=self.temp_file)
        result = check_task_budget('T001', self.temp_file)

        self.assertFalse(result['started'])
        self.assertEqual(result['budget_seconds'], 60)
        self.assertEqual(result['time_spent_seconds'], 0)
        self.assertFalse(result['over_budget'])

    def test_check_budget_in_progress(self):
        """测试进行中任务的预算"""
        create_task('T001', '测试任务', budget_seconds=300, path=self.temp_file)
        start_task('T001', self.temp_file)
        result = check_task_budget('T001', self.temp_file)

        self.assertTrue(result['started'])
        self.assertEqual(result['budget_seconds'], 300)
        self.assertGreaterEqual(result['time_spent_seconds'], 0)
        self.assertFalse(result['over_budget'])

    # ==================== 状态更新测试 ====================

    def test_update_status(self):
        """测试状态更新"""
        create_task('T001', '测试任务', path=self.temp_file)
        result = update_status('T001', 'in_progress', progress=50, path=self.temp_file)
        self.assertTrue(result)

        task = get_task('T001', self.temp_file)
        self.assertEqual(task['status'], 'in_progress')
        self.assertEqual(task['progress'], 50)

    def test_update_nonexistent_task(self):
        """测试更新不存在的任务"""
        result = update_status('T999', 'in_progress', path=self.temp_file)
        self.assertFalse(result)

    # ==================== 质量门禁测试 ====================

    def test_update_quality_gate_pass(self):
        """测试更新质量门禁通过"""
        create_task('T001', '测试任务', path=self.temp_file)
        result = update_quality_gate('T001', True, self.temp_file)
        self.assertTrue(result)

        task = get_task('T001', self.temp_file)
        self.assertTrue(task['quality_gates_passed'])

    def test_update_quality_gate_fail(self):
        """测试更新质量门禁失败"""
        create_task('T001', '测试任务', path=self.temp_file)
        result = update_quality_gate('T001', False, self.temp_file)
        self.assertTrue(result)

        task = get_task('T001', self.temp_file)
        self.assertFalse(task['quality_gates_passed'])

    # ==================== 列表和获取测试 ====================

    def test_get_task(self):
        """测试获取任务"""
        create_task('T001', '任务1', path=self.temp_file)
        create_task('T002', '任务2', path=self.temp_file)

        task = get_task('T002', self.temp_file)
        self.assertEqual(task['id'], 'T002')
        self.assertEqual(task['description'], '任务2')

    def test_get_nonexistent_task(self):
        """测试获取不存在的任务"""
        task = get_task('T999', self.temp_file)
        self.assertIsNone(task)

    def test_list_tasks(self):
        """测试列出任务"""
        create_task('T001', '任务1', path=self.temp_file)
        create_task('T002', '任务2', path=self.temp_file)
        update_status('T001', 'in_progress', path=self.temp_file)

        all_tasks = list_tasks(path=self.temp_file)
        self.assertEqual(len(all_tasks), 2)

        in_progress = list_tasks('in_progress', self.temp_file)
        self.assertEqual(len(in_progress), 1)
        self.assertEqual(in_progress[0]['id'], 'T001')


class TestTaskTrackerEdgeCases(unittest.TestCase):
    """边界条件测试"""

    def setUp(self):
        self.temp_file = tempfile.mktemp(suffix='.json')
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def tearDown(self):
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def test_create_task_with_dependencies(self):
        """测试带依赖的任务创建"""
        create_task('T001', '任务1', path=self.temp_file)
        create_task('T002', '任务2', dependencies=['T001'], path=self.temp_file)

        task = get_task('T002', self.temp_file)
        self.assertEqual(task['dependencies'], ['T001'])

    def test_create_task_with_priority(self):
        """测试带优先级的任务创建"""
        create_task('T001', '紧急任务', priority='P0', path=self.temp_file)
        task = get_task('T001', self.temp_file)
        self.assertEqual(task['priority'], 'P0')


class TestCircuitBreaker(unittest.TestCase):
    """Tests for circuit breaker functionality"""

    def setUp(self):
        """每个测试前创建临时文件和任务"""
        self.temp_file = tempfile.mktemp(suffix='.json')
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)
        # 创建测试任务
        create_task('T001', '测试任务', path=self.temp_file)

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def test_record_step_failure_first(self):
        """First failure should not trip circuit"""
        result = record_step_failure('T001', 'step1', path=self.temp_file)
        self.assertFalse(result['tripped'])
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['step'], 'step1')

    def test_record_step_failure_second(self):
        """Second failure should not trip circuit"""
        record_step_failure('T001', 'step1', path=self.temp_file)
        result = record_step_failure('T001', 'step1', path=self.temp_file)
        self.assertFalse(result['tripped'])
        self.assertEqual(result['count'], 2)

    def test_record_step_failure_third_trips(self):
        """Third failure should trip circuit"""
        record_step_failure('T001', 'step1', path=self.temp_file)
        record_step_failure('T001', 'step1', path=self.temp_file)
        result = record_step_failure('T001', 'step1', path=self.temp_file)
        self.assertTrue(result['tripped'])
        self.assertEqual(result['count'], 3)

    def test_record_step_failure_custom_threshold(self):
        """Custom threshold should work"""
        record_step_failure('T001', 'step1', threshold=5, path=self.temp_file)
        record_step_failure('T001', 'step1', threshold=5, path=self.temp_file)
        result = record_step_failure('T001', 'step1', threshold=5, path=self.temp_file)
        self.assertFalse(result['tripped'])
        self.assertEqual(result['count'], 3)

        # Fourth failure still doesn't trip with threshold=5
        result = record_step_failure('T001', 'step1', threshold=5, path=self.temp_file)
        self.assertFalse(result['tripped'])
        self.assertEqual(result['count'], 4)

        # Fifth failure trips with threshold=5
        result = record_step_failure('T001', 'step1', threshold=5, path=self.temp_file)
        self.assertTrue(result['tripped'])
        self.assertEqual(result['count'], 5)

    def test_check_circuit_state_specific_step(self):
        """Check circuit state for specific step"""
        record_step_failure('T001', 'step1', path=self.temp_file)
        record_step_failure('T001', 'step1', path=self.temp_file)

        result = check_circuit_state('T001', 'step1', path=self.temp_file)
        self.assertEqual(result['task_id'], 'T001')
        self.assertEqual(result['step'], 'step1')
        self.assertEqual(result['failure_count'], 2)
        self.assertFalse(result['circuit_open'])

    def test_check_circuit_state_all_steps(self):
        """Check circuit state for all steps"""
        record_step_failure('T001', 'step1', path=self.temp_file)
        record_step_failure('T001', 'step2', path=self.temp_file)
        record_step_failure('T001', 'step2', path=self.temp_file)

        result = check_circuit_state('T001', path=self.temp_file)
        self.assertEqual(result['task_id'], 'T001')
        self.assertEqual(result['steps']['step1'], 1)
        self.assertEqual(result['steps']['step2'], 2)

    def test_check_circuit_state_no_failures(self):
        """Check circuit when no failures recorded"""
        result = check_circuit_state('T001', 'step1', path=self.temp_file)
        self.assertEqual(result['task_id'], 'T001')
        self.assertEqual(result['step'], 'step1')
        self.assertEqual(result['failure_count'], 0)
        self.assertFalse(result['circuit_open'])

    def test_reset_circuit_specific_step(self):
        """Reset circuit for specific step"""
        record_step_failure('T001', 'step1', path=self.temp_file)
        record_step_failure('T001', 'step1', path=self.temp_file)
        record_step_failure('T001', 'step2', path=self.temp_file)

        result = reset_circuit('T001', 'step1', path=self.temp_file)
        self.assertTrue(result)

        # step1 should be reset
        state = check_circuit_state('T001', 'step1', path=self.temp_file)
        self.assertEqual(state['failure_count'], 0)

        # step2 should still have failures
        state = check_circuit_state('T001', 'step2', path=self.temp_file)
        self.assertEqual(state['failure_count'], 1)

    def test_reset_circuit_all_steps(self):
        """Reset all circuits for task"""
        record_step_failure('T001', 'step1', path=self.temp_file)
        record_step_failure('T001', 'step2', path=self.temp_file)
        record_step_failure('T001', 'step3', path=self.temp_file)

        result = reset_circuit('T001', path=self.temp_file)
        self.assertTrue(result)

        state = check_circuit_state('T001', path=self.temp_file)
        self.assertEqual(state['steps'], {})

    def test_circuit_resets_after_success(self):
        """Circuit should reset after successful step"""
        # Record some failures
        record_step_failure('T001', 'step1', path=self.temp_file)
        record_step_failure('T001', 'step1', path=self.temp_file)

        # Reset the circuit
        result = reset_circuit('T001', 'step1', path=self.temp_file)
        self.assertTrue(result)

        # Verify it's reset
        state = check_circuit_state('T001', 'step1', path=self.temp_file)
        self.assertEqual(state['failure_count'], 0)
        self.assertFalse(state['circuit_open'])

        # Record failures again - should start fresh
        record_step_failure('T001', 'step1', path=self.temp_file)
        record_step_failure('T001', 'step1', path=self.temp_file)
        record_step_failure('T001', 'step1', path=self.temp_file)

        state = check_circuit_state('T001', 'step1', path=self.temp_file)
        self.assertEqual(state['failure_count'], 3)
        self.assertTrue(state['circuit_open'])


def run_tests():
    """运行所有测试"""
    unittest.main(module=__name__, exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()
