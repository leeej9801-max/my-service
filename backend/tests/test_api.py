import json
import logging
from uuid import UUID

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from uuid_utils.compat import uuid7

from app.core.config import Settings
from app.routers.dependencies import current_user_id


async def test_health(client: AsyncClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    value = response.headers["x-request-id"]
    assert UUID(value).version == 4
    records = [r for r in caplog.records if r.name == "app.core.request_id"]
    assert records[0].request_id == value  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("path", "status", "code"),
    [
        ("/missing", 404, "http_error"),
        ("/api/v1/items/invalid", 401, "authentication_required"),
    ],
)
async def test_problem(client: AsyncClient, path: str, status: int, code: str) -> None:
    response = await client.get(path)
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json() == {
        "type": "about:blank",
        "status": status,
        "title": "Not Found" if status == 404 else "Unauthorized",
        "detail": "Not Found" if status == 404 else "Authentication is not configured.",
        "instance": path,
        "code": code,
    }


async def test_validation_problem(app: FastAPI, client: AsyncClient) -> None:
    async def user() -> UUID:
        return uuid7()

    app.dependency_overrides[current_user_id] = user
    response = await client.get("/api/v1/items/invalid")
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "validation_error"
    assert response.json()["errors"][0]["loc"] == ["path", "item_id"]


async def test_unexpected_problem(app: FastAPI) -> None:
    async def broken_user() -> UUID:
        raise RuntimeError("private diagnostic")

    app.dependency_overrides[current_user_id] = broken_user
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/items/invalid")
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "internal_error"
    assert "private diagnostic" not in response.text
    assert UUID(response.headers["x-request-id"]).version == 4


def test_required_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_uuid7() -> None:
    value = uuid7()
    assert isinstance(value, UUID)
    assert value.version == 7


@pytest.mark.parametrize("status", [400, 419, 499])
@pytest.mark.parametrize("detail", [{"reason": "한도 초과"}, ["invalid", "input"]])
async def test_structured_http_problem(
    app: FastAPI, client: AsyncClient, status: int, detail: dict[str, str] | list[str]
) -> None:
    @app.get("/test/http-error")
    async def fail() -> None:
        raise HTTPException(status, detail=detail, headers={"X-Error": "kept"})

    response = await client.get("/test/http-error")
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["x-error"] == "kept"
    body = response.json()
    assert body == {
        "type": "about:blank",
        "title": "Bad Request" if status == 400 else "HTTP Error",
        "status": status,
        "detail": json.dumps(detail, ensure_ascii=False),
        "instance": "/test/http-error",
        "code": "http_error",
    }
