from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pydantic import BaseModel
from datetime import date

from openpuc_scrapers.models.timestamp import RFC3339Time

from .attachment import GenericAttachment


class GenericFiling(BaseModel):
    """Model representing filing data within a case.

    Attributes:
        case_number (str): The unique case number associated with the filing.
        filed_date (date): The date the filing was made.
        party_name (str): The name of the party submitting the filing.
        filing_type (str): The type of filing (e.g., brief, testimony).
        description (str): A description of the filing.
        attachments (Optional[list[Attachment]]): A list of associateda ttachments.
    """

    filed_date: RFC3339Time
    party_name: str
    filing_type: str
    description: str
    attachments: List[GenericAttachment] = []
    extra_metadata: Dict[str, Any] = {}
