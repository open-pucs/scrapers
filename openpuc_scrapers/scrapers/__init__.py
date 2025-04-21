
"""Scrapers for various public utility commission websites."""

from typing import Dict, List, Optional, Union

from .base import GenericScraper
from .il import IllinoisICCScraper

__all__ = [
    'GenericScraper',
    'IllinoisICCScraper',
    "NYPUCScraper",
]
