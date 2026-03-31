#!/usr/bin/env python3
"""
Task Decomposer Tests - 任务分解器专项测试

测试任务分解的核心功能：
1. 任务ID唯一性
2. 优先级分配
3. 依赖检测
4. Owned files追踪
"""

import unittest
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from task_decomposer import decompose, DecomposedTask, auto_priority


class TestTaskDecomposer(unittest.TestCase):
    """任务分解器测试"""

    def test_decompose_returns_list(self):
        """测试分解返回列表"""
        prompt = "实现用户管理模块，包括用户注册、登录、信息修改三个功能"
        tasks = decompose(prompt)
        self.assertIsInstance(tasks, list)
        self.assertGreater(len(tasks), 0)

    def test_task_ids_are_unique(self):
        """测试任务ID唯一性"""
        prompt = "实现电商系统，包括用户模块、订单模块、支付模块"
        tasks = decompose(prompt)
        task_ids = [t.task_id for t in tasks]
        self.assertEqual(len(task_ids), len(set(task_ids)), "Task IDs should be unique")

    def test_task_ids_format(self):
        """测试任务ID格式"""
        prompt = "实现简单的计算器功能"
        tasks = decompose(prompt)
        for task in tasks:
            self.assertTrue(task.task_id.startswith("T"), f"Task ID {task.task_id} should start with T")

    def test_priorities_are_valid(self):
        """测试优先级有效性"""
        prompt = "实现用户认证模块：注册、登录、登出"
        tasks = decompose(prompt)
        valid_priorities = {"P0", "P1", "P2", "P3"}
        for task in tasks:
            self.assertIn(task.priority, valid_priorities, f"Priority {task.priority} should be valid")

    def test_dependencies_format(self):
        """测试依赖格式为列表"""
        prompt = "实现微服务架构：API网关、用户服务、订单服务"
        tasks = decompose(prompt)
        for task in tasks:
            self.assertIsInstance(task.dependencies, list)

    def test_owned_files_format(self):
        """测试拥有文件格式为列表"""
        prompt = "实现博客系统：文章管理、评论管理、用户管理"
        tasks = decompose(prompt)
        for task in tasks:
            self.assertIsInstance(task.owned_files, list)

    def test_status_default(self):
        """测试默认状态为backlog"""
        prompt = "实现一个简单功能"
        tasks = decompose(prompt)
        for task in tasks:
            self.assertEqual(task.status, "backlog")

    def test_to_dict(self):
        """测试任务序列化"""
        prompt = "实现加法功能"
        tasks = decompose(prompt)
        for task in tasks:
            d = task.to_dict()
            self.assertIn("task_id", d)
            self.assertIn("title", d)
            self.assertIn("priority", d)

    def test_multiple_tasks(self):
        """测试多任务场景"""
        prompt = "实现多个功能：功能A、功能B、功能C"
        tasks = decompose(prompt)
        # 应该分解为多个任务
        self.assertIsInstance(tasks, list)

    def test_auto_priority(self):
        """测试自动优先级分配"""
        task = DecomposedTask(task_id="T001", title="测试任务")
        priority = auto_priority(task, index=0, total=5)
        self.assertIn(priority, ["P0", "P1", "P2", "P3"])

    def test_empty_prompt(self):
        """测试空prompt处理"""
        tasks = decompose("")
        self.assertIsInstance(tasks, list)


class TestDecomposedTask(unittest.TestCase):
    """DecomposedTask数据类测试"""

    def test_create_task(self):
        """测试创建任务"""
        task = DecomposedTask(
            task_id="T001",
            title="测试任务",
            description="这是一个测试任务",
            priority="P1",
        )
        self.assertEqual(task.task_id, "T001")
        self.assertEqual(task.title, "测试任务")
        self.assertEqual(task.priority, "P1")
        self.assertEqual(task.status, "backlog")

    def test_task_with_dependencies(self):
        """测试带依赖的任务"""
        task = DecomposedTask(
            task_id="T002",
            title="任务2",
            dependencies=["T001"],
            owned_files=["file1.py", "file2.py"],
        )
        self.assertEqual(task.dependencies, ["T001"])
        self.assertEqual(task.owned_files, ["file1.py", "file2.py"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
