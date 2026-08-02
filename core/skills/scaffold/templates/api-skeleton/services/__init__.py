"""Business logic. One module per use case.

A service knows nothing about HTTP — no status codes, no Request/Response objects, no
headers, no HTTPException. That is what lets the same logic be called by a job, a
consumer or an agent tool later. See docs/SERVICE_STRUCTURE_STANDARDS.md §1.

Shape to copy (services/record_service.py):

    import logging
    from typing import Annotated

    from fastapi import Depends

    from core.exceptions import ResourceNotFoundError
    from repositories.record_repository import RecordRepository, get_record_repository
    from schema.models import Page

    logger = logging.getLogger(__name__)


    class RecordService:
        def __init__(self, repository: RecordRepository) -> None:
            self._repository = repository

        async def get_record(self, record_id: str) -> Record:
            record = await self._repository.fetch_by_id(record_id)
            if record is None:
                # A domain exception, not an HTTPException. The boundary decides
                # this is a 404; the service only says what went wrong.
                raise ResourceNotFoundError(f"No record with id {record_id}.")
            logger.debug("record loaded", extra={"record_id": record_id})
            return record


    def get_record_service(
        repository: Annotated[RecordRepository, Depends(get_record_repository)],
    ) -> RecordService:
        return RecordService(repository)
"""
