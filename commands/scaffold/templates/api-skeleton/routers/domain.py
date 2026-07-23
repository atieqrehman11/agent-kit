from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["Domain"])

# TODO: implement domain endpoints following docs/API_STANDARDS.md
#
# Rules (from docs/API_STANDARDS.md):
#   - Paths:   /v1/{plural-resource}  (lowercase, hyphenated)
#   - Params:  snake_case query/path parameter names
#   - Responses: objects, not bare arrays; include X-Request-ID
#   - Lists:   use the pagination envelope (items, limit, offset, total, has_more)
#   - Errors:  return ErrorResponse from schema/models.py — never FastAPI's {"detail": ...}
#   - No POST /v1/chat/message — chat belongs in ai-prototype-chat-api
#
# Example — list endpoint:
#
# from schema.models import ErrorResponse
#
# @router.get("/records")
# async def list_records(limit: int = 100, offset: int = 0):
#     # TODO: query Unity Catalog via SQL warehouse
#     return {
#         "items": [],
#         "limit": limit,
#         "offset": offset,
#         "total": 0,
#         "has_more": False,
#     }
#
# Example — detail endpoint:
#
# @router.get("/records/{record_id}")
# async def get_record(record_id: str):
#     # TODO: fetch by ID
#     ...
