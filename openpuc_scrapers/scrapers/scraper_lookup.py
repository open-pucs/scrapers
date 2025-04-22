from typing import List
from pydantic import BaseModel

from openpuc_scrapers.scrapers.base import GenericScraper
from openpuc_scrapers.scrapers.dummy import DummyScraper
from openpuc_scrapers.scrapers.ny_puc import NYPUCScraper


# class ScraperName(str, Enum):
#     NY_PUC = "ny_puc"
#     MA_PUC = "ma_puc"
#     IL_PUC = "il_puc"
#     CO_PUC = "co_puc"
#     DUMMY = "dummy"


class ScraperInfoObject(BaseModel):
    id: str
    name: str
    object_type: type[GenericScraper]


SCRAPER_REGISTRY: List[ScraperInfoObject] = [
    ScraperInfoObject(id="ny_puc", name="New York PUC", object_type=NYPUCScraper),
    ScraperInfoObject(id="dummy", name="Dummy Scraper", object_type=DummyScraper),
    # ScraperInfoObject(id="ma_puc", name="Massachusetts PUC", object_type=MAPUCScraper),
    # ScraperInfoObject(id="il_puc", name="Illinois PUC", object_type=ILPUCScraper),
    # ScraperInfoObject(id="co_puc", name="Colorado PUC", object_type=COPUCScraper),
]
