"""Service entry point. Wiring only — no business logic, no data access.

Startup order matters: configuration is validated first, then logging is configured
from it, then everything else. A failure in either must stop the service rather than
let it serve traffic in an unknown state.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.handlers import register_exception_handlers
from core.logging_setup import configure_logging
from core.middleware import RequestContextMiddleware
from routers import domain, platform

settings = get_settings()
configure_logging(settings.log_level, settings.log_format, settings.service_id)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: list the settings this service genuinely cannot run without, so a
    # misconfigured deploy fails here instead of on the first request. e.g.
    #   settings.require("databricks_http_path", "databricks_catalog")
    settings.require()

    if not settings.cors_origins:
        # Loud, because an empty allowlist is right locally and wrong in production.
        logger.warning("CORS_ORIGINS is empty — cross-origin requests will be refused")

    logger.info("startup", extra={"service_version": settings.service_version})
    yield
    logger.info("shutdown")


app = FastAPI(
    title=f"{settings.display_name} API",
    version=settings.service_version,
    lifespan=lifespan,
)

# An allowlist from configuration. Never ["*"] — API_STANDARDS §10.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(RequestContextMiddleware, service_id=settings.service_id)

register_exception_handlers(app)

app.include_router(platform.router)
app.include_router(domain.router)
