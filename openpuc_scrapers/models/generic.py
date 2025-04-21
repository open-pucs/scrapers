from datetime import date
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, HttpUrl

class GenericCase(BaseModel):
    """Generic case data model."""
    case_number: str
    case_title: Optional[str] = None
    case_url: str
    category: Optional[str] = None
    service_type: Optional[str] = None
    judge_name: Optional[List[str]] = None
    filing_date: Optional[date] = None
    case_status: Optional[str] = None
    case_description: Optional[str] = None
    applicant: Optional[str] = None
    industry: Optional[str] = None
    documents: List[str] = Field(default_factory=list)
    service_list: List[Dict[str, Union[str, bool]]] = Field(default_factory=list)
    schedule: List[Dict[str, Optional[str]]] = Field(default_factory=list)

class GenericFiling(BaseModel):
    """Generic filing data model."""
    case_number: str
    filed_date: Optional[date] = None
    party_name: Optional[str] = None
    filing_type: Optional[str] = None
    description: Optional[str] = None
    attachments: List[Dict[str, str]] = Field(default_factory=list)
    document_url: str 