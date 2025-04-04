from datetime import datetime, timezone
from typing import List, Optional
import pugsql
from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.constants import SQL_DB_CONNECTION
from openpuc_scrapers.models.filing import GenericFiling


queries = pugsql.module("queries/")

queries.connect(SQL_DB_CONNECTION)


async def set_case_as_updated(
    case: GenericCase, juristiction: str, state: str, country: str = "usa"
) -> None:
    queries.last_updated_object_upsert(
        object_type="case",
        state=state,
        country=country,
        jurisdiction_name=juristiction,
        object_name=getattr(case, "case_number"),
        indexed_before=datetime.now(tz=timezone.utc),
    )


async def get_last_updated_cases(
    limit: int = 10, match_juristiction: Optional[str] = None
) -> List[GenericFiling]:
    filings = queries.last_updated_objects(
        object_type="case",
        jurisdiction_name=match_juristiction,
    )
    return [GenericFiling(**filing) for filing in filings]
