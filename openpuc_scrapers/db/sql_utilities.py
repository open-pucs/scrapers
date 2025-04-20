from typing import Any, List, Optional

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.constants import OPENSCRAPERS_SQL_DB_SCONNECTION
from openpuc_scrapers.models.filing import GenericFiling
from openpuc_scrapers.models.timestamp import RFC3339Time

# from sqlalchemy.orm import sessionmaker

# Setup async engine and session


# SQL Queries as constants with corrected juristiction spelling
UPSERT_LAST_UPDATED = """
INSERT INTO public.object_last_updated (
    country,
    state,
    juristiction_name,
    object_type,
    object_name
) VALUES (
    :country,
    :state,
    :juristiction_name,
    :object_type,
    :object_name
)
ON CONFLICT (country, state, juristiction_name, object_type, object_name)
DO UPDATE SET indexed_at = NOW();
"""

LIST_NEWEST_ALL = """
SELECT *
FROM public.object_last_updated
WHERE indexed_at > :indexed_after
ORDER BY updated_at ASC
LIMIT :limit;
"""

LIST_NEWEST_JURISDICTION = """
SELECT *
FROM public.object_last_updated
WHERE indexed_at > :indexed_after
  AND juristiction_name = :juristiction_name
ORDER BY updated_at ASC
LIMIT :limit;
"""

engine = create_async_engine(OPENSCRAPERS_SQL_DB_SCONNECTION)

MakeAsyncSession = sessionmaker(
    engine=engine, class_=AsyncSession, expire_on_commit=False
)


# File "/usr/local/lib/python3.12/asyncio/base_events.py", line 691, in run_until_complete
#     return future.result()
#            ^^^^^^^^^^^^^^^
#   File "/app/openpuc_scrapers/pipelines/generic_pipeline_wrappers.py", line 80, in async_shit
#     await push_case_to_s3_and_db(
#   File "/app/openpuc_scrapers/db/s3_utils.py", line 77, in push_case_to_s3_and_db
#     await set_case_as_updated(
#   File "/app/openpuc_scrapers/db/sql_utilities.py", line 66, in set_case_as_updated
#     async with MakeAsyncSession() as session:
#                ^^^^^^^^^^^^^^^^^^
#   File "/home/airflow/.local/lib/python3.12/site-packages/sqlalchemy/orm/session.py", line 4279, in __call__
#     return self.class_(**local_kw)
#            ^^^^^^^^^^^^^^^^^^^^^^^
#   File "/home/airflow/.local/lib/python3.12/site-packages/sqlalchemy/ext/asyncio/session.py", line 107, in __init__
#     self.sync_session_class(bind=bind, binds=binds, **kw)
# TypeError: Session.__init__() got an unexpected keyword argument 'engine'
async def set_case_as_updated(
    case: GenericCase, jurisdiction: str, state: str, country: str = "usa"
) -> None:
    # This async with line has the following errors as well
    # Diagnostics:
    # 1. Object of type "Session" cannot be used with "async with" because it does not correctly implement __aenter__
    #      Attribute "__aenter__" is unknown [reportGeneralTypeIssues]
    # 2. Object of type "Session" cannot be used with "with" because it does not correctly implement __aexit__
    #      Attribute "__aexit__" is unknown [reportGeneralTypeIssues]
    async with MakeAsyncSession() as session:
        # Note: Fixed juristiction_name spelling and removed extra indexed_before
        await session.execute(
            text(UPSERT_LAST_UPDATED),
            {
                "country": country,
                "state": state,
                "juristiction_name": jurisdiction,
                "object_type": "case",
                "object_name": getattr(case, "case_number"),
            },
        )
        await session.commit()


class Caseinfo(BaseModel):
    country: str
    state: str
    jurisdiction_name: str
    indexed_at: RFC3339Time


async def get_last_updated_cases(
    indexed_after: RFC3339Time,
    limit: int = 10,
    match_jurisdiction: Optional[str] = None,
) -> List[Caseinfo]:
    def row_into_caseinfo(row: Any) -> Caseinfo:
        return Caseinfo(
            country=row.country,
            state=row.state,
            jurisdiction_name=row.juristiction_name,
            indexed_at=row.indexed_at,
        )

    indexed_after_datetime = indexed_after.time

    async with MakeAsyncSession() as session:
        if match_jurisdiction:
            result = await session.execute(
                text(LIST_NEWEST_JURISDICTION),
                {
                    "indexed_after": indexed_after_datetime,
                    "juristiction_name": match_jurisdiction,
                    "limit": limit,
                    "object_type": "case",
                },
            )
        else:
            result = await session.execute(
                text(LIST_NEWEST_ALL),
                {
                    "indexed_after": indexed_after_datetime,
                    "limit": limit,
                    "object_type": "case",
                },
            )

        return [row_into_caseinfo(row) for row in result]
