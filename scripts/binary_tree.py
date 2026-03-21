#!/usr/bin/env python3
"""
二叉树遍历工具

提供三种经典二叉树遍历实现:
1. 前序遍历 (Pre-order): 根-左-右
2. 中序遍历 (In-order): 左-根-右
3. 后序遍历 (Post-order): 左-右-根

实现方式: 递归实现 (简洁直观)
"""

from typing import Optional, List


class TreeNode:
    """
    二叉树节点

    Attributes:
        val: 节点值
        left: 左子节点
        right: 右子节点
    """

    def __init__(
        self,
        val: int = 0,
        left: Optional["TreeNode"] = None,
        right: Optional["TreeNode"] = None,
    ) -> None:
        self.val = val
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        return f"TreeNode({self.val})"


def preorder_traversal(root: Optional[TreeNode]) -> List[int]:
    """
    前序遍历 (Pre-order): 根-左-右

    遍历顺序:
    1. 访问当前节点 (根)
    2. 递归遍历左子树
    3. 递归遍历右子树

    Args:
        root: 二叉树根节点

    Returns:
        前序遍历结果列表

    示例:
        >>> root = TreeNode(1, TreeNode(2), TreeNode(3))
        >>> preorder_traversal(root)
        [1, 2, 3]
    """
    result: List[int] = []

    def traverse(node: Optional[TreeNode]) -> None:
        if node is None:
            return
        result.append(node.val)
        traverse(node.left)
        traverse(node.right)

    traverse(root)
    return result


def inorder_traversal(root: Optional[TreeNode]) -> List[int]:
    """
    中序遍历 (In-order): 左-根-右

    遍历顺序:
    1. 递归遍历左子树
    2. 访问当前节点 (根)
    3. 递归遍历右子树

    Args:
        root: 二叉树根节点

    Returns:
        中序遍历结果列表

    示例:
        >>> root = TreeNode(1, TreeNode(2), TreeNode(3))
        >>> inorder_traversal(root)
        [2, 1, 3]
    """
    result: List[int] = []

    def traverse(node: Optional[TreeNode]) -> None:
        if node is None:
            return
        traverse(node.left)
        result.append(node.val)
        traverse(node.right)

    traverse(root)
    return result


def postorder_traversal(root: Optional[TreeNode]) -> List[int]:
    """
    后序遍历 (Post-order): 左-右-根

    遍历顺序:
    1. 递归遍历左子树
    2. 递归遍历右子树
    3. 访问当前节点 (根)

    Args:
        root: 二叉树根节点

    Returns:
        后序遍历结果列表

    示例:
        >>> root = TreeNode(1, TreeNode(2), TreeNode(3))
        >>> postorder_traversal(root)
        [2, 3, 1]
    """
    result: List[int] = []

    def traverse(node: Optional[TreeNode]) -> None:
        if node is None:
            return
        traverse(node.left)
        traverse(node.right)
        result.append(node.val)

    traverse(root)
    return result
