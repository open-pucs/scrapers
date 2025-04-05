from datetime import datetime, timezone
from typing import List, Optional
import pugsql
from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.constants import SQL_DB_CONNECTION
from openpuc_scrapers.models.filing import GenericFiling


from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

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

engine = create_async_engine(SQL_DB_CONNECTION)

MakeAsyncSession = sessionmaker(
    engine=engine, class_=AsyncSession, expire_on_commit=False
)


async def set_case_as_updated(
    case: GenericCase, jurisdiction: str, state: str, country: str = "usa"
) -> None:
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


async def get_last_updated_cases(
    indexed_after: datetime,
    limit: int = 10,
    match_jurisdiction: Optional[str] = None,
    # Added required indexed_before parameter missing in original
) -> List[GenericFiling]:
    async with MakeAsyncSession() as session:
        if match_jurisdiction:
            result = await session.execute(
                text(LIST_NEWEST_JURISDICTION),
                {
                    "indexed_after": indexed_after,
                    "juristiction_name": match_jurisdiction,
                    "limit": limit,
                    # Added object_type filter missing in original SQL
                    "object_type": "case",
                },
            )
        else:
            result = await session.execute(
                text(LIST_NEWEST_ALL),
                {
                    "indexed_after": indexed_after,
                    "limit": limit,
                    # Added object_type filter missing in original SQL
                    "object_type": "case",
                },
            )

        return [GenericFiling(**row._mapping) for row in result]
