"""Pydantic request/response schemas defining the HTTP API contract."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

MAX_TITLE_LENGTH = 200


class TaskCreateRequest(BaseModel):
    title: str
    description: str | None = None

    @field_validator("title")
    @classmethod
    def title_must_be_non_blank_and_bounded(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("title must not be blank")
        if len(stripped) > MAX_TITLE_LENGTH:
            raise ValueError(f"title must be at most {MAX_TITLE_LENGTH} characters")
        return stripped


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None
    created_at: datetime


class ErrorResponse(BaseModel):
    detail: str
