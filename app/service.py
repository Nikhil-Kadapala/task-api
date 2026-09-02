"""Service layer: business logic between the HTTP routes and the repository."""

import uuid

from app.models import Task, TaskPriority
from app.repository import TaskRepository


class TaskNotFoundError(Exception):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"task not found: {task_id}")
        self.task_id = task_id


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def create_task(
        self,
        title: str,
        description: str | None = None,
        priority: TaskPriority = "medium",
    ) -> Task:
        task = Task(id=uuid.uuid4().hex, title=title, description=description, priority=priority)
        return self._repository.add(task)

    def get_task(self, task_id: str) -> Task:
        task = self._repository.get(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task
