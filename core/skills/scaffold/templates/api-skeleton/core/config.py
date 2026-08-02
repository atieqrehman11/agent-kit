"""Every value this service reads, in one validated place.

docs/SERVICE_STRUCTURE_STANDARDS.md §5: configuration is loaded and validated once at
startup, into a typed settings object, and fails loudly on a missing key. Nothing else
in this repo calls os.getenv.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


class ConfigurationError(RuntimeError):
    """A required setting is missing or malformed. Raised at startup, never mid-request."""


class Settings(BaseSettings):
    """Field name maps to the env var of the same name, upper-cased (LOG_LEVEL, CATALOG…)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Identity — feeds GET /v1/info (API_STANDARDS §3) ──────────────────────
    service_id: str = "TPLVAR_SLUG"
    display_name: str = "TPLVAR_DISPLAY_NAME"
    description: str = "TPLVAR_DESCRIPTION"
    api_version: str = "v1"
    service_version: str = "0.1.0"
    owner: str = "TODO_SET_OWNER"
    support_email: str = "TODO_SET_SUPPORT_EMAIL"

    # ── Observability ─────────────────────────────────────────────────────────
    # LOG_LEVEL=DEBUG in the environment turns on debug logging. No code change,
    # no new build. Never call setLevel anywhere else.
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"

    # ── Boundary ──────────────────────────────────────────────────────────────
    # An allowlist. Empty means same-origin only — never "*" in a deployed
    # environment (API_STANDARDS §10). Set as JSON: CORS_ORIGINS='["https://…"]'
    cors_origins: list[str] = Field(default_factory=list)
    max_page_size: int = 500
    max_request_bytes: int = 10 * 1024 * 1024
    request_timeout_seconds: float = 30.0

    # ── Data sources — values come from app.yml ───────────────────────────────
    databricks_http_path: str = ""
    databricks_catalog: str = ""
    databricks_gold_schema: str = "gold"
    table_prefix: str = ""

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalise_level(cls, v: str) -> str:
        level = str(v).upper()
        if level not in _LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of {sorted(_LEVELS)}, got {v!r}")
        return level

    def require(self, *names: str) -> None:
        """Fail loudly at startup for settings this service cannot run without.

        Defaults above keep a local run working; deployment values do not have
        sensible defaults, and a blank one must stop the service rather than
        surface later as a confusing query error.
        """
        missing = [n for n in names if not getattr(self, n, None)]
        if missing:
            raise ConfigurationError(
                "Missing required configuration: " + ", ".join(sorted(n.upper() for n in missing))
            )


@lru_cache
def get_settings() -> Settings:
    """Cached so the whole app shares one instance. Use as a FastAPI dependency."""
    return Settings()
