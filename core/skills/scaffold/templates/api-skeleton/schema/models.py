"""Every model this service exposes, in one place.

docs/SERVICE_STRUCTURE_STANDARDS.md §2: models live under schema/, defined once. A
request model declared inline in a router is a second source of truth for the same
contract — put it here instead.
"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """API_STANDARDS §7. Built only by core/handlers.py — never by a route."""

    error_code: str
    message: str
    detail: Optional[Any] = None
    request_id: Optional[str] = None
    timestamp: str
    errors: Optional[Any] = None


class Page(BaseModel, Generic[T]):
    """API_STANDARDS §8 pagination envelope. Every list endpoint returns this."""

    items: list[T]
    limit: int
    offset: int
    total: int
    has_more: bool


class HealthResponse(BaseModel):
    """API_STANDARDS §4."""

    status: str = Field(description="OK | DEGRADED | ERROR")
    service_id: str
    api_version: str
    service_version: str
    timestamp: str
    dependencies: dict[str, str] = Field(default_factory=dict)


class InfoResponse(BaseModel):
    """API_STANDARDS §3."""

    service_id: str
    display_name: str
    description: str
    api_version: str
    service_version: str
    status: str
    capabilities: list[str]
    icon: str
    owner: str
    support_email: str
    openapi_url: str


# TODO: add this service's domain models below — request, response and domain shapes.
# Keep persistence models out of responses; map between them in the service layer.
