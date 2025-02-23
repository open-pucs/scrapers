Data Models
=================================================

This documentation describes the data models used to represent cases, filings, and attachments scraped from public utility commission websites. The models are implemented using Pydantic BaseModel classes to ensure data validation and provide clear type hints.

Core Models
-----------

Case
~~~~

The ``Case`` model represents a public utility commission case record. Each case has a unique case number and can contain various metadata about the proceedings.

Required Fields:
    - ``case_number`` (str): Unique identifier for the case

Optional Fields:
    - ``case_type`` (str): Classification of the case (e.g., civil, regulatory)
    - ``description`` (str): Detailed description of the case and its purpose
    - ``industry`` (str): Related industry sector 
    - ``petitioner`` (str): Name of the party who filed the case
    - ``hearing_officer`` (str): Name of the assigned hearing officer
    - ``opened_date`` (date): Date when the case was initiated
    - ``closed_date`` (date): Date when the case was closed/resolved
    - ``filings`` (list[Filing]): Collection of associated case filings

Filing
~~~~~~

The ``Filing`` model represents individual documents and submissions made within a case. Each filing represents a formal submission to the commission.

Required Fields:
    - ``filed_date`` (date): Date when the filing was submitted
    - ``party_name`` (str): Name of the submitting party
    - ``filing_type`` (str): Type of filing (e.g., brief, testimony)
    - ``description`` (str): Description of the filing contents

Optional Fields:
    - ``attachments`` (list[Attachment]): Associated documents and files

Attachment
~~~~~~~~~~

The ``Attachment`` model represents individual documents attached to filings, including their metadata and content.

Required Fields:
- ``name`` (str): Name of the attachment file
- ``url`` (HttpUrl): URL where the attachment can be accessed

Optional Fields:
- ``document_type`` (str): File format (e.g., PDF, XLSX)
- ``full_text`` (str): Extracted text content from the document

Relationships
-------------

The models form a hierarchical relationship:

- A ``Case`` can have multiple ``Filing`` objects (one-to-many)
- A ``Filing`` can have multiple ``Attachment`` objects (one-to-many)

This structure reflects the typical organization of utility commission records, where cases contain multiple filings, and filings may include multiple supporting documents.

Data Validation
---------------

All models use Pydantic's BaseModel class, which provides:

- Automatic data validation
- Type checking and coercion
- Optional field handling
- JSON serialization/deserialization

The models support nullable fields through the Optional type hint, allowing for partial data when not all fields are available from the source website.

Usage Example
-------------

.. code-block:: python

    case = Case(
        case_number="PUC-2024-001",
        case_type="regulatory",
        petitioner="Example Utility Co",
        opened_date=date(2024, 1, 15),
        filings=[
            Filing(
                filed_date=date(2024, 1, 15),
                party_name="Example Utility Co",
                filing_type="initial_petition",
                description="Rate increase request",
                attachments=[
                    Attachment(
                        name="petition.pdf",
                        url="https://example.com/files/petition.pdf",
                        document_type="PDF"
                    )
                ]
            )
        ]
    )