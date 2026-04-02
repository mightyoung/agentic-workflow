#!/usr/bin/env python3
"""
Evaluation Scripts Test - 评估脚本测试

测试新增的评估机制：
- run_tracker.py
- step_recorder.py
- reward_calculator.py
- experience_store.py
- pattern_detector.py
"""

import os
import sys
import tempfile
import unittest

# 添加 scripts 路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))


class TestRunTracker(unittest.TestCase):
    """Run Tracker 测试"""

    def setUp(self):
        self.temp_file = tempfile.mktemp(suffix='.json')
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def tearDown(self):
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def test_start_run(self):
        from run_tracker import load_tracker, start_run
        result = start_run('R001', 'DEBUGGING', 'Test run', self.temp_file)
        self.assertTrue(result)

        tracker = load_tracker(self.temp_file)
        self.assertEqual(len(tracker['runs']), 1)
        self.assertEqual(tracker['runs'][0]['run_id'], 'R001')

    def test_record_step(self):
        from run_tracker import load_tracker, record_step, start_run
        start_run('R001', 'DEBUGGING', path=self.temp_file)
        result = record_step('R001', 'THINKING', 500, False, self.temp_file)
        self.assertTrue(result)

        tracker = load_tracker(self.temp_file)
        run = tracker['runs'][0]
        self.assertEqual(len(run['steps']), 1)
        self.assertEqual(run['steps'][0]['step'], 'THINKING')

    def test_finish_run(self):
        from run_tracker import finish_run, start_run
        start_run('R001', 'DEBUGGING', path=self.temp_file)
        result = finish_run('R001', True, self.temp_file)
        self.assertIn('duration_ms', result)


class TestStepRecorder(unittest.TestCase):
    """Step Recorder 测试"""

    def setUp(self):
        self.temp_file = tempfile.mktemp(suffix='.json')
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def tearDown(self):
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def test_start_phase(self):
        from step_recorder import load_records, start_phase
        result = start_phase('R001', 'THINKING', 500, self.temp_file)
        self.assertTrue(result)

        records = load_records(self.temp_file)
        self.assertEqual(len(records['records']), 1)

    def test_end_phase(self):
        from step_recorder import end_phase, start_phase
        start_phase('R001', 'THINKING', 500, self.temp_file)
        result = end_phase('R001', 'THINKING', 300, path=self.temp_file)
        self.assertTrue(result)

    def test_phase_report(self):
        from step_recorder import end_phase, get_phase_report, start_phase
        start_phase('R001', 'THINKING', 500, self.temp_file)
        end_phase('R001', 'THINKING', 300, path=self.temp_file)

        report = get_phase_report('R001', self.temp_file)
        self.assertEqual(report['total_phases'], 1)
        self.assertIn('total_duration_s', report)


class TestRewardCalculator(unittest.TestCase):
    """Reward Calculator 测试"""

    def test_efficiency_reward(self):
        from reward_calculator import calculate_efficiency_reward

        # steps <= max_steps 时应该正奖励
        reward = calculate_efficiency_reward(10, 20)
        self.assertGreater(reward, 0)

        # steps > max_steps 时返回 0 (不奖励但也不惩罚)
        reward = calculate_efficiency_reward(25, 20)
        self.assertEqual(reward, 0)

    def test_calculate_reward(self):
        from reward_calculator import calculate_reward

        result = calculate_reward(
            success=True,
            steps=10,
            tokens=500,
            max_steps=20,
            max_tokens=1000,
            error_count=0,
            quality_score=0.8
        )

        self.assertIn('task_completion', result)
        self.assertIn('efficiency', result)
        self.assertIn('total', result)
        self.assertGreater(result['task_completion'], 0)

    def test_failure_penalty(self):
        from reward_calculator import calculate_reward

        result = calculate_reward(
            success=False,
            steps=10,
            tokens=500,
            error_count=2
        )

        self.assertLess(result['task_completion'], 0)
        self.assertLess(result['penalty'], 0)


class TestExperienceStore(unittest.TestCase):
    """Experience Store 测试"""

    def setUp(self):
        self.temp_file = tempfile.mktemp(suffix='.json')
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def tearDown(self):
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def test_add_experience(self):
        from experience_store import add_experience, load_store
        add_experience('DEBUGGING', True, 10, 500, 5000,
                      error_count=0, reward_total=0.8,
                      description='Test', path=self.temp_file)

        store = load_store(self.temp_file)
        self.assertEqual(len(store['experiences']), 1)

    def test_query_experiences(self):
        from experience_store import add_experience, query_experiences
        add_experience('DEBUGGING', True, 10, 500, 5000,
                      reward_total=0.8, path=self.temp_file)
        add_experience('CODE_GENERATION', True, 15, 800, 6000,
                      reward_total=0.9, path=self.temp_file)

        results = query_experiences(category='DEBUGGING', path=self.temp_file)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['task_category'], 'DEBUGGING')

    def test_get_stats(self):
        from experience_store import add_experience, get_overall_stats
        add_experience('DEBUGGING', True, 10, 500, 5000,
                      reward_total=0.8, path=self.temp_file)

        stats = get_overall_stats(self.temp_file)
        self.assertEqual(stats['total_experiences'], 1)


class TestPatternDetector(unittest.TestCase):
    """Pattern Detector 测试"""

    def test_detect_error_pattern(self):
        from pattern_detector import detect_error_pattern

        # 无错误
        result = detect_error_pattern([])
        self.assertFalse(result['has_patterns'])

        # 重复错误
        errors = ['timeout', 'timeout', 'connection_error', 'timeout']
        result = detect_error_pattern(errors)
        self.assertTrue(result['has_patterns'])
        self.assertIn('timeout', result['repeated_errors'])

    def test_analyze_run(self):
        from pattern_detector import analyze_run

        run_data = {
            'run_id': 'R001',
            'errors': ['timeout', 'timeout'],
            'steps': [{'phase': 'THINKING', 'duration_ms': 100}],
            'total_tokens': 500,
            'duration_ms': 5000
        }

        result = analyze_run(run_data)
        self.assertEqual(result['run_id'], 'R001')
        self.assertTrue(len(result['suggestions']) > 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
