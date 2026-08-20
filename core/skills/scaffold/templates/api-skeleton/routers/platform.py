"""The two endpoints every use case API must expose."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends

from core.config import Settings, get_settings
from schema.models import HealthResponse, InfoResponse

router = APIRouter(tags=["Platform"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@router.get("/v1/health", response_model=HealthResponse)
async def health(settings: SettingsDep) -> HealthResponse:
    """
    Service readiness. Returns OK when the service can handle normal traffic.

    Add real dependency checks (warehouse ping, model endpoint ping) to the
    dependencies dict. Each check belongs in its repository — this endpoint calls
    them, it does not implement them.
    """
    dependencies: dict[str, str] = {}  # TODO: e.g. {"delta_lake": "OK"}
    return HealthResponse(
        status="OK",
        service_id=settings.service_id,
        api_version=settings.api_version,
        service_version=settings.service_version,
        timestamp=_now(),
        dependencies=dependencies,
    )


@router.get("/v1/info", response_model=InfoResponse)
async def info(settings: SettingsDep) -> InfoResponse:
    """
    Service identity used by the platform shell for service discovery.
    Update capabilities to match what this service actually exposes.
    """
    return InfoResponse(
        service_id=settings.service_id,
        display_name=settings.display_name,
        description=settings.description,
        api_version=settings.api_version,
        service_version=settings.service_version,
        status="ACTIVE",
        # TODO: update capabilities — allowed values:
        # ASYNC_JOBS | REPORTING | FILE_DOWNLOADS | DASHBOARD_DATA | CONVERSATION_CONTEXT
        capabilities=["DASHBOARD_DATA", "CONVERSATION_CONTEXT"],
        icon="chart-line",  # TODO: update icon slug
        owner=settings.owner,
        support_email=settings.support_email,
        openapi_url="/openapi.json",
    )


@router.get("/")
async def root(settings: SettingsDep) -> dict:
    """Root — links to interactive docs."""
    return {
        "service_id": settings.service_id,
        "message": f"{settings.display_name} API",
        "docs": "/docs",
        "health": "/v1/health",
        "openapi": "/openapi.json",
    }
