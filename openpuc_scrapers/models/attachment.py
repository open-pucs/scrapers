from pydantic import BaseModel, HttpUrl
from typing import Optional


class Attachment(BaseModel):
    """Model representing an attachment associated with a filing.

    Attributes:
        name (str): The name of the attachment.
        url (HttpUrl): The URL of the attachment.
        document_type (Optional[str]): The type of document (e.g., PDF, XLSX).
        full_text (Optional[str]): The full text content of the attachment.
    """

    name: str
    url: HttpUrl
    document_type: Optional[str] = None
    full_text: Optional[str] = None
