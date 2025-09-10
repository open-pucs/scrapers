import * as fs from "fs";
import * as path from "path";
import { RawGenericDocket, RawDocketWithJurisdiction } from "./types";
import { OPENSCRAPERS_INTERNAL_API_URL } from "./constants";

/**
 * Defines the contract for a scraper.
 */
export interface Scraper {
  state: string;
  jurisdiction_name: string;
  getCaseList: () => Promise<Partial<RawGenericDocket>[]>;
  getCaseDetails: (
    caseData: Partial<RawGenericDocket>,
    savepath_generator: (input: string) => string,
  ) => Promise<RawGenericDocket>;
}

/**
 * Saves a JSON object to S3 via the internal API.
 * @param key The S3 key (path) for the file.
 * @param data The JSON data to save.
 */
async function saveJsonToS3(key: string, data: any) {
  const url = `${OPENSCRAPERS_INTERNAL_API_URL}/admin/write_s3_json`;
  console.log(`Saving to S3 at key: ${key}`);
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, contents: data }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to save to S3: ${response.status} ${errorText}`);
  }
}

export async function processDocket(
  scraper: Scraper,
  basicCaseData: Partial<RawGenericDocket>,
  makeS3JsonSavePath: (path_loc: string) => string,
) {
  try {
    console.log(`Fetching details for case: ${basicCaseData.case_govid}`);
    const fullCaseData = await scraper.getCaseDetails(
      basicCaseData,
      makeS3JsonSavePath,
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
    console.log("Building submission payload");
    const payloadStr = JSON.stringify(payload, null, 2);
    // B

    // Write a .sh file with an equivalent curl command
    const curlScript = `#!/bin/bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '${payloadStr.replace(/'/g, "'\\''")}' \
  "${submitUrl}"
`;
    console.log("Wrote backup curl script.");

    fs.writeFileSync("debug_submit.sh", curlScript, { mode: 0o755 });

    // Actually do the fetch call
    const submitResponse = await fetch(submitUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payloadStr,
    });

    if (!submitResponse.ok) {
      const errorText = await submitResponse.text();
      throw new Error(
        `Failed to submit case: ${submitResponse.status} ${errorText}`,
      );
    }

    console.log(`Successfully submitted case: ${fullCaseData.case_govid}`);
  } catch (error) {
    console.error(
      `Error processing case: ${basicCaseData.case_govid}`,
      error,
    );
  }
}

/**
 * Runs the scraper, fetches all data, and sends it to the API.
 * @param scraper The scraper to run.
 */
export async function runScraper(scraper: Scraper) {
  console.log(`Running scraper for ${scraper.jurisdiction_name}`);

  const timeNow = new Date().toISOString();
  const basePath = path.join(
    "intermediates",
    scraper.state,
    scraper.jurisdiction_name,
  );
  const makeS3JsonSavePath = (path_loc: string) =>
    path.join(basePath, path_loc, `${timeNow}.json`);
  console.log(`Base path for intermediate files in S3: ${basePath}`);

  // 1. Get the list of all cases from the scraper
  const allCases = await scraper.getCaseList();
  console.log(`Found ${allCases.length} total cases from scraper.`);
  await saveJsonToS3(makeS3JsonSavePath("caselist_all"), allCases);

  // 2. Get the list of cases that need to be processed
  const diffUrl = `${OPENSCRAPERS_INTERNAL_API_URL}/public/caselist/${scraper.state}/${scraper.jurisdiction_name}/casedata_differential`;
  const diffResponse = await fetch(diffUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(allCases),
  });

  if (!diffResponse.ok) {
    const errorText = await diffResponse.text();
    throw new Error(
      `Failed to get case differential: ${diffResponse.status} ${errorText}`,
    );
  }

  const diffResult = await diffResponse.json();
  const casesToProcess: Partial<RawGenericDocket>[] =
    diffResult.to_process || [];
  console.log(
    `Found ${casesToProcess.length} cases to process after differential check.`,
  );
  await saveJsonToS3(makeS3JsonSavePath("caselist_differential"), diffResult);

  // 3. Process each case and submit it to the API
  for (const basicCaseData of casesToProcess) {
    await processDocket(scraper, basicCaseData, makeS3JsonSavePath);
  }

  console.log("Scraper run finished.");
}
