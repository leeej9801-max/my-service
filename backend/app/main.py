from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.exceptions import HTTPException

from app.core.config import Settings
from app.core.errors import http_error, unexpected_error, validation_error
from app.core.request_id import RequestIdMiddleware
from app.routers import health, items


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()  # type: ignore[call-arg]
    engine = create_async_engine(
        str(settings.database_url),
        pool_pre_ping=True,
        connect_args={"server_settings": {"timezone": "UTC"}},
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.state.sessions = async_sessionmaker(engine, expire_on_commit=False)
    app.add_middleware(RequestIdMiddleware)
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(Exception, unexpected_error)
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(items.router, prefix="/api/v1")
    return app
