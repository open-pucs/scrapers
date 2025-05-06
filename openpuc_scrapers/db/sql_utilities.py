# Having a sqldb connection in this python project is adding a bunch of dependancies and complexity that in my opinion isnt needed.
# What I would like to do is using only really simple data primatives that exist inside redis.
# A docket consists of 4 values
# - A unique name for that docket.
# - A jurisdiction name for that docket.
# - The unix time that docket was last updated.
# - A bytestring that represents the data for that object.
# We need to fufill a couple basic requirements.
# 1. Every time a docket is indexed, if it doesnt exist in the datastructure, it should be added. If it already exists and matches on its id, it should update the data, juristiction_name, and most importantly unix-timestamp for that object. (It might do this just by deleting the old one and inserting the newest one.)
# 2. The datastructure should support a fast query that gets all the dockets that have been ingested since a certain timestamp.
# 3. Another query that just gets all the latest ingested dockets for a certain jurisdiction.
#
from typing import Any, List, Optional

from pydantic import BaseModel
from openpuc_scrapers.db.s3_wrapper import S3FileManager
from openpuc_scrapers.models.constants import (
    OPENSCRAPERS_REDIS_URL,
    OPENSCRAPERS_S3_OBJECT_BUCKET,
)
from redis import Redis, from_url

from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.timestamp import (
    RFC3339Time,
    rfc_time_now,
    rfc_time_to_timestamp,
)

# Redis connection URL (e.g. "redis://localhost:6379/0")
# You can also use environment variables or config.

# Namespaces for our sorted sets
GLOBAL_BY_TIME = "dockets:by_time"
JURISDICTION_PREFIX = "dockets:by_jurisdiction:"

# Setup Redis client
redis: Redis = from_url(OPENSCRAPERS_REDIS_URL, decode_responses=False)


class CaseInfo(BaseModel):
    country: str
    state: str
    jurisdiction_name: str
    indexed_at: Optional[RFC3339Time] = None
    case: GenericCase


class CaseInfoMinimal(BaseModel):
    country: str
    state: str
    jurisdiction_name: str
    indexed_at: Optional[RFC3339Time] = None
    case_id: str


def generate_case_uuid(case_info: CaseInfo) -> str:
    return (
        f"{case_info.state}-{case_info.jurisdiction_name}-{case_info.case.case_number}"
    )


async def set_case_as_updated(
    case_info: CaseInfo,
) -> None:
    """
    Upsert a docket into Redis. We index by case.case_number as the unique ID.
    This will:
      1. HSET the hash for the docket
      2. ZADD the global by-time set
      3. ZADD the jurisdiction-specific set
    """
    docket_uuid = generate_case_uuid(case_info=case_info)
    updated_at = case_info.indexed_at
    if updated_at is None:
        updated_at = rfc_time_now()
    updated_at_timestamp = int(rfc_time_to_timestamp(updated_at))

    # 1. Store the fields in a hash
    redis.set(
        f"docket:{docket_uuid}",
        case_info.model_dump_json(),
    )

    # 2. Add/update in the global sorted set
    redis.zadd(GLOBAL_BY_TIME, {docket_uuid: updated_at_timestamp})

    # 3. Add/update in the jurisdiction-specific sorted set
    redis.zadd(
        f"{JURISDICTION_PREFIX}{case_info.jurisdiction_name}",
        {docket_uuid: updated_at_timestamp},
    )


async def get_all_cases_from_jurisdiction(
    jurisdiction_name: str, state: str, country: str = "usa"
) -> List[CaseInfoMinimal]:
    s3 = S3FileManager(OPENSCRAPERS_S3_OBJECT_BUCKET)
    # example "objects/usa/ny/ny_puc/18-G-0736.json"
    prefix = f"objects/{country}/{state}/{jurisdiction_name}/"
    caseidlist = await s3.list_objects_with_prefix_async(prefix=prefix)

    def gen_caseinfo(case_id: str) -> CaseInfoMinimal:
        case_id_minified = case_id.split("/")[-1].split(".json")[
            0
        ]  # Extract filename without path or extension
        return CaseInfoMinimal(
            case_id=case_id_minified,
            jurisdiction_name=jurisdiction_name,
            state=state,
            country=country,
        )

    case_info_list = []
    for case_id in caseidlist:
        case_info_list.append(gen_caseinfo(case_id))
    return case_info_list


async def get_last_updated_cases(
    indexed_after: RFC3339Time,
    limit: int = 10,
    match_jurisdiction: Optional[str] = None,
) -> List[CaseInfo]:
    """
    Retrieve dockets updated after `indexed_after`. Optionally filter by jurisdiction.
    """
    # Convert to unix timestamp
    ts = int(indexed_after.timestamp())

    # Pick the appropriate sorted set
    if match_jurisdiction:
        key = f"{JURISDICTION_PREFIX}{match_jurisdiction}"
        # ZRANGEBYSCORE returns in ascending score (older→newer)
        ids = redis.zrangebyscore(key, ts, "+inf", start=0, num=limit)
    else:
        ids = redis.zrangebyscore(GLOBAL_BY_TIME, ts, "+inf", start=0, num=limit)

    results: List[CaseInfo] = []
    for docket_id in ids:
        h = redis.get(f"docket:{docket_id}")
        # h is a serialized str
        results.append(CaseInfo.model_validate_json(h))

    return results
