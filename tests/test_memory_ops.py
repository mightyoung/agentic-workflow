#!/usr/bin/env python3
"""
Memory Ops 测试 - 测试 memory_ops.py 的功能

覆盖:
- SESSION-STATE 创建
- 修正记录添加
- 偏好记录添加
- 决策记录添加
- 数值记录添加
"""

import os
import sys
import tempfile
import unittest

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

from memory_ops import (
    add_correction,
    add_decision,
    add_preference,
    add_task_result,
    add_value,
    check_idle_status,
    ensure_session_state_exists,
    get_info,
    show_session_state,
    update_task_info,
)


class TestMemoryOps(unittest.TestCase):
    """Memory Ops 核心功能测试"""

    def setUp(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_session = os.path.join(self.temp_dir, 'SESSION-STATE.md')

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ==================== SESSION-STATE 基本操作测试 ====================

    def test_ensure_session_state_exists_creates_file(self):
        """测试确保 SESSION-STATE 存在"""
        result = ensure_session_state_exists(self.temp_session)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.temp_session))

    def test_ensure_session_state_exists_reads_existing(self):
        """测试读取已存在的 SESSION-STATE"""
        # 先创建
        ensure_session_state_exists(self.temp_session)
        # 再读取 - 返回False表示文件已存在，无需创建
        result = ensure_session_state_exists(self.temp_session)
        self.assertFalse(result)

    def test_session_state_not_exists_read(self):
        """测试读取不存在的 SESSION-STATE"""
        # 应该返回 False 但不抛异常
        result = ensure_session_state_exists('/nonexistent/SESSION-STATE.md')
        self.assertFalse(result)

    # ==================== 任务更新测试 ====================

    def test_update_task_info(self):
        """测试更新任务信息"""
        ensure_session_state_exists(self.temp_session)

        result = update_task_info(
            self.temp_session,
            '测试任务',
            'EXECUTING'
        )
        self.assertTrue(result)

    def test_update_task_info_invalid_path(self):
        """测试更新无效路径的任务信息"""
        result = update_task_info(
            '/invalid/path/SESSION-STATE.md',
            '测试任务',
            'EXECUTING'
        )
        self.assertFalse(result)

    # ==================== 修正记录测试 ====================

    def test_add_correction(self):
        """测试添加修正记录"""
        ensure_session_state_exists(self.temp_session)

        result = add_correction(
            self.temp_session,
            '错误理解',
            '正确理解'
        )
        self.assertTrue(result)

    def test_add_correction_invalid_path(self):
        """测试添加修正到无效路径"""
        result = add_correction(
            '/invalid/path/SESSION-STATE.md',
            '错误',
            '正确'
        )
        self.assertFalse(result)

    # ==================== 偏好记录测试 ====================

    def test_add_preference(self):
        """测试添加偏好记录"""
        ensure_session_state_exists(self.temp_session)

        result = add_preference(
            self.temp_session,
            'Python',
            'JavaScript'
        )
        self.assertTrue(result)

    def test_add_preference_partial(self):
        """测试部分偏好（只喜欢）"""
        ensure_session_state_exists(self.temp_session)

        result = add_preference(
            self.temp_session,
            'Python',
            None
        )
        self.assertTrue(result)

    # ==================== 决策记录测试 ====================

    def test_add_decision(self):
        """测试添加决策记录"""
        ensure_session_state_exists(self.temp_session)

        result = add_decision(
            self.temp_session,
            '选择微服务架构',
            '因为需要高可用'
        )
        self.assertTrue(result)

    def test_add_decision_without_reason(self):
        """测试添加决策（无原因）"""
        ensure_session_state_exists(self.temp_session)

        result = add_decision(
            self.temp_session,
            '选择单体架构'
        )
        self.assertTrue(result)

    # ==================== 数值记录测试 ====================

    def test_add_value(self):
        """测试添加数值记录"""
        ensure_session_state_exists(self.temp_session)

        result = add_value(
            self.temp_session,
            'API_KEY',
            'sk-12345678'
        )
        self.assertTrue(result)

    # ==================== 信息获取测试 ====================

    def test_get_info(self):
        """测试获取信息"""
        ensure_session_state_exists(self.temp_session)
        update_task_info(self.temp_session, '新任务', 'PLANNING')

        info = get_info(self.temp_session, 'task')
        self.assertIsNotNone(info)
        self.assertIn('新任务', info)

    def test_get_info_invalid_path(self):
        """测试获取无效路径的信息"""
        info = get_info('/invalid/path/SESSION-STATE.md', 'task')
        self.assertIsNone(info)

    def test_get_info_nonexistent_key(self):
        """测试获取不存在的键"""
        ensure_session_state_exists(self.temp_session)
        info = get_info(self.temp_session, 'nonexistent_key')
        self.assertIsNone(info)


class TestMemoryOpsEdgeCases(unittest.TestCase):
    """边界条件测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_session = os.path.join(self.temp_dir, 'SESSION-STATE.md')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_multiple_operations(self):
        """测试多次操作"""
        ensure_session_state_exists(self.temp_session)

        # 添加多个修正
        add_correction(self.temp_session, '错1', '对1')
        add_correction(self.temp_session, '错2', '对2')

        # 添加偏好
        add_preference(self.temp_session, 'A', 'B')

        # 添加决策
        add_decision(self.temp_session, '决策1', '原因1')
        add_decision(self.temp_session, '决策2')

        # 验证都能添加
        _ = show_session_state(self.temp_session)

    def test_special_characters_in_values(self):
        """测试特殊字符的数值"""
        ensure_session_state_exists(self.temp_session)

        # URL
        result = add_value(self.temp_session, 'URL', 'https://example.com?a=1&b=2')
        self.assertTrue(result)

        # 中文
        result = add_value(self.temp_session, '名称', '微服务架构')
        self.assertTrue(result)


def run_tests():
    """运行所有测试"""
    unittest.main(module=__name__, exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()


class TestIdleDetection(unittest.TestCase):
    """测试 check_idle_status 函数"""

    def setUp(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_session = os.path.join(self.temp_dir, 'SESSION-STATE.md')

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_check_idle_status_recent_activity(self):
        """Active session should not be idle"""
        ensure_session_state_exists(self.temp_session)

        result = check_idle_status(self.temp_session, idle_threshold_minutes=30)

        self.assertFalse(result["is_idle"])
        self.assertEqual(result["idle_minutes"], 0)
        self.assertIsNotNone(result["last_active"])

    def test_check_idle_status_old_activity(self):
        """Session with old timestamp should be idle"""
        ensure_session_state_exists(self.temp_session)

        # 修改开始时间为2小时前
        from datetime import datetime, timedelta
        old_time = (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        with open(self.temp_session, encoding='utf-8') as f:
            content = f.read()
        content = content.replace(
            f"**开始时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**开始时间**: {old_time}"
        )
        with open(self.temp_session, 'w', encoding='utf-8') as f:
            f.write(content)

        result = check_idle_status(self.temp_session, idle_threshold_minutes=30)

        self.assertTrue(result["is_idle"])
        self.assertGreaterEqual(result["idle_minutes"], 60)

    def test_check_idle_status_no_file(self):
        """Graceful handling when file doesn't exist"""
        result = check_idle_status('/nonexistent/SESSION-STATE.md', idle_threshold_minutes=30)

        self.assertFalse(result["is_idle"])
        self.assertEqual(result["idle_minutes"], 0)
        self.assertIsNone(result["last_active"])


class TestResultTracking(unittest.TestCase):
    """测试 add_task_result 函数"""

    def setUp(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_session = os.path.join(self.temp_dir, 'SESSION-STATE.md')
        ensure_session_state_exists(self.temp_session)

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_task_result_success(self):
        """Record successful task result"""
        result = add_task_result(
            self.temp_session,
            'task-001',
            'success',
            120,
            ['Lesson 1', 'Lesson 2'],
            ['Next action 1']
        )
        self.assertTrue(result)

    def test_add_task_result_failure(self):
        """Record failed task result"""
        result = add_task_result(
            self.temp_session,
            'task-002',
            'failed',
            60,
            ['Failed lesson'],
            ['Recovery action']
        )
        self.assertTrue(result)

    def test_add_task_result_partial(self):
        """Record partial success result"""
        result = add_task_result(
            self.temp_session,
            'task-003',
            'partial',
            90,
            ['Partial lesson'],
            []
        )
        self.assertTrue(result)

    def test_add_task_result_reads_back(self):
        """Verify result was written to history"""
        add_task_result(
            self.temp_session,
            'task-004',
            'success',
            45,
            ['Test lesson'],
            []
        )

        # 验证历史文件存在并可读取
        history_file = os.path.join(self.temp_dir, '.task_history.jsonl')
        self.assertTrue(os.path.exists(history_file))

        with open(history_file, encoding='utf-8') as f:
            content = f.read()
        self.assertIn('task-004', content)
        self.assertIn('success', content)

    def test_add_task_result_invalid_path(self):
        """Test with invalid path returns False"""
        result = add_task_result(
            '/invalid/path/SESSION-STATE.md',
            'task-005',
            'success',
            30,
            [],
            []
        )
        self.assertFalse(result)
