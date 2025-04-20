from typing import Any, List, Optional

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.constants import OPENSCRAPERS_SQL_DB_SCONNECTION
from openpuc_scrapers.models.filing import GenericFiling
from openpuc_scrapers.models.timestamp import RFC3339Time

# from sqlalchemy.orm import sessionmaker

# Setup async engine and session


INITIALIZE_LAST_UPDATED = """
CREATE TABLE IF NOT EXISTS public.object_last_updated (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    country VARCHAR NOT NULL,
    state VARCHAR NOT NULL,
    juristiction_name VARCHAR NOT NULL,
    object_type VARCHAR NOT NULL,
    object_name VARCHAR NOT NULL
);
"""
INITIALIZE_ATTACHMENT_TEXT = """
CREATE TABLE IF NOT EXISTS public.attachment_text_reprocessed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    attachment_hash VARCHAR NOT NULL,
    update_type VARCHAR NOT NULL,
    object_type VARCHAR NOT NULL,
    object_name VARCHAR NOT NULL
);
"""


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


Base = declarative_base()
engine = create_async_engine(OPENSCRAPERS_SQL_DB_SCONNECTION, echo=True)


async def hackishly_initialize_db() -> None:
    async with engine.begin() as session:
        await session.execute(text(INITIALIZE_LAST_UPDATED))
        await session.execute(text(INITIALIZE_ATTACHMENT_TEXT))
        await session.commit()


async def set_case_as_updated(
    case: GenericCase, jurisdiction: str, state: str, country: str = "usa"
) -> None:
    await hackishly_initialize_db()
    async with engine.begin() as session:
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

    async with engine.begin() as session:
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
