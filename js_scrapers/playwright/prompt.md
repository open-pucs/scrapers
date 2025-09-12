In /home/nicole/Documents/mycorrhiza/scrapers/js_scrapers/playwright/ny_puc_scraper.spec.ts

please make it so that the function

```ts
  async scrapeByGovIds(govIds: string[], mode: ScrapingMode): Promise<any[]> {
    console.log(
      `Scraping ${govIds.length} cases in ${mode} mode (parallel processing)`,
    );

    switch (mode) {
      case ScrapingMode.METADATA:
        return await this.scrapeMetadataOnly(govIds);

      case ScrapingMode.DOCUMENTS:
        return await this.scrapeDocumentsOnly(govIds);

      case ScrapingMode.PARTIES:
        return await this.scrapePartiesOnly(govIds);

      case ScrapingMode.FULL_EXTRACTION:
        console.log(
          `Running full extraction for ${govIds.length} cases with max ${this.max_concurrent_browsers} concurrent browsers`,
        );
        const scrapeExtractionForId = async (govId: string) => {
          try {
            // Run all three operations in parallel for each ID
            const [metadata, documents, parties] = await Promise.all([
              this.getCaseMeta(govId),
              this.scrapeDocumentsOnly([govId]),
              this.scrapePartiesOnly([govId]),
            ]);

            if (metadata) {
              metadata.filings = documents;
              metadata.case_parties = parties;
              return metadata;
            }
            return null;
          } catch (error) {
            console.error(`Error in full extraction for ${govId}:`, error);
            return null;
          }
        };

        const extractionResults = await this.processTasksWithQueue(
          govIds,
          scrapeExtractionForId,
        );
        return extractionResults.filter((result) => result !== null);

      default:
        throw new Error(`Unsupported scraping mode: ${mode}`);
    }
  }
```

always returns a list of Partial<RawGenericDocket>. For the parties and fillings only modes, it should just return an object of the form {"case_govid": govid, "fillings": fillings}.

Also the concurrency for this seems kinda sloppy right now with process with queue being handled in each of the seperate functions, for reference scrapeMetadataOnly, scrapePartiesOnly and scrapeDocumentsOnly should not have built in concurrency and only operate on a single govid. If there is any concurrency it should be handled directly in the scrapeByGovIds function.
