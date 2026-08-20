"""Domain endpoints — the boundary layer.

A router parses, validates, delegates and serialises. It holds no business logic, no
data access and no LLM calls, and it never builds an error body — it validates,
delegates and translates, nothing else.

The commented example below is the shape to copy: router → service → repository, with
the service raising a domain exception the handler layer already knows how to render.

Rules:
  - Paths:     /v1/{plural-resource}  (lowercase, hyphenated)
  - Params:    snake_case query and path parameter names; never a bare {id}
  - Responses: objects, not bare arrays
  - Lists:     Page[...] from schema/models.py, and limit is capped at max_page_size
  - Errors:    raise from core/exceptions.py — never return an error body from here
  - No POST /v1/chat/message — chat belongs in the conversational API service
"""

from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["Domain"])

# TODO: implement this service's domain endpoints. Delete the example once you have one.
#
# from typing import Annotated
#
# from fastapi import Depends, Query
#
# from schema.models import Page
# from services.record_service import RecordService, get_record_service
#
#
# @router.get("/records", response_model=Page[Record])
# async def list_records(
#     service: Annotated[RecordService, Depends(get_record_service)],
#     limit: int = Query(100, ge=1, le=500),   # le must match settings.max_page_size
#     offset: int = Query(0, ge=0),
# ) -> Page[Record]:
#     """List records. Business logic lives in the service; this only shapes the call."""
#     return await service.list_records(limit=limit, offset=offset)
#
#
# @router.get("/records/{record_id}", response_model=Record)
# async def get_record(
#     record_id: str,
#     service: Annotated[RecordService, Depends(get_record_service)],
# ) -> Record:
#     """Fetch one record. A missing record raises ResourceNotFoundError in the
#     service and becomes a 404 ErrorResponse in core/handlers.py — there is no
#     `if not record: return JSONResponse(...)` to write here."""
#     return await service.get_record(record_id)
