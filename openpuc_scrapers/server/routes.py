from typing import List

from fastapi import FastAPI
from fastapi.responses import FileResponse

from openpuc_scrapers.db.s3_utils import (
    fetch_attachment_data_from_s3,
    fetch_attachment_file_from_s3,
    fetch_case_filing_from_s3,
)
from openpuc_scrapers.db.sql_utilities import CaseInfo, get_last_updated_cases
from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.raw_attachments import RawAttachment
from openpuc_scrapers.models.hashes import Blake2bHash
from openpuc_scrapers.models.timestamp import rfc_time_from_string


def register_routes(app: FastAPI):
    """
    Register all API routes for the OpenPUC Scrapers server.

    Args:
        app (FastAPI): The FastAPI application instance to register routes on.
    """

    @app.get("/api/cases/{state}/{jurisdiction_name}/{case_name}")
    async def handle_case_filing_from_s3(
        case_name: str, jurisdiction_name: str, state: str
    ) -> GenericCase:
        """
        Fetch a specific case filing from S3.

        Args:
            case_name (str): Name of the case
            jurisdiction_name (str): Name of the jurisdiction
            state (str): State of the jurisdiction

        Returns:
            GenericCase: The requested case filing
        """
        return await fetch_case_filing_from_s3(
            case_name=case_name,
            jurisdiction_name=jurisdiction_name,
            state=state,
        )

    @app.get("/api/caselist/{jurisdiction_name}/all/indexed_after/{rfc339_date}")
    async def handle_caselist_jurisdiction_fetch(
        jurisdiction_name: str, rfc339_date: str, limit: int = 1000
    ) -> List[CaseInfo]:
        """
        Fetch case list for a specific jurisdiction after a given date.

        Args:
            jurisdiction_name (str): Name of the jurisdiction
            rfc339_date (str): RFC3339 formatted timestamp
            limit (int, optional): Maximum number of cases to return. Defaults to 1000.

        Returns:
            List[CaseInfo]: List of case information
        """
        date = rfc_time_from_string(rfc339_date)
        return await get_last_updated_cases(
            indexed_after=date, match_jurisdiction=jurisdiction_name, limit=limit
        )

    @app.get("/api/caselist/all/indexed_after/{rfc339_date}")
    async def handle_caselist_all_fetch(
        rfc339_date: str, limit: int = 1000
    ) -> List[CaseInfo]:
        """
        Fetch case list for all jurisdictions after a given date.

        Args:
            rfc339_date (str): RFC3339 formatted timestamp
            limit (int, optional): Maximum number of cases to return. Defaults to 1000.

        Returns:
            List[CaseInfo]: List of case information
        """
        date = rfc_time_from_string(rfc339_date)
        return await get_last_updated_cases(indexed_after=date, limit=limit)

    @app.get("/api/raw_attachments/{blake2b_hash}/obj")
    async def handle_attachment_data_from_s3(
        blake2b_hash: Blake2bHash,
    ) -> RawAttachment:
        """
        Fetch attachment data from S3 by its Blake2b hash.

        Args:
            blake2b_hash (Blake2bHash): Hash of the attachment

        Returns:
            RawAttachment: The attachment data
        """
        return await fetch_attachment_data_from_s3(hash=blake2b_hash)

    @app.get("/api/raw_attachments/{blake2b_hash}/raw")
    async def handle_attachment_file_from_s3(blake2b_hash: Blake2bHash) -> FileResponse:
        """
        Fetch attachment file from S3 by its Blake2b hash.

        Args:
            blake2b_hash (Blake2bHash): Hash of the attachment

        Returns:
            FileResponse: The attachment file
        """
        file_path = await fetch_attachment_file_from_s3(hash=blake2b_hash)
        return FileResponse(file_path)
