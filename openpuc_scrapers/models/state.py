from datetime import date
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, HttpUrl

class StateCaseData(BaseModel):
    """Base class for state-specific case data."""
    case_number: str
    case_title: Optional[str] = None
    case_url: HttpUrl
    category: Optional[str] = None
    service_type: Optional[str] = None
    judge_name: Optional[List[str]] = None
    filing_date: Optional[date] = None
    case_status: Optional[str] = None
    case_description: Optional[str] = None
    applicant: Optional[str] = None
    industry: Optional[str] = None

class StateFilingData(BaseModel):
    """Base class for state-specific filing data."""
    case_number: str
    filed_date: Optional[date] = None
    party_name: Optional[str] = None
    filing_type: Optional[str] = None
    description: Optional[str] = None
    document_url: HttpUrl 