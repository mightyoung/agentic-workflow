#!/usr/bin/env python3
"""
LRU Cache 实现 - 基于 OrderedDict 的 O(1) 实现

实现要求:
- get(key): O(1) 时间复杂度
- put(key, value): O(1) 时间复杂度
- 容量超限时自动淘汰最久未使用的条目
"""

from collections import OrderedDict
from typing import Any, Optional, Tuple, List


class LRUCache:
    """
    LRU (Least Recently Used) Cache 实现

    使用 Python OrderedDict 维护插入/访问顺序,
    每次访问或插入时将对应 key 移至末尾,
    容量超限时从头部淘汰最久未使用的条目。

    时间复杂度: O(1) for both get and put

    示例:
        >>> cache = LRUCache(capacity=2)
        >>> cache.put(1, "a")
        >>> cache.put(2, "b")
        >>> cache.get(1)  # 返回 "a"，key=1 变为最新
        'a'
        >>> cache.put(3, "c")  # 淘汰 key=2 (最久未使用)
        >>> cache.get(2)  # key=2 已被淘汰
        None
    """

    def __init__(self, capacity: int) -> None:
        """
        初始化 LRU Cache

        Args:
            capacity: 缓存容量，必须为正整数

        Raises:
            ValueError: 当 capacity <= 0 时抛出
        """
        if capacity <= 0:
            raise ValueError(f"Capacity must be positive, got {capacity}")
        self._capacity = capacity
        self._cache: OrderedDict[int, Any] = OrderedDict()

    def get(self, key: int) -> int | Any:
        """
        获取缓存值并将对应 key 标记为最近使用

        Args:
            key: 要获取的键

        Returns:
            缓存的值，若 key 不存在则返回 -1
        """
        if key not in self._cache:
            return -1
        # 移至末尾表示最近使用
        self._cache.move_to_end(key)
        return self._cache[key]

    def put(self, key: int, value: Any) -> None:
        """
        插入或更新缓存值

        Args:
            key: 缓存键
            value: 缓存值

        Note:
            - 若 key 已存在，更新值并标记为最近使用
            - 若缓存满，淘汰最久未使用的条目再插入
        """
        if key in self._cache:
            # 已存在，更新并移至末尾
            self._cache.move_to_end(key)
            self._cache[key] = value
        else:
            # 新插入
            if len(self._cache) >= self._capacity:
                # 淘汰最久未使用的 (头部)
                self._cache.popitem(last=False)
            self._cache[key] = value

    def contains(self, key: int) -> bool:
        """检查 key 是否存在于缓存中"""
        return key in self._cache

    def size(self) -> int:
        """返回当前缓存条目数量"""
        return len(self._cache)

    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()

    def keys(self) -> List[int]:
        """返回所有 key 列表（按最近使用顺序）"""
        return list(self._cache.keys())

    def values(self) -> List[Any]:
        """返回所有 value 列表（按最近使用顺序）"""
        return list(self._cache.values())

    def items(self) -> List[Tuple[int, Any]]:
        """返回所有 (key, value) 列表（按最近使用顺序）"""
        return list(self._cache.items())

    def __len__(self) -> int:
        return len(self._cache)

    def __repr__(self) -> str:
        items = ", ".join(f"{k}: {v!r}" for k, v in self._cache.items())
        return f"LRUCache(capacity={self._capacity}, items=[{items}])"

    def __contains__(self, key: int) -> bool:
        return key in self._cache


# ============================================================
# 手动双向链表实现（用于对比学习和理解底层原理）
# ============================================================


class _Node:
    """双向链表节点"""
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: int = 0, value: Any = None) -> None:
        self.key = key
        self.value = value
        self.prev: Optional[_Node] = None
        self.next: Optional[_Node] = None


class LRUCacheManual:
    """
    LRU Cache 手动实现 - 使用双向链表 + 哈希表

    数据结构:
    - 双向链表: 维护访问顺序，头部是最久未使用，尾部是最近使用
    - 哈希表: O(1) 查找节点

    时间复杂度: O(1) for both get and put
    """

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError(f"Capacity must be positive, got {capacity}")
        self._capacity = capacity
        self._map: dict[int, _Node] = {}
        # 虚拟头尾节点简化边界处理
        self._head = _Node()  # 哨兵节点
        self._tail = _Node()  # 哨兵节点
        self._head.next = self._tail
        self._tail.prev = self._head

    def _remove(self, node: _Node) -> None:
        """从双向链表中移除节点"""
        node.prev.next = node.next
        node.next.prev = node.prev

    def _add_to_tail(self, node: _Node) -> None:
        """将节点添加到链表尾部（最近使用）"""
        node.prev = self._tail.prev
        node.next = self._tail
        self._tail.prev.next = node
        self._tail.prev = node

    def get(self, key: int) -> int | Any:
        if key not in self._map:
            return -1
        node = self._map[key]
        # 移至尾部（最近使用）
        self._remove(node)
        self._add_to_tail(node)
        return node.value

    def put(self, key: int, value: Any) -> None:
        if key in self._map:
            node = self._map[key]
            node.value = value
            self._remove(node)
            self._add_to_tail(node)
        else:
            if len(self._map) >= self._capacity:
                # 淘汰最久未使用（头部哨兵后的节点）
                removed = self._head.next
                self._remove(removed)
                del self._map[removed.key]
            new_node = _Node(key, value)
            self._map[key] = new_node
            self._add_to_tail(new_node)

    def contains(self, key: int) -> bool:
        return key in self._map

    def size(self) -> int:
        return len(self._map)

    def keys(self) -> List[int]:
        """返回所有 key 列表（按最近使用顺序）"""
        result = []
        curr = self._head.next
        while curr != self._tail:
            result.append(curr.key)
            curr = curr.next
        return result

    def __len__(self) -> int:
        return len(self._map)

    def __repr__(self) -> str:
        items = []
        curr = self._head.next
        while curr != self._tail:
            items.append(f"{curr.key}: {curr.value!r}")
            curr = curr.next
        return f"LRUCacheManual(capacity={self._capacity}, items=[{', '.join(items)}])"
