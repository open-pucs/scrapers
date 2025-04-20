from openpuc_scrapers.db.airflow_basemodel import AirflowBaseModel
from typing import Any, Dict, Optional

from openpuc_scrapers.models.timestamp import RFC3339Time, rfc_time_now

from .filing import GenericFiling


class GenericCase(AirflowBaseModel):
    """Model representing case data.

    Attributes:
        case_number (str): The unique case number.
        case_type (Optional[str]): The type of the case (e.g., civil, regulatory).
        description (Optional[str]): A detailed description of the case.
        industry (Optional[str]): The industry related to the case.
        petitioner (Optional[str]): The name of the petitioner in the case.
        hearing_officer (Optional[str]): The hearing officer for the case.
        opened_date (Optional[date]): The date the case was opened.
        closed_date (Optional[date]): The date the case was closed.
        filings (Optional[list[Filing]]): A list of filings associated with the case.
    """

    case_number: str
    case_type: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    petitioner: Optional[str] = None
    hearing_officer: Optional[str] = None
    opened_date: Optional[RFC3339Time] = None
    closed_date: Optional[RFC3339Time] = None
    filings: Optional[list[GenericFiling]] = None
    extra_metadata: Dict[str, Any] = {}
    indexed_at: RFC3339Time = rfc_time_now()
