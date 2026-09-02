"""Repository layer: persistence for Task domain objects.

The baseline uses a process-local in-memory store behind a small interface so
a future PR can swap in SQLite (or another store) without touching the service
layer. Tests construct a fresh repository per test, so state never leaks.
"""

import threading
from typing import Protocol

from app.models import Task


class TaskRepository(Protocol):
    def add(self, task: Task) -> Task: ...

    def get(self, task_id: str) -> Task | None: ...

    def reset(self) -> None: ...


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()

    def add(self, task: Task) -> Task:
        with self._lock:
            self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> Task | None:
        with self._lock:
            return self._tasks.get(task_id)

    def reset(self) -> None:
        with self._lock:
            self._tasks.clear()
