from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GenericAttachment(BaseModel):
    """Generic attachment data model."""

    name: str
    document_extension: str
    url: str
    attachment_type: str
    attachment_subtype: str
    extra_metadata: Dict[str, Any]
    # Default value here since 99% of the time this should be set by the api.
    hash: Optional[str] = None


class GenericFiling(BaseModel):
    """Generic filing data model."""

    name: str
    filed_date: date
    organization_authors: List[str]
    individual_authors: List[str]
    filing_type: str
    description: str
    attachments: List[GenericAttachment]
    extra_metadata: Dict[str, Any]


class GenericParty(BaseModel):
    """Generic party data model."""

    name: str
    is_corperate_entity: bool
    is_human: bool


class GenericCase(BaseModel):
    """Generic case data model."""

    case_govid: str
    opened_date: Optional[date] = None
    case_name: str
    case_url: str
    case_type: str
    description: str
    industry: str
    petitioner: str
    hearing_officer: str
    closed_date: Optional[date]
    filings: List[GenericFiling]
    case_parties: List[GenericParty]
    extra_metadata: Dict[str, Any]
