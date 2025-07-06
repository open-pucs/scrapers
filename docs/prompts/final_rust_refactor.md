Currently I have this python code that is running in
/home/nicole/Documents/mycorrhizae/open-scrapers/openpuc_scrapers/pipelines/raw_attachment_handling.py

That is really slow and taking around 70% of the time in the actual document processing piplelines.

So far most of the rust code has been transfered over into the project 
/home/nicole/Documents/mycorrhizae/open-scrapers/openscraper_processing


Now I want you to modify the python code to jsonify the 

/home/nicole/Documents/mycorrhizae/open-scrapers/openpuc_scrapers/pipelines/generic_pipeline_wrappers.py

```py
# A snippet from: /home/nicole/Documents/mycorrhizae/open-scrapers/openpuc_scrapers/pipelines/generic_pipeline_wrappers.py
def process_case(
    scraper: GenericScraper[StateCaseData, StateFilingData],
    case: StateCaseData,
    base_path: str,
) -> GenericCase:
    # ...
    # Main code for processing case
    # ...
    # NOW THAT THE CASE IS FULLY GENERIC IT SHOULD PUSH ALL THIS STUFF OVER TO RUST

    async def async_shit(case: GenericCase) -> Tuple[GenericCase, int, int]:
        """
        Processes all filings for a case, returning the updated case with
        total counts of successful and errored attachments across all filings.
        """
        # Schedule processing for each generic filing
        tasks = [process_generic_filing(f) for f in case_specific_generic_cases]
        results = await asyncio.gather(*tasks)

        # Aggregate success and error counts and update filings
        total_success = sum(success for (_, success, _) in results)
        total_error = sum(error for (_, _, error) in results)
        case.filings = [f for (f, _, _) in results]

        # Push updated case
        await push_case_to_s3_and_db(
            case=case,
            jurisdiction_name=scraper.jurisdiction_name,
            state=scraper.state,
        )

        return case, total_success, total_error

    return_generic_case, success_count, error_count = asyncio.run(
        async_shit(generic_case)
    )
    default_logger.info(
        f"Of all the attachments in this case, {success_count} were uploaded successfully, and {error_count} encountered an error."
    )
    # INSTEAD OF RETURNING THE CASE REFACTOR THE CODE TO RETURN A SUCCESSFUL SIGNAL
    return return_generic_case
```
Has an async component that handles a bunch of processing info. At this point split from the original code and.

1. Go ahead and make a generic case data with the incomplete processed componnents.

2. Jsonify that and save it to a redis queue.

3. Have the rust component of this project, specifically the worker code at 
/home/nicole/Documents/mycorrhizae/open-scrapers/openscraper_processing/src/worker.rs

pull the json out from the redis queue, deserialize it and begin the processing code.

All the code in the following steps has been completed:

1. Transfer all the types in the files:
/home/nicole/Documents/mycorrhizae/open-scrapers/openpuc_scrapers/models/case.py
/home/nicole/Documents/mycorrhizae/open-scrapers/openpuc_scrapers/models/filing.py
/home/nicole/Documents/mycorrhizae/open-scrapers/openpuc_scrapers/models/attachment.py
/home/nicole/Documents/mycorrhizae/open-scrapers/openpuc_scrapers/models/raw_attachments.py
/home/nicole/Documents/mycorrhizae/open-scrapers/openpuc_scrapers/models/hashes.py
/home/nicole/Documents/mycorrhizae/open-scrapers/openpuc_scrapers/models/timestamp.py

into rust code:

2. Translate all the code in 
/home/nicole/Documents/mycorrhizae/open-scrapers/openpuc_scrapers/pipelines/raw_attachment_handling.py
and 
/home/nicole/Documents/mycorrhizae/open-scrapers/openpuc_scrapers/db/s3_utils.py
into rust functionality.

Now in addition to modifying the python code I want you to take the code in 
/home/nicole/Documents/mycorrhizae/open-scrapers/openpuc_scrapers/server

And translate it to an axum server in 
/home/nicole/Documents/mycorrhizae/open-scrapers/openscraper_processing
