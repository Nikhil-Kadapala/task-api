"""Unit tests for the service layer against the real in-memory repository."""

import pytest

from app.service import TaskNotFoundError, TaskService


def test_create_task_assigns_unique_ids(service: TaskService) -> None:
    first = service.create_task(title="one")
    second = service.create_task(title="two")

    assert first.id != second.id


def test_create_task_persists_fields(service: TaskService) -> None:
    task = service.create_task(title="one", description="desc")

    assert task.title == "one"
    assert task.description == "desc"
    assert task.priority == "medium"
    assert task.created_at is not None


def test_create_task_persists_priority(service: TaskService) -> None:
    task = service.create_task(title="one", priority="low")

    assert task.priority == "low"


def test_get_task_roundtrip(service: TaskService) -> None:
    created = service.create_task(title="one")

    fetched = service.get_task(created.id)

    assert fetched == created


def test_get_missing_task_raises_not_found(service: TaskService) -> None:
    with pytest.raises(TaskNotFoundError) as exc_info:
        service.get_task("missing-id")

    assert exc_info.value.task_id == "missing-id"
