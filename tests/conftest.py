"""Shared fixtures. Every test gets a fresh app + repository, so no state
can leak between tests and the suite is deterministic in any order."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repository import InMemoryTaskRepository
from app.service import TaskService


@pytest.fixture
def repository() -> InMemoryTaskRepository:
    return InMemoryTaskRepository()


@pytest.fixture
def service(repository: InMemoryTaskRepository) -> TaskService:
    return TaskService(repository)


@pytest.fixture
def client(repository: InMemoryTaskRepository) -> TestClient:
    return TestClient(create_app(repository))
