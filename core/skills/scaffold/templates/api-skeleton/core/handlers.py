"""The one place an error response is built.

docs/SERVICE_STRUCTURE_STANDARDS.md §3. No route builds an error body by hand; if you
find yourself returning a JSONResponse with an error_code in it, raise an AppError
instead and add a case here.

Four handlers, in the order they matter:
  AppError                 every domain failure — maps via its own error_code/status
  RequestValidationError   framework 422s, normalized off {"detail": ...}
  HTTPException            anything raised by the framework or a dependency
  Exception                the catch-all: logs with a stack trace, leaks nothing
"""

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.exceptions import AppError
from core.middleware import current_request_id
from schema.models import ErrorResponse

logger = logging.getLogger(__name__)

# API_STANDARDS §7 — the code returned for a framework-raised status.
_STATUS_CODES = {
    400: "INVALID_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "RESOURCE_NOT_FOUND",
    405: "INVALID_REQUEST",
    409: "RESOURCE_CONFLICT",
    413: "INVALID_REQUEST",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    503: "SERVICE_UNAVAILABLE",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _response(
    request: Request, status_code: int, error_code: str, message: str, detail=None, errors=None
):
    # request.state is set by RequestContextMiddleware and survives into here, which
    # runs outside it. The ContextVar is the fallback for a failure raised before
    # the middleware got to set it.
    request_id = getattr(request.state, "request_id", None) or current_request_id() or None
    body = ErrorResponse(
        error_code=error_code,
        message=message,
        detail=detail,
        request_id=request_id,
        timestamp=_now(),
        errors=errors,
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(),
        headers={"X-Request-ID": request_id} if request_id else None,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        # Expected failures: one line, no stack trace. WARNING for 5xx because it
        # is a dependency problem we already understand, not a crash.
        logger.log(
            logging.WARNING if exc.status_code >= 500 else logging.INFO,
            "handled error",
            extra={"error_code": exc.error_code, "path": request.url.path},
        )
        return _response(request, exc.status_code, exc.error_code, exc.message, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        return _response(
            request,
            422,
            "VALIDATION_ERROR",
            "The request failed validation.",
            errors=[
                {"field": ".".join(str(p) for p in e.get("loc", [])), "message": e.get("msg")}
                for e in exc.errors()
            ],
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        code = _STATUS_CODES.get(exc.status_code, "INTERNAL_ERROR")
        return _response(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        # The catch-all. Full detail to the log, nothing internal to the caller —
        # no stack trace, no SQL, no upstream URL, no prompt.
        logger.exception(
            "unhandled error",
            extra={"method": request.method, "path": request.url.path},
        )
        return _response(request, 500, "INTERNAL_ERROR", "An unexpected error occurred.")
