import { chromium, Page, Browser, BrowserContext } from "playwright";
import * as fs from "fs";

const out_directory = "outputs/utah_coal_mines";
// New instructions:
//
// So this old method isnt working great. I think the best method would be to restructure everything using an index system. So:
// Step 1: Go ahead and scrape the list of mines page.
// Step 2: For each mine go ahead and generate an index for each mine, specifically what page its on and what position its on the page.
// Step 3: Then spawn a new task that reloads the mine page, clikcs through until it encounters the page the mine is on, goes down to the row the mine is on, then clicks the view button that will navigate the website to the mine page:
//
//<th lwc-392cvb27u8q="" class="private-ssr-placeholder-class" role="rowheader" aria-readonly="true" scope="row" tabindex="0" data-label="View" data-col-key-value="0-button-icon-0"><lightning-primitive-cell-factory lwc-392cvb27u8q="" data-label="View" lwc-f1qthpifoh-host=""><span lwc-f1qthpifoh="" class="slds-grid slds-grid_align-center"><div lwc-f1qthpifoh="" class="private-ssr-placeholder-class"><lightning-primitive-cell-button lwc-f1qthpifoh="" data-navigation="enable" data-action-triggers="enter,space" tabindex="-1"><lightning-button-icon variant="border-filled" lwc-485vfn4rmof-host=""><button lwc-485vfn4rmof="" class="slds-button slds-button_icon slds-button_icon-border-filled" title="Preview" type="button" part="button button-icon"><lightning-primitive-icon lwc-485vfn4rmof="" exportparts="icon" variant="bare" lwc-1of0md8cufd-host=""><svg focusable="false" aria-hidden="true" viewBox="0 0 520 520" part="icon" lwc-1of0md8cufd="" data-key="enter" class="slds-button__icon"><g lwc-1of0md8cufd=""><path d="M440 305s1 16-15 16H152c-9 0-13-12-7-18l56-56c6-6 6-15 0-21l-21-21c-6-6-15-6-21 0L24 340c-6 6-6 15 0 21l136 135c6 6 15 6 21 0l21-21c6-6 6-15 0-21l-56-56c-6-7-2-17 7-17h332c7 0 15-8 15-16V35c0-7-7-15-15-15h-30c-8 0-15 8-15 15v270z" lwc-1of0md8cufd=""></path></g></svg></lightning-primitive-icon><span class="slds-assistive-text" lwc-485vfn4rmof="">SELECT</span></button></lightning-button-icon></lightning-primitive-cell-button></div></span></lightning-primitive-cell-factory></th>
//
// Step 4: Go ahead and scrape the mine page as normal having navigated to it successfully.

interface MineIndex {
  case_govid: string;
  case_name: string;
  petitioner: string;
  county: string;
  pageNumber: number;
  rowPosition: number;
}

async function scrapeMinesWithIndex(page: Page): Promise<MineIndex[]> {
  await page.goto("https://utahdnr.my.site.com/s/coal-document-display");
  await page.waitForLoadState("networkidle");

  const mineIndexes: MineIndex[] = [];
  let pageNumber = 0;

  while (true) {
    console.log(`Scraping page ${pageNumber} of mines for indexing...`);
    await page.waitForLoadState("networkidle");
    const rows = await page.locator("tbody tr").all();
    console.log(`Found ${rows.length} mines on page ${pageNumber}`);

    for (let rowIndex = 0; rowIndex < rows.length; rowIndex++) {
      const row = rows[rowIndex];
      const permitId = await row
        .locator('td[data-label="Permit ID"]')
        .innerText();
      const mineName = await row
        .locator('td[data-label="Mine Name"]')
        .innerText();
      const mineOperator = await row
        .locator('td[data-label="Owner"]')
        .innerText();
      const county = await row.locator('td[data-label="County"]').innerText();

      const mineIndex: MineIndex = {
        case_govid: permitId,
        case_name: mineName,
        petitioner: mineOperator,
        county: county,
        pageNumber: pageNumber,
        rowPosition: rowIndex,
      };
      mineIndexes.push(mineIndex);
    }

    try {
      await page
        .locator("lightning-button.slds-p-horizontal_x-small:nth-child(4)")
        .first()
        .click({ timeout: 5000 });
      pageNumber++;
    } catch (e) {
      console.log("No more mine pages. Finished indexing mines.");
      break;
    }
  }
  return mineIndexes;
}

async function navigateToMineAndScrape(
  context: BrowserContext,
  mineIndex: MineIndex,
): Promise<any> {
  const page = await context.newPage();
  try {
    console.log(
      `Navigating to mine ${mineIndex.case_govid} on page ${mineIndex.pageNumber}, row ${mineIndex.rowPosition}`,
    );

    await page.goto("https://utahdnr.my.site.com/s/coal-document-display");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);

    for (
      let currentPage = 0;
      currentPage < mineIndex.pageNumber;
      currentPage++
    ) {
      console.log(
        `Clicking to page ${currentPage + 1} to reach target page ${mineIndex.pageNumber}`,
      );
      await page
        .locator("lightning-button.slds-p-horizontal_x-small:nth-child(4)")
        .first()
        .click({ timeout: 5000 });
      await page.waitForLoadState("networkidle");
    }

    console.log(
      `Reached target page ${mineIndex.pageNumber}, looking for row ${mineIndex.rowPosition}`,
    );
    const rows = await page.locator("tbody tr").all();

    if (mineIndex.rowPosition >= rows.length) {
      throw new Error(
        `Row ${mineIndex.rowPosition} not found on page ${mineIndex.pageNumber}`,
      );
    }

    const targetRow = rows[mineIndex.rowPosition];
    const viewButton = targetRow.locator('th[data-label="View"] button');

    console.log(`Clicking view button for mine ${mineIndex.case_govid}`);
    await viewButton.click();
    await page.waitForLoadState("networkidle");
    // Wait an extra half a second to just make sure everything works.
    await page.waitForTimeout(500);

    const filings = await scrapeFilingsFromCurrentPage(
      page,
      mineIndex.case_govid,
    );

    // Validate that all filings have the correct permit ID
    const validFilings = filings.filter((filing) => {
      const filingPermitId = filing.extra_metadata?.permitID;
      if (filingPermitId !== mineIndex.case_govid) {
        console.warn(
          `Filtering out filing with mismatched permit ID. Expected: ${mineIndex.case_govid}, Found: ${filingPermitId}`,
        );
        return false;
      }
      return true;
    });

    console.log(
      `Mine ${mineIndex.case_govid}: ${validFilings.length}/${filings.length} filings passed permit ID validation`,
    );

    const caseData = {
      case_govid: mineIndex.case_govid,
      opened_date: null,
      case_name: mineIndex.case_name,
      case_url: page.url(),
      case_type: "",
      case_subtype: "",
      description: "",
      industry: "Coal",
      petitioner: mineIndex.petitioner,
      hearing_officer: "",
      closed_date: null,
      filings: validFilings,
      case_parties: [],
      extra_metadata: {
        county: mineIndex.county,
      },
    };

    return caseData;
  } catch (error) {
    console.error(`Error navigating to mine ${mineIndex.case_govid}:`, error);
    return null;
  } finally {
    await page.close();
  }
}

async function scrapeFilingsFromCurrentPage(
  page: Page,
  permitId: string,
): Promise<any[]> {
  const filings = [];
  let total_pages_so_far = 0;

  console.log(
    `Beginning the process of scraping filings for permit ${permitId}...`,
  );

  while (true) {
    await page.waitForLoadState("networkidle");
    const rows = await page
      .locator(".slds-table > tbody:nth-child(2) tr")
      .all();
    console.log(
      `Found ${rows.length} filings on page ${total_pages_so_far} for ${permitId}`,
    );

    for (const row of rows) {
      const docDate = await row
        .locator('td[data-label="Document Date"]')
        .innerText();
      const docFrom = await row
        .locator('td[data-label="Doc From"]')
        .innerText();
      const docTo = await row.locator('td[data-label="Doc To"]').innerText();
      const docRegarding = await row
        .locator('td[data-label="Doc Regarding"]')
        .innerText();

      // Validate that the filing has a valid date
      if (
        !docDate ||
        docDate.trim() === "" ||
        docDate === "undefined" ||
        docDate === "null"
      ) {
        console.warn(
          `Skipping filing for permit ${permitId} - no valid document date found`,
        );
        continue;
      }

      // Validate that the filing has a valid name/regarding
      if (
        !docRegarding ||
        docRegarding.trim() === "" ||
        docRegarding === "undefined" ||
        docRegarding === "null"
      ) {
        console.warn(
          `Skipping filing for permit ${permitId} - no valid document regarding found`,
        );
        continue;
      }

      const docLocation = "Incoming";
      const viewLink = "unknown";

      const filing = {
        filed_date: docDate.trim(),
        filling_govid: "",
        name: docRegarding.trim(),
        organization_author_blob: [docTo],
        individual_author_blob: [docFrom],
        filing_type: "",
        description: "",
        attachments: [
          {
            name: docRegarding.trim(),
            document_extension: "pdf",
            attachment_govid: "",
            url: viewLink,
            attachment_type: docLocation,
            attachment_subtype: "",
            extra_metadata: {
              permitID: permitId,
            },
            hash: null,
          },
        ],
        extra_metadata: {
          doc_location: docLocation,
          permitID: permitId,
        },
      };

      filings.push(filing);
    }

    try {
      await page
        .locator("lightning-button.slds-p-horizontal_x-small:nth-child(4)")
        .first()
        .click({ timeout: 5000 });
      total_pages_so_far += 1;
    } catch (e) {
      console.log(`No more filings pages for permit ${permitId}.`);
      break;
    }
  }

  return filings;
}

async function runTestingMode() {
  fs.mkdirSync(out_directory, { recursive: true });

  console.log("TESTING MODE: Running with headed browser...");
  const browser = await chromium.launch({ headless: false, slowMo: 500 });
  const page = await browser.newPage();

  console.log("Step 1: Scraping mines list to get random mine...");
  const mineIndexes = await scrapeMinesWithIndex(page);
  console.log(`Found ${mineIndexes.length} mines in total.`);
  await page.close();

  const randomIndex = Math.floor(Math.random() * mineIndexes.length);
  const selectedMine = mineIndexes[randomIndex];
  console.log(
    `TESTING MODE: Randomly selected mine ${selectedMine.case_govid} (${selectedMine.case_name}) from position ${randomIndex}`,
  );

  console.log("Step 2: Scraping the selected mine...");
  const context = await browser.newContext();
  const mineData = await navigateToMineAndScrape(context, selectedMine);
  await context.close();

  if (mineData) {
    console.log(
      `TESTING MODE: Successfully scraped mine ${mineData.case_govid}. Found ${mineData.filings.length} filings.`,
    );

    console.log("Step 3: Saving test data to disk...");
    fs.writeFileSync(
      `${out_directory}/test_${mineData.case_govid}.json`,
      JSON.stringify(mineData, null, 2),
    );
    console.log(
      `TESTING MODE: Saved test data to ${out_directory}/test_${mineData.case_govid}.json`,
    );
  } else {
    console.log("TESTING MODE: Failed to scrape the selected mine.");
  }

  await browser.close();
  console.log("TESTING MODE: Complete!");
}

async function runFullMode(concurrencyOverride: number | null = null) {
  fs.mkdirSync(out_directory, { recursive: true });

  const browser = await chromium.launch();
  const page = await browser.newPage();

  console.log("Step 1: Scraping mines list to generate index...");
  const mineIndexes = await scrapeMinesWithIndex(page);
  console.log(`Found ${mineIndexes.length} mines in total.`);
  await page.close();

  console.log(
    "Step 2: Navigating to each mine and scraping detailed data concurrently...",
  );
  const allMines: any[] = [];

  const concurrencyLimit = concurrencyOverride || 6;
  console.log(`Using concurrency limit: ${concurrencyLimit}`);
  const mineQueue = [...mineIndexes];

  async function worker() {
    const context = await browser.newContext();
    try {
      while (mineQueue.length > 0) {
        const mineIndex = mineQueue.shift();
        if (mineIndex) {
          try {
            console.log(`Worker starting on mine ${mineIndex.case_govid}`);
            const mineData = await navigateToMineAndScrape(context, mineIndex);
            if (mineData) {
              // Save the mine data immediately after scraping
              const filename = `${out_directory}/${mineData.case_govid}.json`;
              fs.writeFileSync(filename, JSON.stringify(mineData, null, 2));
              console.log(
                `Finished scraping mine ${mineIndex.case_govid}. Found ${mineData.filings.length} filings. Saved to ${filename}`,
              );
              allMines.push(mineData);
            }
          } catch (error) {
            console.error(
              `Error scraping mine ${mineIndex.case_govid}:`,
              error,
            );
          }
        }
      }
    } finally {
      await context.close();
    }
  }

  const workers = [];
  for (let i = 0; i < concurrencyLimit; i++) {
    workers.push(worker());
  }

  await Promise.all(workers);

  console.log(
    `Successfully scraped ${allMines.length} mines with their filings.`,
  );

  await browser.close();
  console.log("All done!");
}

async function main() {
  const args = process.argv.slice(2);
  const isTestingMode = args.includes("--testing");

  // Parse concurrency override flag
  let concurrencyOverride = null;
  const concurrencyFlagIndex = args.indexOf("--concurrency");
  if (concurrencyFlagIndex !== -1 && concurrencyFlagIndex + 1 < args.length) {
    const concurrencyValue = parseInt(args[concurrencyFlagIndex + 1], 10);
    if (!isNaN(concurrencyValue) && concurrencyValue > 0) {
      concurrencyOverride = concurrencyValue;
    } else {
      console.error("Invalid concurrency value. Must be a positive integer.");
      process.exit(1);
    }
  }

  if (isTestingMode) {
    await runTestingMode();
  } else {
    await runFullMode(concurrencyOverride);
  }
}

main().catch(console.error);
