# Step 1: Recognisance

Your goal for this first step is to crawl the website and come back with a schema for all the important types of data on the website, and get back a specific site representation of the following data types:

1. A datatype modeling the dockets/proceedings availible on the website.

2. Another modeling the filings present in each docket/proceedings.

3. Another modeling the attachments that might be adjoined to each attachment. 

NOTE: Depending on the website the attachments could either be fetchable in a seperate page for each filing, or the page that displays filings could actually display attachments, and all the attachments in a filing could be linked by sharing a common file/filing id.

NOTE: For all of the schemas, name each field so that its identicial to what its called on the website for easier debugging.


For your report back go ahead and let me know what type of website it is where it stores the attachments, as well as each website endpoint we should scrape to get that data.

For instance here is some example schemas for the New York Public Utilities Comission.

```py
class NYPUCAttachment(BaseModel):
    document_title: str = ""
    url: HttpUrl
    file_format: str = ""
    document_type: str = ""
    file_name: str = ""


class NYPUCFiling(BaseModel):
    attachments: List[NYPUCAttachment] = []
    filing_type: str = ""
    case_number: str = ""
    date_filed: str = ""
    filing_on_behalf_of: str = ""
    description_of_filing: str = ""
    filing_no: str = ""
    filed_by: str = ""
    response_to: str = ""


class NYPUCDocket(BaseModel):
    case_number: str  # 24-C-0663
    matter_type: str  # Complaint
    matter_subtype: str  # Appeal of an Informal Hearing Decision
    case_title: str  # In the Matter of the Rules and Regulations of the Public Service
    organization: str  # Individual
    date_filed: str
    industry_affected: str
    related_cases: List["NYPUCDocket"] = []
    party_list: List[str] = []  # List of organizations/parties
```



