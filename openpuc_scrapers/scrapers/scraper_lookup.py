from enum import Enum
from typing import Optional

from openpuc_scrapers.scrapers.base import GenericScraper
from openpuc_scrapers.scrapers.ny_puc import NYPUCScraper


class ScraperName(str, Enum):
    NY_PUC = "ny_puc"
    MA_PUC = "ma_puc"
    IL_PUC = "il_puc"
    CO_PUC = "co_puc"


def get_scraper_type_from_name(name: ScraperName) -> type[GenericScraper]:
    match name:
        case ScraperName.NY_PUC:
            return NYPUCScraper
        case ScraperName.MA_PUC:
            raise ValueError("Not implemented")
        case ScraperName.IL_PUC:
            raise ValueError("Not implemented")
        case ScraperName.CO_PUC:
            raise ValueError("Not implemented")
        # case _:
        #     raise ValueError("Scraper not Found")


def get_scraper_type_from_name_unvalidated(name: str) -> type[GenericScraper]:
    try:
        scraper_name = ScraperName(name)
    except ValueError:
        raise ValueError(f"Invalid scraper name: {name}") from None
    return get_scraper_type_from_name(scraper_name)
