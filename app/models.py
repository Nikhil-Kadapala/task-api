"""Domain models for the task-api service.

These are plain Python types used between the service and repository layers.
They are deliberately independent of the HTTP/Pydantic schemas so the API
contract can evolve separately from the domain.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class Task:
    id: str
    title: str
    description: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
