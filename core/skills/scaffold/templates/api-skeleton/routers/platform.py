from datetime import datetime, timezone

from fastapi import APIRouter

from config import API_VERSION, DESCRIPTION, DISPLAY_NAME, SERVICE_ID, SERVICE_VERSION

router = APIRouter(tags=["Platform"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@router.get("/v1/health")
async def health():
    """
    Service readiness. Returns OK when the service can handle normal traffic.
    Add real dependency checks (warehouse ping, model endpoint ping) in the
    dependencies dict. See docs/API_STANDARDS.md §4.
    """
    dependencies: dict = {}  # TODO: e.g. {"delta_lake": "OK", "model_endpoint": "OK"}
    return {
        "status": "OK",
        "service_id": SERVICE_ID,
        "api_version": API_VERSION,
        "service_version": SERVICE_VERSION,
        "timestamp": _now(),
        "dependencies": dependencies,
    }


@router.get("/v1/info")
async def info():
    """
    Service identity used by the platform shell for service discovery.
    Update capabilities to match what this service actually exposes.
    See docs/API_STANDARDS.md §3.
    """
    return {
        "service_id": SERVICE_ID,
        "display_name": DISPLAY_NAME,
        "description": DESCRIPTION,
        "api_version": API_VERSION,
        "service_version": SERVICE_VERSION,
        "status": "ACTIVE",
        # TODO: update capabilities — allowed values:
        # ASYNC_JOBS | REPORTING | FILE_DOWNLOADS | DASHBOARD_DATA | CONVERSATION_CONTEXT
        "capabilities": ["DASHBOARD_DATA", "CONVERSATION_CONTEXT"],
        "icon": "chart-line",             # TODO: update icon slug
        "owner": "TODO_SET_OWNER",        # e.g. "Analytics"
        "support_email": "TODO_SET_SUPPORT_EMAIL",
        "openapi_url": "/openapi.json",
    }


@router.get("/")
async def root():
    """Root — links to interactive docs."""
    return {
        "service_id": SERVICE_ID,
        "message": f"{DISPLAY_NAME} API",
        "docs": "/docs",
        "health": "/v1/health",
        "openapi": "/openapi.json",
    }
