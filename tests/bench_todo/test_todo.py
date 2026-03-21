"""Tests for TodoList"""

import pytest
import os
import tempfile
from todo_v1_direct import TodoList, Todo


@pytest.fixture
def temp_todo():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        filepath = f.name
    todos = TodoList(filepath)
    yield todos
    if os.path.exists(filepath):
        os.remove(filepath)


def test_add_todo(temp_todo):
    todo = temp_todo.add("Buy groceries")
    assert todo.id == 1
    assert todo.title == "Buy groceries"
    assert todo.completed is False


def test_delete_todo(temp_todo):
    todo = temp_todo.add("Test task")
    assert temp_todo.delete(todo.id) is True
    assert len(temp_todo.list_all()) == 0


def test_complete_todo(temp_todo):
    todo = temp_todo.add("Test task")
    result = temp_todo.complete(todo.id)
    assert result is not None
    assert result.completed is True


def test_list_todos(temp_todo):
    temp_todo.add("Task 1")
    temp_todo.add("Task 2")
    todos = temp_todo.list_all()
    assert len(todos) == 2


def test_persistence(temp_todo):
    temp_todo.add("Persistent task")
    new_todos = TodoList(temp_todo.filepath)
    assert len(new_todos.list_all()) == 1
    assert new_todos.list_all()[0].title == "Persistent task"
