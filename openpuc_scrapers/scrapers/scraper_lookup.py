from typing import Any, List, Optional
from pydantic import BaseModel

from openpuc_scrapers.scrapers.base import GenericScraper
from openpuc_scrapers.scrapers.dummy import DummyScraper
from openpuc_scrapers.scrapers.il_puc import IllinoisICCScraper
from openpuc_scrapers.scrapers.ma_puc import MassachusettsDPUScraper
from openpuc_scrapers.scrapers.ny_puc import NYPUCDocket, NYPUCScraper
from openpuc_scrapers.scrapers.ut_dogm import UTDOGMDocket, UTDOGMScraper


class ScraperInfoObject(BaseModel):
    id: str
    name: str
    object_type: type[GenericScraper]
    test_singular_docket: Optional[Any] = None


SCRAPER_REGISTRY: List[ScraperInfoObject] = [
    ScraperInfoObject(
        id="ny_puc",
        name="New York PUC",
        object_type=NYPUCScraper,
        test_singular_docket=NYPUCDocket(
            case_number="18-G-0736",
            matter_type="Complaint",
            matter_subtype="Formal Non-Consumer Related",
            case_title="Complaint and Formal Dispute Resolution Request For Expedited Resolution of East Coast Power & Gas, LLC Regarding Annual Reconciliation Charges of KeySpan Gas East Corporation d/b/a National Grid for January - April 2018",
            organization="East Coast Power & Gas, LLC",
            date_filed="12/05/2018",
            industry_affected="Gas",  # This field wasn't provided in the comments
        ),
    ),
    ScraperInfoObject(
        id="ut_dogm",
        name="Utah Divison of Oil and Gas",
        object_type=UTDOGMScraper,
        test_singular_docket=UTDOGMDocket(
            case_number="18-G-0736",
            matter_type="Complaint",
            matter_subtype="Formal Non-Consumer Related",
            case_title="Complaint and Formal Dispute Resolution Request For Expedited Resolution of East Coast Power & Gas, LLC Regarding Annual Reconciliation Charges of KeySpan Gas East Corporation d/b/a National Grid for January - April 2018",
            organization="East Coast Power & Gas, LLC",
            date_filed="12/05/2018",
            industry_affected="Gas",  # This field wasn't provided in the comments
        ),
    ),
    ScraperInfoObject(id="dummy", name="Dummy Scraper", object_type=DummyScraper),
    ScraperInfoObject(id="il_puc", name="Illinois ICC", object_type=IllinoisICCScraper),
    ScraperInfoObject(
        id="ma_puc", name="Massachusetts PUC", object_type=MassachusettsDPUScraper
    ),
    # ScraperInfoObject(id="co_puc", name="Colorado PUC", object_type=COPUCScraper),
]
