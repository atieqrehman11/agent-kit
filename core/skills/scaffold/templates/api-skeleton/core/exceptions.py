"""One exception hierarchy for the whole service.

Domain code raises, the boundary translates,
nothing in between builds an error body. Every exception here carries a stable
error_code from the platform error table.

Services and repositories raise these. They never raise HTTPException — that would
tie the logic to being called over HTTP, and this code should also be reachable from
a job, a consumer or an agent tool.
"""

from typing import Any, Optional


class AppError(Exception):
    """Base for every domain exception. Subclasses set the three class attributes."""

    error_code: str = "INTERNAL_ERROR"
    status_code: int = 500
    message: str = "An unexpected error occurred."

    def __init__(self, message: Optional[str] = None, detail: Optional[Any] = None) -> None:
        self.message = message or self.message
        self.detail = detail
        super().__init__(self.message)


class InvalidRequestError(AppError):
    error_code = "INVALID_REQUEST"
    status_code = 400
    message = "The request was malformed."


class UnauthenticatedError(AppError):
    error_code = "UNAUTHENTICATED"
    status_code = 401
    message = "Authentication is required."


class ForbiddenError(AppError):
    error_code = "FORBIDDEN"
    status_code = 403
    message = "You do not have access to this resource."


class ResourceNotFoundError(AppError):
    error_code = "RESOURCE_NOT_FOUND"
    status_code = 404
    message = "The requested resource was not found."


class ResourceConflictError(AppError):
    error_code = "RESOURCE_CONFLICT"
    status_code = 409
    message = "The resource is in a conflicting state."


class ResourceNotReadyError(AppError):
    error_code = "RESOURCE_NOT_READY"
    status_code = 409
    message = "The resource is not ready yet."


class ValidationFailedError(AppError):
    error_code = "VALIDATION_ERROR"
    status_code = 422
    message = "The request failed validation."


class RateLimitedError(AppError):
    error_code = "RATE_LIMITED"
    status_code = 429
    message = "Too many requests."


class UpstreamBadResponseError(AppError):
    error_code = "UPSTREAM_BAD_RESPONSE"
    status_code = 502
    message = "An upstream service returned an unusable response."


class ServiceUnavailableError(AppError):
    error_code = "SERVICE_UNAVAILABLE"
    status_code = 503
    message = "A required dependency is unavailable."


class UpstreamTimeoutError(AppError):
    error_code = "UPSTREAM_TIMEOUT"
    status_code = 504
    message = "An upstream service timed out."


# TODO: add service-specific exceptions here. Prefix their error_code with this
# service's id, upper-cased with underscores — so a caller
# can tell a platform error from one of ours. e.g. for service_id "kpi-reporting":
#
# class ReportExpiredError(AppError):
#     error_code = "KPI_REPORTING_REPORT_EXPIRED"
#     status_code = 409
#     message = "The report has expired and must be regenerated."
