from openpuc_scrapers.pipelines.generic_pipeline import process_cases
from openpuc_scrapers.models.misc import post_list_to_endpoint_split
from openpuc_scrapers.scrapers.il import IllinoisICC, ILICCCaseData


# Run Illinois ICC processing test
async def test_il_on_single_case() -> None:
    """
    Test the Illinois ICC scraper on a single test case.
    This function creates a test case, processes it with the scraper,
    and optionally posts the results to an endpoint.
    """
    # Create a test case
    test_case = ILICCCaseData(
        case_url="https://www.icc.illinois.gov/docket/P2025-0274",
        case_number="25-0274",
        category="Electric"
    )
    
    # Initialize the scraper
    il_scraper = IllinoisICC()
    
    # Process the case
    outputs = process_cases(il_scraper, [test_case], ".")
    
    # Assert that at least one output was generated
    assert len(outputs) > 0
    
    # Optional: Post to ingest endpoint (commented out for safety)
    # Uncomment to test posting to an endpoint
    # ingest_url = "https://your-api-endpoint.com/ingest/openscrapers"
    # await post_list_to_endpoint_split(outputs, ingest_url)
    
    # Return the outputs for further inspection if needed
    return outputs


if __name__ == "__main__":
    import asyncio
    
    # Run the test
    print("Running Illinois ICC pipeline test")
    results = asyncio.run(test_il_on_single_case())
    print(f"Test completed with {len(results)} results") 