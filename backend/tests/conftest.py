import asyncio
import os
import sys
from collections.abc import AsyncIterator
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import PostgresDsn
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.main import create_app
from app.routers.dependencies import current_user_id

USER_A = UUID("00000000-0000-4000-8000-000000000001")


@pytest.fixture
async def app() -> AsyncIterator[FastAPI]:
    # Health/error tests never connect; production settings have no default DSN.
    settings = Settings(
        database_url=PostgresDsn("postgresql+asyncpg://unused@127.0.0.1/unused")
    )
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a disposable PostgreSQL database.")
    Settings(database_url=PostgresDsn(url))
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "alembic",
        "upgrade",
        "head",
        env={**os.environ, "DATABASE_URL": url},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    output, _ = await process.communicate()
    assert process.returncode == 0, output.decode()
    return url


@pytest.fixture
async def db_app(database_url: str) -> AsyncIterator[FastAPI]:
    application = create_app(Settings(database_url=PostgresDsn(database_url)))
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture
async def db_session(db_app: FastAPI) -> AsyncIterator[AsyncSession]:
    async with db_app.state.sessions() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.execute(text("TRUNCATE TABLE item"))
            await session.commit()


@pytest.fixture
async def db_client(
    db_app: FastAPI, db_session: AsyncSession
) -> AsyncIterator[AsyncClient]:
    async def user_a() -> UUID:
        return USER_A

    db_app.dependency_overrides[current_user_id] = user_a
    try:
        async with AsyncClient(
            transport=ASGITransport(app=db_app, raise_app_exceptions=False),
            base_url="http://test",
        ) as http:
            yield http
    finally:
        db_app.dependency_overrides.clear()
