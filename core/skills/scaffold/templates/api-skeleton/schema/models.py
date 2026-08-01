from typing import Any, Optional

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    detail: Optional[Any] = None
    request_id: Optional[str] = None
    timestamp: str
    errors: Optional[Any] = None
