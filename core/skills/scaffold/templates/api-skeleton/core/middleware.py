"""Request identity and the one access-log line.

API_STANDARDS §10: accept an inbound X-Request-ID or generate one, echo it on every
response, and emit one log line per request carrying service_id, request_id, method,
path, status_code and duration_ms — from here, not from each route.
"""

import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"

# Read by the exception handlers so an error body carries the same id as the
# access log line for the same request.
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def current_request_id() -> str:
    return request_id_var.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_id: str) -> None:
        super().__init__(app)
        self.service_id = service_id

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        # Both, deliberately. request.state survives into the exception handlers,
        # which run outside this middleware; the ContextVar is what service and
        # repository code reads, where there is no Request object to hand around.
        request.state.request_id = request_id
        request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        finally:
            # Runs even when a handler raised, so a failed request is still logged
            # exactly once with its real duration.
            logger.info(
                "request",
                extra={
                    "service_id": self.service_id,
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
