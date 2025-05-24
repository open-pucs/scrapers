Here is this code snippet from some document processing code in
/home/nicole/Documents/mycorrhizae/open-scrapers/openpuc_scrapers/pipelines/generic_pipeline_wrappers.py

```py
    case_specific_generic_cases = []
    for filing in filings:
        generic_filing = scraper.into_generic_filing_data(filing)
        case_specific_generic_cases.append(generic_filing)


    async def async_shit(case: GenericCase) -> Tuple[GenericCase, int, int]:
        tasks = []
        for generic_filing in case_specific_generic_cases:
            tasks.append(process_generic_filing(generic_filing))
        result_generic_filings = await asyncio.gather(*tasks)
        case.filings = result_generic_filings
        await push_case_to_s3_and_db(
            case=case,
            jurisdiction_name=scraper.jurisdiction_name,
            state=scraper.state,
        )
        # TODO: Compute the success count for all attachments, and the error count for all attachments, and return them with the function:
        return case

    return_generic_case, success_count, error_count = asyncio.run(
        async_shit(generic_case)
    )
    default_logger.info(
        f"Of all the attachments in this case, {success_count} were uploaded successfully, and {error_count} encountered an error."
    )
    return return_generic_case
```

Could you descent into the process_generic_filing code to get it to return a success and errored count, tally tghem all together and return it out so it can be logged.



