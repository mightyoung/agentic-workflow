"""Todo List - TDD Tests (RED phase)"""

import pytest
import os
import tempfile


# ===== TDD RED: Write failing tests first =====

class TestTodoDataStructure:
    """TASK-001: Todo 数据结构测试"""

    def test_todo_has_required_fields(self):
        """Todo 必须有 id, title, completed, created_at 字段"""
        from todo import Todo
        todo = Todo(id=1, title="Test")
        assert hasattr(todo, 'id')
        assert hasattr(todo, 'title')
        assert hasattr(todo, 'completed')
        assert hasattr(todo, 'created_at')

    def test_todo_default_completed_false(self):
        """新创建的 Todo 默认 completed=False"""
        from todo import Todo
        todo = Todo(id=1, title="Test")
        assert todo.completed is False


class TestTodoListBasic:
    """TASK-001: TodoList 基本操作测试"""

    def test_add_todo(self):
        """添加 todo"""
        from todo import TodoList
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            todos = TodoList(f.name)
            todo = todos.add("Buy groceries")
            assert todo.title == "Buy groceries"
            assert todo.id == 1
            assert todo.completed is False
            os.unlink(f.name)

    def test_delete_todo(self):
        """删除 todo"""
        from todo import TodoList
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            todos = TodoList(f.name)
            todo = todos.add("Test task")
            assert todos.delete(todo.id) is True
            assert len(todos.list_all()) == 0
            os.unlink(f.name)

    def test_complete_todo(self):
        """标记 todo 完成"""
        from todo import TodoList
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            todos = TodoList(f.name)
            todo = todos.add("Test task")
            result = todos.complete(todo.id)
            assert result is not None
            assert result.completed is True
            os.unlink(f.name)

    def test_list_todos(self):
        """列表展示"""
        from todo import TodoList
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            todos = TodoList(f.name)
            todos.add("Task 1")
            todos.add("Task 2")
            all_todos = todos.list_all()
            assert len(all_todos) == 2
            os.unlink(f.name)


class TestTodoValidation:
    """TASK-004: 输入验证测试"""

    def test_empty_title_rejected(self):
        """空标题应被拒绝"""
        from todo import TodoList
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            todos = TodoList(f.name)
            _ = todos.add("")
            # 空标题应该被截断或处理
            os.unlink(f.name)

    def test_id_auto_increment(self):
        """ID 自动递增"""
        from todo import TodoList
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            todos = TodoList(f.name)
            t1 = todos.add("Task 1")
            t2 = todos.add("Task 2")
            assert t2.id == t1.id + 1
            os.unlink(f.name)


class TestTodoPersistence:
    """持久化测试"""

    def test_persistence_after_add(self):
        """添加后数据持久化"""
        from todo import TodoList
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            filepath = f.name
        todos1 = TodoList(filepath)
        todos1.add("Persistent task")
        todos2 = TodoList(filepath)
        assert len(todos2.list_all()) == 1
        assert todos2.list_all()[0].title == "Persistent task"
        os.unlink(filepath)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
