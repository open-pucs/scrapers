:mod:`openpuc_scrapers.models`
=======================================================================

.. module:: openpuc_scrapers.models
   :synopsis: Data models for representing public utility commission case records.

This module provides Pydantic data models for representing cases, filings, and attachments
scraped from public utility commission websites.

Classes
-------

.. autoclass:: Case
   :members:
   :show-inheritance:

.. autoclass:: Filing
   :members:
   :show-inheritance:

.. autoclass:: Attachment
   :members:
   :show-inheritance:

Examples
--------

Creating a new case record::

    from datetime import date
    from openpuc_scrapers.models import Case, Filing, Attachment
    
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

Working with filing attachments::

    # Access the first filing's attachments
    first_filing = case.filings[0]
    for attachment in first_filing.attachments:
        print(f"Document: {attachment.name} ({attachment.document_type})")
        print(f"URL: {attachment.url}")

Checking case status::

    if case.closed_date:
        print(f"Case {case.case_number} was closed on {case.closed_date}")
    else:
        print(f"Case {case.case_number} is still open")