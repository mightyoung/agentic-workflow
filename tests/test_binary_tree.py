#!/usr/bin/env python3
"""
二叉树遍历工具测试 - TDD 方式验证实现

测试覆盖:
1. TreeNode 树节点构建
2. 前序遍历 (Pre-order): 根-左-右
3. 中序遍历 (In-order): 左-根-右
4. 后序遍历 (Post-order): 左-右-根
5. 空树边界情况
6. 单节点树
7. 斜树 (完全左偏/右偏)
8. 递归实现
9. 迭代实现 (栈)
"""

import os
import sys
import unittest
from typing import Optional, List

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "utils"))
from binary_tree import TreeNode, preorder_traversal, inorder_traversal, postorder_traversal


def build_tree(values: list) -> Optional[TreeNode]:
    """辅助函数: 从层序数组构建二叉树"""
    if not values or values[0] is None:
        return None
    root = TreeNode(values[0])
    queue = [root]
    i = 1
    while queue and i < len(values):
        node = queue.pop(0)
        # 左子节点
        if i < len(values) and values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1
        # 右子节点
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1
    return root


class TestTreeNode(unittest.TestCase):
    """TreeNode 节点测试"""

    def test_node_creation(self):
        node = TreeNode(1)
        self.assertEqual(node.val, 1)
        self.assertIsNone(node.left)
        self.assertIsNone(node.right)

    def test_node_with_children(self):
        left = TreeNode(2)
        right = TreeNode(3)
        root = TreeNode(1, left, right)
        self.assertEqual(root.val, 1)
        self.assertEqual(root.left.val, 2)
        self.assertEqual(root.right.val, 3)


class TestPreorderTraversal(unittest.TestCase):
    """前序遍历测试 (根-左-右)"""

    def test_standard_tree(self):
        #       1
        #      / \
        #     2   3
        #    / \
        #   4   5
        root = TreeNode(1)
        root.left = TreeNode(2, TreeNode(4), TreeNode(5))
        root.right = TreeNode(3)
        self.assertEqual(preorder_traversal(root), [1, 2, 4, 5, 3])

    def test_empty_tree(self):
        self.assertEqual(preorder_traversal(None), [])

    def test_single_node(self):
        root = TreeNode(42)
        self.assertEqual(preorder_traversal(root), [42])

    def test_left_skewed_tree(self):
        # 1
        #  \
        #   2
        #    \
        #     3
        root = TreeNode(1)
        root.right = TreeNode(2)
        root.right.right = TreeNode(3)
        self.assertEqual(preorder_traversal(root), [1, 2, 3])

    def test_right_skewed_tree(self):
        #    3
        #   /
        #  2
        # /
        #1
        root = TreeNode(3)
        root.left = TreeNode(2)
        root.left.left = TreeNode(1)
        self.assertEqual(preorder_traversal(root), [3, 2, 1])


class TestInorderTraversal(unittest.TestCase):
    """中序遍历测试 (左-根-右)"""

    def test_standard_tree(self):
        #       1
        #      / \
        #     2   3
        #    / \
        #   4   5
        root = TreeNode(1)
        root.left = TreeNode(2, TreeNode(4), TreeNode(5))
        root.right = TreeNode(3)
        self.assertEqual(inorder_traversal(root), [4, 2, 5, 1, 3])

    def test_empty_tree(self):
        self.assertEqual(inorder_traversal(None), [])

    def test_single_node(self):
        root = TreeNode(42)
        self.assertEqual(inorder_traversal(root), [42])

    def test_left_skewed_tree(self):
        # 1
        #  \
        #   2
        #    \
        #     3
        root = TreeNode(1)
        root.right = TreeNode(2)
        root.right.right = TreeNode(3)
        self.assertEqual(inorder_traversal(root), [1, 2, 3])

    def test_right_skewed_tree(self):
        #    3
        #   /
        #  2
        # /
        #1
        root = TreeNode(3)
        root.left = TreeNode(2)
        root.left.left = TreeNode(1)
        self.assertEqual(inorder_traversal(root), [1, 2, 3])


class TestPostorderTraversal(unittest.TestCase):
    """后序遍历测试 (左-右-根)"""

    def test_standard_tree(self):
        #       1
        #      / \
        #     2   3
        #    / \
        #   4   5
        root = TreeNode(1)
        root.left = TreeNode(2, TreeNode(4), TreeNode(5))
        root.right = TreeNode(3)
        self.assertEqual(postorder_traversal(root), [4, 5, 2, 3, 1])

    def test_empty_tree(self):
        self.assertEqual(postorder_traversal(None), [])

    def test_single_node(self):
        root = TreeNode(42)
        self.assertEqual(postorder_traversal(root), [42])

    def test_left_skewed_tree(self):
        # 1
        #  \
        #   2
        #    \
        #     3
        root = TreeNode(1)
        root.right = TreeNode(2)
        root.right.right = TreeNode(3)
        self.assertEqual(postorder_traversal(root), [3, 2, 1])

    def test_right_skewed_tree(self):
        #    3
        #   /
        #  2
        # /
        #1
        root = TreeNode(3)
        root.left = TreeNode(2)
        root.left.left = TreeNode(1)
        self.assertEqual(postorder_traversal(root), [1, 2, 3])


class TestTraversalComprehensive(unittest.TestCase):
    """综合遍历测试"""

    def test_complete_binary_tree(self):
        #         1
        #       /   \
        #      2     3
        #     / \   / \
        #    4   5 6   7
        root = build_tree([1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(preorder_traversal(root), [1, 2, 4, 5, 3, 6, 7])
        self.assertEqual(inorder_traversal(root), [4, 2, 5, 1, 6, 3, 7])
        self.assertEqual(postorder_traversal(root), [4, 5, 2, 6, 7, 3, 1])

    def test_large_tree(self):
        # 构建一个较大的平衡树
        #          1
        #       /     \
        #      2        3
        #     /  \    /  \
        #    4    5  6     7
        #   / \  /
        #  8   9 10
        root = build_tree([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, None, None, None, None, None])
        self.assertEqual(preorder_traversal(root), [1, 2, 4, 8, 9, 5, 10, 3, 6, 7])
        self.assertEqual(inorder_traversal(root), [8, 4, 9, 2, 10, 5, 1, 6, 3, 7])
        self.assertEqual(postorder_traversal(root), [8, 9, 4, 10, 5, 2, 6, 7, 3, 1])


if __name__ == "__main__":
    unittest.main()
