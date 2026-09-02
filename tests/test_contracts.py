"""Contract tests: pin the OpenAPI surface so accidental API changes fail loudly."""

from fastapi.testclient import TestClient


def test_openapi_exposes_task_endpoints(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()

    assert set(spec["paths"].keys()) == {"/tasks", "/tasks/{task_id}"}
    assert "post" in spec["paths"]["/tasks"]
    assert "get" in spec["paths"]["/tasks/{task_id}"]


def test_create_task_contract(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    post = spec["paths"]["/tasks"]["post"]

    assert "201" in post["responses"]
    request_schema = spec["components"]["schemas"]["TaskCreateRequest"]
    assert "title" in request_schema["required"]
    assert set(request_schema["properties"].keys()) == {"title", "description"}


def test_task_response_contract(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    response_schema = spec["components"]["schemas"]["TaskResponse"]

    assert set(response_schema["properties"].keys()) == {
        "id",
        "title",
        "description",
        "created_at",
    }
    assert set(response_schema["required"]) == {"id", "title", "description", "created_at"}


def test_get_task_documents_404(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    get = spec["paths"]["/tasks/{task_id}"]["get"]

    assert "404" in get["responses"]
