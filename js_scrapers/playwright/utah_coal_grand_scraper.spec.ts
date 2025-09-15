import { test, expect, chromium, Page, Browser } from "@playwright";
import * as fs from "fs";

const out_directory = "outputs/utah_coal_mines";
// So we have a problem, the selectedPermitName of a mine doesnt actually change what id that mine extracts from.
// secret iteration patterns, take the url:
// https://ogm.utah.gov/coal-files/?tabType=Specific+Project&selectedRowId=a0B8z000000iHHiEAM&selectedPermitName=
// Specifically this selectedRoaId and iterate the middle number i through z
// a0B8z000000iHH{i...z}EAM
// then take this id
// a0B8z000000iHI{0...9}EAM
//
//
// a0B8z000000iHIAEA2
// and
// a0B8z000000iHIBEA2
//
// So what you should do is scrape the files for these urls first. Then scrape all the mines. Then associate each of the mines with the list of permits for each mine, then save it to disk. (This should be done as soon as the fillings for each well are finished being downloaded.) Also I dont think parallelism for this thing is fully working. It should spawn a seperate new browser tab for each of the filling operations that need to happen.

async function scrapeMines(page: Page): Promise<any[]> {
  await page.goto("https://utahdnr.my.site.com/s/coal-document-display");
  await page.waitForLoadState("networkidle");

  const cases = [];

  while (true) {
    console.log("Scraping a page of mines...");
    await page.waitForLoadState("networkidle");
    const rows = await page.locator("tbody tr").all();
    console.log(`Found ${rows.length} mines on the page`);

    for (const row of rows) {
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

      const caseData = {
        case_govid: permitId,
        opened_date: null,
        case_name: mineName,
        case_url: `https://ogm.utah.gov/coal-files/?tabType=Specific+Project&selectedRowId=a0B8z000000iHHjEAM&selectedPermitName=${permitId}`,
        case_type: "",
        case_subtype: "",
        description: "",
        industry: "Coal",
        petitioner: mineOperator,
        hearing_officer: "",
        closed_date: null,
        filings: [],
        case_parties: [],
        extra_metadata: {
          county: county,
        },
      };
      cases.push(caseData);
    }

    try {
      await page
        .locator("lightning-button.slds-p-horizontal_x-small:nth-child(4)")
        .first()
        .click({ timeout: 5000 });
    } catch (e) {
      console.log("No more mine pages. Finished scraping mines.");
      break;
    }
  }
  return cases;
}

async function scrapeFilings(
  browser: Browser,
  permitURL: string,
): Promise<any[]> {
  const page = await browser.newPage();
  const filings = [];
  let permitIDGlobal = "";
  try {
    await page.goto(permitURL);
    await page.waitForLoadState("networkidle");

    console.log(
      `Beginning the process of scraping filings for permit ${permitURL}...`,
    );
    let total_pages_so_far = 0;
    while (true) {
      await page.waitForLoadState("networkidle");
      const rows = await page
        .locator(".slds-table > tbody:nth-child(2) tr")
        .all();
      console.log(
        `Found ${rows.length} filings on the ${total_pages_so_far} page of fillings for ${permitURL}`,
      );

      for (const row of rows) {
        const permitIDLocal = await row
          .locator('td[data-label="Permit"]')
          .innerText();
        if (!permitIDGlobal) {
          permitIDGlobal = permitIDLocal;
        }
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
        // These dont work, ignoring.
        // const docLocation = await row
        //   .locator('td[data-label="Doc Location"]')
        //   .innerText();
        // const viewLink = await row.locator("a").first().getAttribute("href");
        const docLocation = "Incoming";
        const viewLink = "unknown";

        const filing = {
          filed_date: docDate,
          filling_govid: "",
          name: docRegarding,
          organization_author_blob: [docTo],
          individual_author_blob: [docFrom],
          filing_type: "",
          description: "",
          attachments: [
            {
              name: docRegarding,
              document_extension: "pdf",
              attachment_govid: "",
              url: viewLink,
              attachment_type: docLocation,
              attachment_subtype: "",
              extra_metadata: {
                permitID: permitIDLocal,
              },
              hash: null,
            },
          ],
          extra_metadata: {
            doc_location: docLocation,
            permitID: permitIDLocal,
          },
        };

        filings.push(filing);
      }

      try {
        await page
          .locator("lightning-button.slds-p-horizontal_x-small:nth-child(4)")
          .first()
          .click({ timeout: 5000 });
      } catch (e) {
        console.log(`No more filings pages for permit ${permitIDGlobal}.`);
        break;
      }
      total_pages_so_far += 1;
    }
  } catch (error) {
    console.error(
      `An error occurred while scraping filings for permit ${permitIDGlobal}:`,
      error,
    );
  } finally {
    console.log(`Finally finished processing fillings for ${permitIDGlobal}`);
    await page.close();
    return filings;
  }
}

test("Grand Utah Coal Scraper", async ({ page }) => {
  test.setTimeout(0);
  fs.mkdirSync(out_directory, { recursive: true });

  console.log("Step 1: Scraping all mines...");
  const allMines = await scrapeMines(page);
  console.log(`Found ${allMines.length} mines in total.`);

  console.log("Step 2: Scraping filings for each mine concurrently...");

  const browser = await chromium.launch();
  const concurrencyLimit = 10;
  const mineQueue = [...allMines];

  async function worker() {
    while (mineQueue.length > 0) {
      const mine = mineQueue.shift();
      if (mine) {
        try {
          console.log(`Worker starting on permit ${mine.case_govid}`);
          const filings = await scrapeFilings(browser, mine.case_govid);
          mine.filings = filings;
          console.log(
            `Finished scraping for permit ${mine.case_govid}. Found ${filings.length} filings.`,
          );
        } catch (error) {
          console.error(
            `Error scraping filings for permit ${mine.case_govid}:`,
            error,
          );
          mine.filings = [];
        }
      }
    }
  }

  const workers = [];
  for (let i = 0; i < concurrencyLimit; i++) {
    workers.push(worker());
  }

  await Promise.all(workers);
  await browser.close();

  console.log("Step 3: Saving all data to disk...");
  for (const mine of allMines) {
    fs.writeFileSync(
      `${out_directory}/${mine.case_govid}.json`,
      JSON.stringify(mine, null, 2),
    );
  }
  console.log("All done!");
});

