# task-api

A deliberately small FastAPI task-management service. It exists as the target
repository for a review-skill benchmark: large enough to have real layers
(route → schema → service → repository), small enough that a reviewer can hold
the whole change map in their head.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
uv sync
```

## Run

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Interactive docs are at `http://localhost:8000/docs`.

With Docker:

```bash
docker build -t task-api .
docker run --rm -p 8000:8000 task-api
```

## Test, lint, type check

These are the same commands CI runs:

```bash
uv run pytest                  # test suite (deterministic; fresh state per test)
uv run ruff check .            # lint
uv run ruff format --check .   # format check
uv run mypy app tests          # type check
```

## API

### `POST /tasks`

Creates a task.

- Request body: `{"title": str, "description": str | null, "priority": "low" | "medium" | "high"}`
- `title` is required, must be non-blank after trimming, and at most 200
  characters (surrounding whitespace is stripped).
- `priority` is optional and defaults to `"medium"`. Invalid values return `422`.
- Returns `201 Created` with `{"id", "title", "description", "priority", "created_at"}`.
- Invalid payloads return `422 Unprocessable Entity`.

### `GET /tasks/{task_id}`

Returns the saved task with the same shape as the create response, or
`404 Not Found` with `{"detail": "..."}` for unknown IDs.

## Architecture

Intentionally small, one file per layer:

```text
HTTP route (app/main.py)
  -> request schema (app/schemas.py)
  -> task service (app/service.py)
  -> repository (app/repository.py)
  -> stored task (app/models.py)
  -> response schema (app/schemas.py)
```

Persistence is an in-memory store behind a `TaskRepository` protocol, so a
future change can swap in SQLite without touching the service layer. Tests
build a fresh app and repository per test (see `tests/conftest.py`), so the
suite is deterministic and order-independent.
