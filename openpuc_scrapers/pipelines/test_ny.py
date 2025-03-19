from openpuc_scrapers.models.generic_scraper import process_cases
from openpuc_scrapers.models.misc import post_list_to_endpoint_split
from openpuc_scrapers.scrapers.ny import NYPUCDocketInfo, NYPUCScraper


# Run NYPUC processing test
async def test_ny_on_single_case() -> None:

    docket = NYPUCDocketInfo(
        docket_id="18-G-0736",
        matter_type="Complaint",
        matter_subtype="Formal Non-Consumer Related",
        title="Complaint and Formal Dispute Resolution Request For Expedited Resolution of East Coast Power & Gas, LLC Regarding Annual Reconciliation Charges of KeySpan Gas East Corporation d/b/a National Grid for January - April 2018",
        organization="East Coast Power & Gas, LLC",
        date_filed="12/05/2018",
        industry_affected="Gas",  # This field wasn't provided in the comments
    )
    nypuc_scraper = NYPUCScraper()
    outputs = process_cases(nypuc_scraper, [docket], ".")
    assert len(outputs) > 0
    # yes I know its bad practice, but I really need to test our pipeline to see if this works with the generic scraping framework, I will remove it later I promise :) - nic
    #
    kessler_docs_ingest_url = (
        "https://nightly-api.kessler.xyz/ingest-v1/ingest-docs/openscrapers"
    )
    await post_list_to_endpoint_split(outputs, kessler_docs_ingest_url)
