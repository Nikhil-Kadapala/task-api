"""FastAPI application factory and HTTP routes for the task-api service."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.repository import InMemoryTaskRepository, TaskRepository
from app.schemas import ErrorResponse, TaskCreateRequest, TaskResponse
from app.service import TaskNotFoundError, TaskService


def create_app(repository: TaskRepository | None = None) -> FastAPI:
    app = FastAPI(title="task-api", version="0.1.0")

    service = TaskService(repository or InMemoryTaskRepository())
    app.state.task_service = service

    @app.exception_handler(TaskNotFoundError)
    async def task_not_found_handler(_request: Request, exc: TaskNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(detail=str(exc)).model_dump(mode="json"),
        )

    @app.post(
        "/tasks",
        response_model=TaskResponse,
        status_code=status.HTTP_201_CREATED,
        responses={422: {"model": ErrorResponse}},
    )
    async def create_task(payload: TaskCreateRequest) -> TaskResponse:
        task = service.create_task(title=payload.title, description=payload.description)
        return TaskResponse.model_validate(task)

    @app.get(
        "/tasks/{task_id}",
        response_model=TaskResponse,
        responses={404: {"model": ErrorResponse}},
    )
    async def get_task(task_id: str) -> TaskResponse:
        task = service.get_task(task_id)
        return TaskResponse.model_validate(task)

    return app


app = create_app()
