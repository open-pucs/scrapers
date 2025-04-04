from datetime import datetime, timezone
from typing import List, Optional
import pugsql
from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.constants import SQL_DB_CONNECTION
from openpuc_scrapers.models.filing import GenericFiling


queries = pugsql.module("queries/")

queries.connect(SQL_DB_CONNECTION)


def set_case_as_updated(
    case: GenericCase, jurisdiction: str, state: str, country: str = "usa"
) -> None:
    queries.last_updated_object_upsert(
        object_type="case",
        state=state,
        country=country,
        jurisdiction_name=jurisdiction,
        object_name=getattr(case, "case_number"),
        indexed_before=datetime.now(tz=timezone.utc),
    )


def get_last_updated_cases(
    limit: int = 10, match_jurisdiction: Optional[str] = None
) -> List[GenericFiling]:
    filings = queries.last_updated_objects(
        object_type="case",
        jurisdiction_name=match_jurisdiction,
    )
    return [GenericFiling(**filing) for filing in filings]
