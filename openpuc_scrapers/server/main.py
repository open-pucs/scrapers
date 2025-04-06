from typing import List, Union
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openpuc_scrapers.db.s3_utils import (
    fetch_attachment_data_from_s3,
    fetch_attachment_file_from_s3,
    fetch_case_filing_from_s3,
)
from openpuc_scrapers.db.sql_utilities import Caseinfo, get_last_updated_cases
from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.raw_attachments import RawAttachment
from openpuc_scrapers.models.hashes import Blake2bHash
from openpuc_scrapers.models.timestamp import RFC3339Time, rfc_time_from_string

app = FastAPI()
app.mount("/", StaticFiles(directory="static", html=True), name="static")


# Root endpoint now served by static homepage


@app.get("/api/cases/{state}/{jurisdiction_name}/{case_name}")
async def handle_case_filing_from_s3(
    case_name: str, jurisdiction_name: str, state: str
) -> GenericCase:
    return await fetch_case_filing_from_s3(
        case_name=case_name,
        jurisdiction_name=jurisdiction_name,
        state=state,
    )


@app.get("/api/caselist/{jurisdiction_name}/all/indexed_after/{rfc339_date}")
async def handle_caselist_jurisdiction_fetch(
    jurisdiction_name: str, rfc339_date: str, limit: int = 1000
) -> List[Caseinfo]:
    date = rfc_time_from_string(rfc339_date)
    return await get_last_updated_cases(
        indexed_after=date, match_jurisdiction=jurisdiction_name, limit=limit
    )


@app.get("/api/caselist/all/indexed_after/{rfc339_date}")
async def handle_caselist_all_fetch(
    rfc339_date: str, limit: int = 1000
) -> List[Caseinfo]:
    date = rfc_time_from_string(rfc339_date)
    return await get_last_updated_cases(indexed_after=date, limit=limit)


@app.get("/api/raw_attachments/{blake2b_hash}/obj")
async def handle_attachment_data_from_s3(blake2b_hash: Blake2bHash) -> RawAttachment:
    return await fetch_attachment_data_from_s3(hash=blake2b_hash)


@app.get("/api/raw_attachments/{blake2b_hash}/raw")
async def handle_attachment_file_from_s3(blake2b_hash: Blake2bHash) -> FileResponse:
    file_path = await fetch_attachment_file_from_s3(hash=blake2b_hash)
    return FileResponse(file_path)
