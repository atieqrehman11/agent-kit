"""All I/O. One class per concern — a table, an object store, an upstream API, a model.

Everything that leaves this process goes through here: the SQL warehouse, object
storage, external HTTP, and any LLM call. Timeouts, retries and backoff live in this
layer, and a repository raises a domain exception when it gives up — never a raw
client error, and never a business decision. See docs/SERVICE_STRUCTURE_STANDARDS.md §1.

A repository never calls a service.

Shape to copy (repositories/record_repository.py):

    import logging
    from typing import Annotated, Optional

    from fastapi import Depends

    from core.config import Settings, get_settings
    from core.exceptions import ServiceUnavailableError

    logger = logging.getLogger(__name__)


    class RecordRepository:
        def __init__(self, settings: Settings) -> None:
            # Catalog, schema and table prefix come from configuration — never a
            # literal here (docs/SERVICE_STRUCTURE_STANDARDS.md §5).
            self._table = (
                f"{settings.databricks_catalog}"
                f".{settings.databricks_gold_schema}"
                f".{settings.table_prefix}records"
            )
            self._timeout = settings.request_timeout_seconds

        async def fetch_by_id(self, record_id: str) -> Optional[Record]:
            # Parameterised — never an f-string with caller input in the predicate.
            sql = f"SELECT * FROM {self._table} WHERE record_id = :record_id"
            try:
                ...
            except TimeoutError as exc:
                logger.warning("warehouse timeout", extra={"table": self._table})
                raise ServiceUnavailableError("The data warehouse is unavailable.") from exc
"""
