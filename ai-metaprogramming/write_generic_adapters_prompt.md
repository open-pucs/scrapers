Take these schemas 

```py
{state_specific_schemas}
```

and write adapter functions to transform them into these types:

```py
class GenericCase(BaseModel):
    """Model representing case data.
    Attributes:
        case_number (str): The unique case number.
        case_type (Optional[str]): The type of the case (e.g., civil, regulatory).
        description (Optional[str]): A detailed description of the case.
        industry (Optional[str]): The industry related to the case.
        petitioner (Optional[str]): The name of the petitioner in the case.
        hearing_officer (Optional[str]): The hearing officer for the case.
        opened_date (Optional[date]): The date the case was opened.
        closed_date (Optional[date]): The date the case was closed.
        filings (Optional[list[Filing]]): A list of filings associated with the case.
    """
    case_number: str
    case_type: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    petitioner: Optional[str] = None
    hearing_officer: Optional[str] = None
    opened_date: Optional[date] = None
    closed_date: Optional[date] = None
    filings: Optional[list[GenericFiling]] = None
    extra_metadata: Dict[str, Any] = {}

class GenericFiling(BaseModel):
    """Model representing filing data within a case.
    Attributes:
        case_number (str): The unique case number associated with the filing.
        filed_date (date): The date the filing was made.
        party_name (str): The name of the party submitting the filing.
        filing_type (str): The type of filing (e.g., brief, testimony).
        description (str): A description of the filing.
        attachments (Optional[list[Attachment]]): A list of associateda ttachments.
    """
    filed_date: date
    party_name: str
    filing_type: str
    description: str
    attachments: List[GenericAttachment] = []
    extra_metadata: Dict[str, Any] = {}

class GenericAttachment(BaseModel):
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
    extra_metadata: Dict[str, Any] = {}
```


