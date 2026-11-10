import logging
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

request_id: ContextVar[str] = ContextVar("request_id", default="-")
logger = logging.getLogger(__name__)
original_factory = logging.getLogRecordFactory()


def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
    record = original_factory(*args, **kwargs)
    record.request_id = request_id.get()
    return record


logging.setLogRecordFactory(record_factory)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s request_id=%(request_id)s %(name)s %(message)s",
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        value = str(uuid4())
        token = request_id.set(value)
        request.state.request_id = value
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = value
            logger.info(
                "%s %s %s", request.method, request.url.path, response.status_code
            )
            return response
        finally:
            request_id.reset(token)
