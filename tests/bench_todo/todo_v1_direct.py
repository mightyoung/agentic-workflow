#!/usr/bin/env python3
"""Todo List - Direct Implementation (WITHOUT Skill)"""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime


@dataclass
class Todo:
    id: int
    title: str
    completed: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class TodoList:
    def __init__(self, filepath: str = "todos.json"):
        self.filepath = filepath
        self.todos: list[Todo] = []
        self.next_id = 1
        self.load()

    def load(self) -> None:
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                content = f.read()
                if content.strip():
                    data = json.loads(content)
                    self.todos = [Todo(**t) for t in data.get("todos", [])]
                    self.next_id = data.get("next_id", 1)

    def save(self) -> None:
        with open(self.filepath, "w") as f:
            json.dump(
                {"todos": [asdict(t) for t in self.todos], "next_id": self.next_id},
                f,
                indent=2,
            )

    def add(self, title: str) -> Todo:
        todo = Todo(id=self.next_id, title=title)
        self.todos.append(todo)
        self.next_id += 1
        self.save()
        return todo

    def delete(self, id: int) -> bool:
        for i, t in enumerate(self.todos):
            if t.id == id:
                self.todos.pop(i)
                self.save()
                return True
        return False

    def complete(self, id: int) -> Optional[Todo]:
        for t in self.todos:
            if t.id == id:
                t.completed = True
                self.save()
                return t
        return None

    def list_all(self) -> list[Todo]:
        return self.todos


def main():
    import sys

    todos = TodoList()

    if len(sys.argv) < 2:
        print("Usage: python todo.py <command> [args]")
        print("Commands: add <title>, delete <id>, complete <id>, list")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add" and len(sys.argv) >= 3:
        todo = todos.add(" ".join(sys.argv[2:]))
        print(f"Added: [{todo.id}] {todo.title}")

    elif cmd == "delete" and len(sys.argv) >= 3:
        id = int(sys.argv[2])
        if todos.delete(id):
            print(f"Deleted todo {id}")
        else:
            print(f"Todo {id} not found")

    elif cmd == "complete" and len(sys.argv) >= 3:
        id = int(sys.argv[2])
        todo = todos.complete(id)
        if todo:
            print(f"Completed: [{todo.id}] {todo.title}")
        else:
            print(f"Todo {id} not found")

    elif cmd == "list":
        for t in todos.list_all():
            status = "[x]" if t.completed else "[ ]"
            print(f"{status} [{t.id}] {t.title}")

    else:
        print("Unknown command")
        sys.exit(1)


if __name__ == "__main__":
    main()
