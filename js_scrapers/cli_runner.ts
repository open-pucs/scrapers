import { Scraper, runScraper } from "./pipeline";
import { RawGenericDocket, RawDocketWithJurisdiction } from "./types";
import * as path from "path";

// Rust API used for the downloader.
const OPENSCRAPERS_INTERNAL_API_URL =
  process.env.OPENSCRAPERS_INTERNAL_API_URL || "http://localhost:33399";

/**
 * Processes a specific list of dockets for a given scraper.
 * @param scraper The scraper to use.
 * @param docketIds The list of docket IDs to process.
 */
export async function runScraperForDockets(
  scraper: Scraper,
  docketIds: string[]
) {
  console.log(
    `Running scraper for ${scraper.jurisdiction_name} for ${docketIds.length} specific dockets.`
  );

  const timeNow = new Date().toISOString();
  const basePath = path.join(
    "intermediates",
    scraper.state,
    scraper.jurisdiction_name
  );
  const makeS3JsonSavePath = (path_loc: string) =>
    path.join(basePath, path_loc, `${timeNow}.json`);

  for (const docketId of docketIds) {
    try {
      console.log(`Fetching details for case: ${docketId}`);
      // The getCaseDetails function expects a Partial<RawGenericDocket>.
      // We only have the case_govid, which should be enough for the scraper
      // to fetch the rest of the details.
      const basicCaseData: Partial<RawGenericDocket> = { case_govid: docketId };

      const fullCaseData = await scraper.getCaseDetails(
        basicCaseData,
        makeS3JsonSavePath
      );

      const payload: RawDocketWithJurisdiction = {
        docket: fullCaseData,
        jurisdiction: {
          country: "usa",
          state: scraper.state,
          jurisdiction: scraper.jurisdiction_name,
        },
      };

      // Submit the final object to the API
      const submitUrl = `${OPENSCRAPERS_INTERNAL_API_URL}/admin/cases/submit`;
      const submitResponse = await fetch(submitUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!submitResponse.ok) {
        const errorText = await submitResponse.text();
        throw new Error(
          `Failed to submit case: ${submitResponse.status} ${errorText}`
        );
      }

      console.log(`Successfully submitted case: ${fullCaseData.case_govid}`);
    } catch (error) {
      console.error(`Error processing case: ${docketId}`, error);
    }
  }

  console.log("Scraper run finished for specific dockets.");
}

/**
 * The main entry point for the CLI.
 * @param scraper The scraper to run.
 */
export async function runCli(scraper: Scraper) {
  const args = process.argv.slice(2);

  if (args.length > 0) {
    // If there are command-line arguments, treat them as docket IDs
    await runScraperForDockets(scraper, args);
  } else {
    // If there are no arguments, run the full scraper
    await runScraper(scraper);
  }
}