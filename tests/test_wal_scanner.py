#!/usr/bin/env python3
"""
WAL Scanner 测试 - 测试 wal_scanner.py 的功能

覆盖:
- 触发检测 (correction, preference, decision, proper_noun)
- 模式计数和晋升
- 边界条件
"""

import os
import sys
import tempfile
import unittest

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

from wal_scanner import (
    PROMOTION_THRESHOLD,
    WAL_PATTERNS,
    get_pattern_key,
    get_pending_promotions,
    increment_pattern_count,
    load_patterns,
    promote_pattern,
    scan_wal_triggers,
    should_update_session_state,
)


class TestWALScanner(unittest.TestCase):
    """WAL Scanner 核心功能测试"""

    def setUp(self):
        """每个测试前创建临时文件"""
        self.temp_file = tempfile.mktemp(suffix='.json')
        # 确保测试开始时文件是干净的
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    def tearDown(self):
        """测试后清理"""
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)

    # ==================== 触发检测测试 ====================

    def test_correction_detection(self):
        """测试修正信息检测"""
        triggers = scan_wal_triggers("是X，不是Y，其实错了")
        self.assertIn('correction', triggers)

    def test_preference_positive(self):
        """测试正面偏好检测"""
        triggers = scan_wal_triggers("我喜欢用Python")
        self.assertIn('preference_positive', triggers)

    def test_preference_negative(self):
        """测试负面偏好检测"""
        triggers = scan_wal_triggers("我不喜欢用Java")
        self.assertIn('preference_negative', triggers)

    def test_decision(self):
        """测试决策检测"""
        triggers = scan_wal_triggers("用Python方案")
        self.assertIn('decision', triggers)

    def test_proper_noun(self):
        """测试专有名词检测"""
        triggers = scan_wal_triggers("这个叫微服务")
        self.assertIn('proper_noun', triggers)

    def test_no_triggers(self):
        """测试无触发情况"""
        triggers = scan_wal_triggers("今天天气真好")
        self.assertEqual(len(triggers), 0)

    # ==================== 数值检测测试 ====================

    def test_date_detection(self):
        """测试日期检测"""
        triggers = scan_wal_triggers("会议定在2024-01-15")
        self.assertIn('values', triggers)
        self.assertIn('date', triggers['values'])

    def test_url_detection(self):
        """测试URL检测"""
        triggers = scan_wal_triggers("参考 https://example.com")
        self.assertIn('values', triggers)
        self.assertIn('url', triggers['values'])

    def test_id_detection(self):
        """测试ID检测"""
        triggers = scan_wal_triggers("订单号 ABC123DEF")
        self.assertIn('values', triggers)
        self.assertIn('id', triggers['values'])

    # ==================== should_update_session_state 测试 ====================

    def test_should_update_true(self):
        """测试应该更新SESSION-STATE"""
        triggers = {'correction': ['不是']}
        self.assertTrue(should_update_session_state(triggers))

    def test_should_update_false(self):
        """测试不应该更新SESSION-STATE"""
        triggers = {}
        self.assertFalse(should_update_session_state(triggers))

    # ==================== 模式计数和晋升测试 ====================

    def test_pattern_key_generation(self):
        """测试模式键生成"""
        key = get_pattern_key('correction', '不是')
        self.assertEqual(key, 'correction_')

    def test_increment_count(self):
        """测试计数增加"""
        count, should_promote = increment_pattern_count('correction', '不是', self.temp_file)
        self.assertEqual(count, 1)
        self.assertFalse(should_promote)

    def test_promotion_threshold(self):
        """测试晋升阈值达到3次"""
        # 达到晋升阈值
        for _i in range(PROMOTION_THRESHOLD):
            count, should_promote = increment_pattern_count('correction', '不是', self.temp_file)

        self.assertEqual(count, PROMOTION_THRESHOLD)
        self.assertTrue(should_promote)

    def test_pending_promotions(self):
        """测试待晋升列表"""
        # 添加一个达到晋升阈值的模式
        for _i in range(PROMOTION_THRESHOLD):
            increment_pattern_count('decision', '用', self.temp_file)

        pending = get_pending_promotions(self.temp_file)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['type'], 'decision')

    def test_promote_pattern(self):
        """测试模式晋升"""
        # 先添加模式
        for _i in range(PROMOTION_THRESHOLD):
            increment_pattern_count('correction', '不是', self.temp_file)

        # 晋升
        key = get_pattern_key('correction', '不是')
        result = promote_pattern(key, self.temp_file)
        self.assertTrue(result)

        # 验证已晋升
        patterns = load_patterns(self.temp_file)
        self.assertTrue(patterns['patterns'][key]['promoted'])

    # ==================== 边界条件测试 ====================

    def test_empty_text(self):
        """测试空文本"""
        triggers = scan_wal_triggers("")
        self.assertEqual(len(triggers), 0)

    def test_mixed_triggers(self):
        """测试混合触发"""
        triggers = scan_wal_triggers("我喜欢Python，用这个方案")
        self.assertIn('preference_positive', triggers)
        self.assertIn('decision', triggers)

    def test_load_invalid_json(self):
        """测试加载无效JSON"""
        # 创建无效JSON文件
        with open(self.temp_file, 'w') as f:
            f.write('invalid json')

        patterns = load_patterns(self.temp_file)
        self.assertEqual(patterns['patterns'], {})

    def test_load_empty_file(self):
        """测试加载不存在的文件"""
        patterns = load_patterns('/nonexistent/path.json')
        self.assertEqual(patterns['patterns'], {})


class TestWALPatterns(unittest.TestCase):
    """WAL Patterns 正则表达式测试"""

    def test_correction_patterns(self):
        """测试修正模式正则"""
        correction_keywords = ['不是', '其实', '错了', '不对', '更正']
        for kw in correction_keywords:
            for pattern, ptype in WAL_PATTERNS:
                if ptype == 'correction':
                    import re
                    matches = re.findall(pattern, kw)
                    self.assertTrue(len(matches) > 0, f"Pattern should match '{kw}'")

    def test_preference_patterns(self):
        """测试偏好模式正则"""
        positive_keywords = ['我喜欢', '我想要', '我倾向', '我更喜欢']
        for kw in positive_keywords:
            for pattern, ptype in WAL_PATTERNS:
                if ptype == 'preference_positive':
                    import re
                    matches = re.findall(pattern, kw)
                    self.assertTrue(len(matches) > 0, f"Pattern should match '{kw}'")


def run_tests():
    """运行所有测试"""
    unittest.main(module=__name__, exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()
