import { Scraper, runScraper, processDocket } from "./pipeline";
import { RawGenericDocket } from "./types";
import * as path from "path";

/**
 * Processes a specific list of dockets for a given scraper.
 * @param scraper The scraper to use.
 * @param dockets The list of dockets to process.
 */
export async function runScraperForDockets(
  scraper: Scraper,
  dockets: Partial<RawGenericDocket>[],
) {
  console.log(
    `Running scraper for ${scraper.jurisdiction_name} for ${dockets.length} specific dockets.`,
  );

  const timeNow = new Date().toISOString();
  const basePath = path.join(
    "intermediates",
    scraper.state,
    scraper.jurisdiction_name,
  );
  const makeS3JsonSavePath = (path_loc: string) =>
    path.join(basePath, path_loc, `${timeNow}.json`);

  if (scraper.processTasksWithQueue && dockets.length > 1) {
    console.log(`Processing ${dockets.length} dockets in parallel`);
    await scraper.processTasksWithQueue(
      dockets,
      (basicCaseData) => processDocket(scraper, basicCaseData, makeS3JsonSavePath),
      4 // Default max concurrent
    );
  } else {
    // Fallback to sequential processing
    for (const basicCaseData of dockets) {
      await processDocket(scraper, basicCaseData, makeS3JsonSavePath);
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
        e,
      );
    }
  } else {
    // If there are no arguments, run the full scraper
    await runScraper(scraper);
  }
}
