from pydantic import BaseModel, Field

from openpuc_scrapers.models.case import GenericCase


class JurisdictionInfo(BaseModel):
    country: str
    state: str
    jurisdiction: str


class CaseWithJurisdiction(BaseModel):
    case: GenericCase
    jurisdiction: JurisdictionInfo
