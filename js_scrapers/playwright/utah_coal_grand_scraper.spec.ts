import { chromium, Page, Browser, BrowserContext } from "playwright";
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
  context: BrowserContext,
  permitURL: string,
): Promise<any[]> {
  const page = await context.newPage();
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

function generateUtahUrls(): string[] {
  const urls: string[] = [];
  const baseUrl =
    "https://utahdnr.my.site.com/s/coal-document-display?tabType=Specific+Project&selectedRowId=";
  const permitName = "&selectedPermitName=";

  // a0B8z000000iHH{i...z}EAM
  for (let i = "i".charCodeAt(0); i <= "z".charCodeAt(0); i++) {
    const middleChar = String.fromCharCode(i);
    const rowId = `a0B8z000000iHH${middleChar}EAM`;
    urls.push(baseUrl + rowId + permitName);
  }

  // a0B8z000000iHI{0...9}EAM
  for (let i = 0; i <= 9; i++) {
    const rowId = `a0B8z000000iHI${i}EAM`;
    urls.push(baseUrl + rowId + permitName);
  }

  // a0B8z000000iHIAEA2 and a0B8z000000iHIBEA2
  urls.push(baseUrl + "a0B8z000000iHIAEA2" + permitName);
  urls.push(baseUrl + "a0B8z000000iHIBEA2" + permitName);

  return urls;
}

async function main() {
  fs.mkdirSync(out_directory, { recursive: true });

  const browser = await chromium.launch();
  const page = await browser.newPage();

  console.log("Step 1: Scraping all mines...");
  const allMines = await scrapeMines(page);
  console.log(`Found ${allMines.length} mines in total.`);
  await page.close();

  console.log("Step 2: Generating predefined URLs for filings...");
  const filingUrls = generateUtahUrls();
  console.log(`Generated ${filingUrls.length} URLs for filings.`);

  console.log("Step 3: Scraping filings from all URLs concurrently...");
  const allFilings: any[] = [];

  const concurrencyLimit = 10;
  const urlQueue = [...filingUrls];

  async function worker() {
    const context = await browser.newContext();
    try {
      while (urlQueue.length > 0) {
        const url = urlQueue.shift();
        if (url) {
          try {
            console.log(`Worker starting on URL ${url}`);
            const filings = await scrapeFilings(context, url);
            allFilings.push(...filings);
            console.log(
              `Finished scraping for URL ${url}. Found ${filings.length} filings.`,
            );
          } catch (error) {
            console.error(`Error scraping filings for URL ${url}:`, error);
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

  console.log(`Scraped a total of ${allFilings.length} filings.`);

  console.log("Step 4: Associating filings with mines...");
  for (const mine of allMines) {
    mine.filings = allFilings.filter(
      (filing) => filing.extra_metadata.permitID === mine.case_govid,
    );
  }

  console.log("Step 5: Saving all data to disk...");
  for (const mine of allMines) {
    fs.writeFileSync(
      `${out_directory}/${mine.case_govid}.json`,
      JSON.stringify(mine, null, 2),
    );
  }

  await browser.close();
  console.log("All done!");
}

main().catch(console.error);
