"""The only place logging is configured.

configure_logging() is called once from the
app lifespan. No other module calls basicConfig, setLevel, or attaches a handler —
if it did, the LOG_LEVEL setting would stop meaning anything.
"""

import json
import logging
import sys
from typing import Any

# Attributes LogRecord always carries; anything else was passed as an extra= field
# and belongs in the structured output.
_STANDARD = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """One JSON object per line, so log search can filter on any field."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S") + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str, fmt: str, service_id: str) -> None:
    """Install one stdout handler at the configured level. Idempotent."""
    handler = logging.StreamHandler(sys.stdout)
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s  %(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Access logging is ours (see core/middleware.py). uvicorn's own duplicates it.
    logging.getLogger("uvicorn.access").disabled = True

    logging.getLogger(__name__).info(
        "logging configured", extra={"service_id": service_id, "log_level": level}
    )
