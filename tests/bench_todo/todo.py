#!/usr/bin/env python3
"""Todo List 应用 - JSON 文件持久化"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Todo:
    """Todo 数据结构"""
    id: int
    title: str
    completed: bool = False
    created_at: str = field(default_factory=lambda: __import__('datetime').datetime.now().isoformat())


class TodoList:
    """Todo 列表管理器 - 支持 JSON 文件持久化"""

    def __init__(self, filepath: str = "todos.json"):
        self.filepath = filepath
        self.todos: list[Todo] = []
        self.next_id = 1
        self.load()

    def load(self) -> None:
        """从 JSON 文件加载数据"""
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                content = f.read()
                if content.strip():
                    data = json.loads(content)
                    self.todos = [Todo(**t) for t in data.get("todos", [])]
                    self.next_id = data.get("next_id", 1)

    def save(self) -> None:
        """保存到 JSON 文件"""
        with open(self.filepath, "w") as f:
            json.dump(
                {"todos": [self._todo_to_dict(t) for t in self.todos], "next_id": self.next_id},
                f,
                indent=2,
            )

    def _todo_to_dict(self, todo: Todo) -> dict:
        """将 Todo 转换为字典"""
        return {"id": todo.id, "title": todo.title, "completed": todo.completed, "created_at": todo.created_at}

    def add(self, title: str) -> Todo:
        """添加 todo"""
        # 空标题处理
        title = title.strip()[:200] if title.strip() else "Untitled"
        todo = Todo(id=self.next_id, title=title)
        self.todos.append(todo)
        self.next_id += 1
        self.save()
        return todo

    def delete(self, id: int) -> bool:
        """删除 todo"""
        for i, t in enumerate(self.todos):
            if t.id == id:
                self.todos.pop(i)
                self.save()
                return True
        return False

    def complete(self, id: int) -> Optional[Todo]:
        """标记 todo 完成"""
        for t in self.todos:
            if t.id == id:
                t.completed = True
                self.save()
                return t
        return None

    def list_all(self) -> list[Todo]:
        """列出所有 todo"""
        return self.todos


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Todo List CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add 命令
    add_parser = subparsers.add_parser("add", help="添加 todo")
    add_parser.add_argument("title", nargs="*", help="todo 标题")
    add_parser.add_argument("-m", "--message", help="todo 标题 (alternative)")

    # delete 命令
    del_parser = subparsers.add_parser("delete", help="删除 todo")
    del_parser.add_argument("id", type=int, help="todo ID")

    # complete 命令
    complete_parser = subparsers.add_parser("complete", help="标记完成")
    complete_parser.add_argument("id", type=int, help="todo ID")

    # list 命令
    subparsers.add_parser("list", help="列出所有 todo")

    args = parser.parse_args()
    todos = TodoList()

    if args.command == "add":
        title = " ".join(args.title) if args.title else (args.message or "Untitled")
        todo = todos.add(title)
        print(f"Added: [{todo.id}] {todo.title}")

    elif args.command == "delete":
        if todos.delete(args.id):
            print(f"Deleted todo {args.id}")
        else:
            print(f"Todo {args.id} not found")

    elif args.command == "complete":
        todo = todos.complete(args.id)
        if todo:
            print(f"Completed: [{todo.id}] {todo.title}")
        else:
            print(f"Todo {args.id} not found")

    elif args.command == "list":
        for t in todos.list_all():
            status = "[x]" if t.completed else "[ ]"
            print(f"{status} [{t.id}] {t.title}")
