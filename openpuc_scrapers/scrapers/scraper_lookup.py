from typing import List
from pydantic import BaseModel

from openpuc_scrapers.scrapers.base import GenericScraper
from openpuc_scrapers.scrapers.dummy import DummyScraper
from openpuc_scrapers.scrapers.il_puc import IllinoisICCScraper
from openpuc_scrapers.scrapers.ma_puc import MassachusettsDPUScraper
from openpuc_scrapers.scrapers.ny_puc import NYPUCScraper


class ScraperInfoObject(BaseModel):
    id: str
    name: str
    object_type: type[GenericScraper]


SCRAPER_REGISTRY: List[ScraperInfoObject] = [
    ScraperInfoObject(id="ny_puc", name="New York PUC", object_type=NYPUCScraper),
    ScraperInfoObject(id="dummy", name="Dummy Scraper", object_type=DummyScraper),
    ScraperInfoObject(id="il_puc", name="Illinois ICC", object_type=IllinoisICCScraper),
    ScraperInfoObject(
        id="ma_puc", name="Massachusetts PUC", object_type=MassachusettsDPUScraper
    ),
    # ScraperInfoObject(id="co_puc", name="Colorado PUC", object_type=COPUCScraper),
]
