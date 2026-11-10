import json
import logging
from http import HTTPStatus

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.request_id import request_id


class Problem(HTTPException):
    def __init__(self, status_code: int, detail: str, code: str) -> None:
        super().__init__(status_code, detail)
        self.code = code


async def http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    try:
        title = HTTPStatus(exc.status_code).phrase
    except ValueError:
        title = "HTTP Error"
    detail = exc.detail
    if not isinstance(detail, str):
        detail = json.dumps(jsonable_encoder(detail), ensure_ascii=False)
    return JSONResponse(
        status_code=exc.status_code,
        media_type="application/problem+json",
        headers=exc.headers,
        content={
            "type": "about:blank",
            "status": exc.status_code,
            "title": title,
            "detail": detail,
            "instance": request.url.path,
            "code": exc.code if isinstance(exc, Problem) else "http_error",
        },
    )


async def validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    return JSONResponse(
        status_code=422,
        media_type="application/problem+json",
        content={
            "type": "about:blank",
            "status": 422,
            "title": "Unprocessable Content",
            "detail": "Request validation failed.",
            "instance": request.url.path,
            "code": "validation_error",
            "errors": jsonable_encoder(exc.errors()),
        },
    )


async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    value = request.state.request_id
    token = request_id.set(value)
    try:
        logging.getLogger(__name__).error("Unhandled request error", exc_info=exc)
    finally:
        request_id.reset(token)
    return JSONResponse(
        status_code=500,
        media_type="application/problem+json",
        headers={"X-Request-ID": value},
        content={
            "type": "about:blank",
            "status": 500,
            "title": "Internal Server Error",
            "detail": "An unexpected error occurred.",
            "instance": request.url.path,
            "code": "internal_error",
        },
    )
