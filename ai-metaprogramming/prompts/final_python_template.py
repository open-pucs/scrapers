from openpuc_scrapers.models.case import GenericCase
from openpuc_scrapers.models.filing import GenericFiling
from openpuc_scrapers.models.attachment import GenericAttachment
from openpuc_scrapers.scrapers.base import GenericScraper

{% if not code %}
{{ raise("Code content is required but was undefined or empty") }}
{% else %}
{{ code }}
{% endif %}
