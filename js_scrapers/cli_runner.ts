import { Scraper, runScraper } from "./pipeline";
import { RawGenericDocket, RawDocketWithJurisdiction } from "./types";
import * as path from "path";

// Rust API used for the downloader.
const OPENSCRAPERS_INTERNAL_API_URL =
  process.env.OPENSCRAPERS_INTERNAL_API_URL || "http://localhost:33399";

/**
 * Processes a specific list of dockets for a given scraper.
 * @param scraper The scraper to use.
 * @param dockets The list of dockets to process.
 */
export async function runScraperForDockets(
  scraper: Scraper,
  dockets: Partial<RawGenericDocket>[]
) {
  console.log(
    `Running scraper for ${scraper.jurisdiction_name} for ${dockets.length} specific dockets.`
  );

  const timeNow = new Date().toISOString();
  const basePath = path.join(
    "intermediates",
    scraper.state,
    scraper.jurisdiction_name
  );
  const makeS3JsonSavePath = (path_loc: string) =>
    path.join(basePath, path_loc, `${timeNow}.json`);

  for (const basicCaseData of dockets) {
    try {
      console.log(
        `Fetching details for case: ${basicCaseData.case_govid || "N/A"}`
      );
      // The getCaseDetails function expects a Partial<RawGenericDocket>.

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
      console.error(
        `Error processing case: ${basicCaseData.case_govid || "N/A"}`,
        error
      );
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
    // If there are command-line arguments, treat them as a JSON string
    // of a Partial<RawGenericDocket> or a list of the same.
    const docketsJSON = args[0];
    try {
      let dockets: Partial<RawGenericDocket>[];
      const parsed = JSON.parse(docketsJSON);

      if (Array.isArray(parsed)) {
        dockets = parsed;
      } else {
        dockets = [parsed];
      }
      await runScraperForDockets(scraper, dockets);
    } catch (e) {
      console.error(
        "Could not parse input as JSON, please pass in a JSON string of a Partial<RawGenericDocket> or a list of the same",
        e
      );
    }
  } else {
    // If there are no arguments, run the full scraper
    await runScraper(scraper);
  }
}