"""HTTP-level tests for POST /tasks and GET /tasks/{task_id}."""

from fastapi.testclient import TestClient


def test_create_task_returns_201_with_generated_id(client: TestClient) -> None:
    response = client.post("/tasks", json={"title": "Buy milk"})

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["title"] == "Buy milk"
    assert body["description"] is None
    assert "created_at" in body


def test_create_task_with_description(client: TestClient) -> None:
    response = client.post("/tasks", json={"title": "Buy milk", "description": "2% or whole"})

    assert response.status_code == 201
    assert response.json()["description"] == "2% or whole"


def test_create_task_strips_surrounding_whitespace(client: TestClient) -> None:
    response = client.post("/tasks", json={"title": "  Buy milk  "})

    assert response.status_code == 201
    assert response.json()["title"] == "Buy milk"


def test_create_task_missing_title_returns_422(client: TestClient) -> None:
    response = client.post("/tasks", json={"description": "no title here"})

    assert response.status_code == 422


def test_create_task_blank_title_returns_422(client: TestClient) -> None:
    response = client.post("/tasks", json={"title": "   "})

    assert response.status_code == 422


def test_create_task_overlong_title_returns_422(client: TestClient) -> None:
    response = client.post("/tasks", json={"title": "x" * 201})

    assert response.status_code == 422


def test_get_task_returns_saved_task(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "Buy milk", "description": "2% or whole"}).json()

    response = client.get(f"/tasks/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_task_returns_404(client: TestClient) -> None:
    response = client.get("/tasks/does-not-exist")

    assert response.status_code == 404
    assert response.json()["detail"]
