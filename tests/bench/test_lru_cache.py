#!/usr/bin/env python3
"""
LRU Cache 测试 - TDD 方式验证实现

测试覆盖:
1. 基本 get/put 操作
2. LRU 淘汰逻辑
3. 容量边界
4. 更新已有 key
5. 错误处理
6. 辅助方法
7. 两种实现的等效性
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "utils"))
from lru_cache import LRUCache, LRUCacheManual


class TestLRUCacheBasic(unittest.TestCase):
    """基本操作测试"""

    def test_put_and_get(self):
        cache = LRUCache(capacity=2)
        cache.put(1, "a")
        cache.put(2, "b")
        self.assertEqual(cache.get(1), "a")
        self.assertEqual(cache.get(2), "b")

    def test_get_nonexistent(self):
        cache = LRUCache(capacity=2)
        self.assertEqual(cache.get(999), -1)

    def test_update_existing_key(self):
        cache = LRUCache(capacity=2)
        cache.put(1, "a")
        cache.put(1, "A")
        self.assertEqual(cache.get(1), "A")
        self.assertEqual(cache.size(), 1)

    def test_get_moves_to_recent(self):
        cache = LRUCache(capacity=2)
        cache.put(1, "a")
        cache.put(2, "b")
        cache.get(1)  # 访问 key=1
        cache.put(3, "c")  # 应淘汰 key=2 (最久未使用)
        self.assertEqual(cache.get(2), -1)
        self.assertEqual(cache.get(1), "a")
        self.assertEqual(cache.get(3), "c")


class TestLRUCacheEviction(unittest.TestCase):
    """LRU 淘汰逻辑测试"""

    def test_eviction_on_capacity(self):
        cache = LRUCache(capacity=2)
        cache.put(1, "a")
        cache.put(2, "b")
        cache.put(3, "c")  # 应淘汰 key=1
        self.assertEqual(cache.get(1), -1)
        self.assertEqual(cache.get(2), "b")
        self.assertEqual(cache.get(3), "c")

    def test_multiple_evictions(self):
        cache = LRUCache(capacity=3)
        for i in range(1, 6):
            cache.put(i, f"v{i}")
        # 淘汰了 1, 2
        self.assertEqual(cache.get(1), -1)
        self.assertEqual(cache.get(2), -1)
        self.assertEqual(cache.get(3), "v3")
        self.assertEqual(cache.get(4), "v4")
        self.assertEqual(cache.get(5), "v5")

    def test_eviction_after_update(self):
        cache = LRUCache(capacity=2)
        cache.put(1, "a")
        cache.put(2, "b")
        cache.put(1, "a2")  # 更新 key=1
        cache.put(3, "c")   # 应淘汰 key=2
        self.assertEqual(cache.get(1), "a2")
        self.assertEqual(cache.get(2), -1)
        self.assertEqual(cache.get(3), "c")


class TestLRUCacheEdgeCases(unittest.TestCase):
    """边界情况测试"""

    def test_capacity_one(self):
        cache = LRUCache(capacity=1)
        cache.put(1, "a")
        self.assertEqual(cache.get(1), "a")
        cache.put(2, "b")  # 淘汰 key=1
        self.assertEqual(cache.get(1), -1)
        self.assertEqual(cache.get(2), "b")

    def test_invalid_capacity_zero(self):
        with self.assertRaises(ValueError):
            LRUCache(capacity=0)

    def test_invalid_capacity_negative(self):
        with self.assertRaises(ValueError):
            LRUCache(capacity=-1)

    def test_empty_cache(self):
        cache = LRUCache(capacity=5)
        self.assertEqual(cache.size(), 0)
        self.assertEqual(cache.get(1), -1)
        self.assertEqual(cache.keys(), [])

    def test_none_value(self):
        cache = LRUCache(capacity=2)
        cache.put(1, None)
        self.assertIsNone(cache.get(1))  # 值为 None，返回 None（key 存在）
        self.assertEqual(cache.size(), 1)


class TestLRUCacheAuxMethods(unittest.TestCase):
    """辅助方法测试"""

    def test_contains(self):
        cache = LRUCache(capacity=2)
        cache.put(1, "a")
        self.assertTrue(cache.contains(1))
        self.assertFalse(cache.contains(2))

    def test_size(self):
        cache = LRUCache(capacity=3)
        self.assertEqual(cache.size(), 0)
        cache.put(1, "a")
        cache.put(2, "b")
        self.assertEqual(cache.size(), 2)

    def test_clear(self):
        cache = LRUCache(capacity=3)
        cache.put(1, "a")
        cache.put(2, "b")
        cache.clear()
        self.assertEqual(cache.size(), 0)
        self.assertEqual(cache.get(1), -1)

    def test_keys(self):
        cache = LRUCache(capacity=3)
        cache.put(1, "a")
        cache.put(2, "b")
        self.assertEqual(cache.keys(), [1, 2])

    def test_keys_order(self):
        cache = LRUCache(capacity=3)
        cache.put(1, "a")
        cache.put(2, "b")
        cache.put(3, "c")
        cache.get(1)  # key=1 变为最近使用
        # 顺序: 2, 3, 1
        self.assertEqual(cache.keys(), [2, 3, 1])

    def test_values(self):
        cache = LRUCache(capacity=3)
        cache.put(1, "a")
        cache.put(2, "b")
        self.assertEqual(cache.values(), ["a", "b"])

    def test_items(self):
        cache = LRUCache(capacity=3)
        cache.put(1, "a")
        cache.put(2, "b")
        self.assertEqual(cache.items(), [(1, "a"), (2, "b")])

    def test_len_dunder(self):
        cache = LRUCache(capacity=2)
        self.assertEqual(len(cache), 0)
        cache.put(1, "a")
        self.assertEqual(len(cache), 1)

    def test_contains_dunder(self):
        cache = LRUCache(capacity=2)
        cache.put(1, "a")
        self.assertTrue(1 in cache)
        self.assertFalse(2 in cache)

    def test_repr(self):
        cache = LRUCache(capacity=2)
        cache.put(1, "a")
        r = repr(cache)
        self.assertIn("LRUCache", r)
        self.assertIn("capacity=2", r)


class TestLRUCacheTypes(unittest.TestCase):
    """类型多样性测试"""

    def test_various_value_types(self):
        cache = LRUCache(capacity=5)
        cache.put(1, "string")
        cache.put(2, 123)
        cache.put(3, [1, 2, 3])
        cache.put(4, {"key": "value"})
        cache.put(5, (1, 2))

        self.assertEqual(cache.get(1), "string")
        self.assertEqual(cache.get(2), 123)
        self.assertEqual(cache.get(3), [1, 2, 3])
        self.assertEqual(cache.get(4), {"key": "value"})
        self.assertEqual(cache.get(5), (1, 2))

    def test_various_key_types(self):
        # 只能使用 int 或可哈希类型
        cache = LRUCache(capacity=3)
        cache.put(1, "a")
        cache.put(0, "b")
        cache.put(-1, "c")
        self.assertEqual(cache.get(1), "a")
        self.assertEqual(cache.get(0), "b")
        self.assertEqual(cache.get(-1), "c")


class TestLRUCacheManual(unittest.TestCase):
    """手动实现测试 - 确保双向链表版本与 OrderedDict 版本行为一致"""

    def _test_equivalence(self, operations: list, capacity: int = 2):
        ordered_cache = LRUCache(capacity)
        manual_cache = LRUCacheManual(capacity)

        for op in operations:
            op_type = op[0]
            if op_type == "put":
                _, k, v = op
                ordered_cache.put(k, v)
                manual_cache.put(k, v)
            elif op_type == "get":
                _, k = op
                o_result = ordered_cache.get(k)
                m_result = manual_cache.get(k)
                self.assertEqual(o_result, m_result,
                    f"get({k}): OrderedDict={o_result}, Manual={m_result}")

            # 每步都验证状态一致
            self.assertEqual(ordered_cache.size(), manual_cache.size(),
                f"Size mismatch after {op}")
            self.assertEqual(ordered_cache.keys(), manual_cache.keys(),
                f"Keys mismatch after {op}")

    def test_basic_operations(self):
        ops = [
            ("put", 1, "a"),
            ("put", 2, "b"),
            ("get", 1),
            ("put", 3, "c"),
            ("get", 2),
            ("get", 3),
            ("get", 1),
        ]
        self._test_equivalence(ops)

    def test_update_key(self):
        ops = [
            ("put", 1, "a"),
            ("put", 2, "b"),
            ("put", 1, "a2"),
            ("get", 1),
            ("put", 3, "c"),
            ("get", 2),
        ]
        self._test_equivalence(ops)

    def test_capacity_one(self):
        ops = [
            ("put", 1, "a"),
            ("get", 1),
            ("put", 2, "b"),
            ("get", 1),
            ("get", 2),
            ("put", 3, "c"),
            ("get", 2),
            ("get", 3),
        ]
        self._test_equivalence(ops, capacity=1)

    def test_many_operations(self):
        ops = []
        for i in range(20):
            ops.append(("put", i, f"v{i}"))
        for i in range(10):
            ops.append(("get", i))
        ops.append(("put", 100, "v100"))
        self._test_equivalence(ops, capacity=10)


class TestLRUCachePerformance(unittest.TestCase):
    """性能基准测试"""

    def test_large_cache(self):
        cache = LRUCache(capacity=1000)
        # 填充
        for i in range(1000):
            cache.put(i, f"v{i}")
        # 访问 500-999 使这些变为最近使用，0-499 保持最久未使用
        for i in range(500, 1000):
            cache.get(i)
        # 继续插入触发淘汰
        for i in range(1000, 1500):
            cache.put(i, f"v{i}")
        # 验证
        self.assertEqual(cache.size(), 1000)
        # 最久未使用的 (0-499) 应该被淘汰
        for i in range(500):
            self.assertEqual(cache.get(i), -1)
        # 最近使用的 (500-999) 应该保留
        for i in range(500, 1000):
            self.assertEqual(cache.get(i), f"v{i}")
        # 新插入的 (1000-1499) 应该保留
        for i in range(1000, 1500):
            self.assertEqual(cache.get(i), f"v{i}")


if __name__ == "__main__":
    unittest.main()
