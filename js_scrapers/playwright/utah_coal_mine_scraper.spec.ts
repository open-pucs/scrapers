import { test, expect } from "@playwright/test";
import * as fs from "fs";

test("Utah Coal Scraper", async ({ page }) => {
  const out_directory = "outputs/utah_coal_mines";
  fs.mkdirSync(out_directory, { recursive: true });
  await page.goto("https://utahdnr.my.site.com/s/coal-document-display");
  await page.waitForLoadState("networkidle");

  const cases = [];

  while (true) {
    console.log("Starting a new page iteration");
    await page.waitForLoadState("networkidle");
    const rows = await page.locator("tbody tr").all();
    console.log(`Found ${rows.length} rows on the page`);

    for (const row of rows) {
      const permitId = await row
        .locator('td[data-label="Permit ID"]')
        .innerText();
      console.log(`Permit ID: ${permitId}`);
      const mineName = await row
        .locator('td[data-label="Mine Name"]')
        .innerText();
      console.log(`Mine Name: ${mineName}`);
      const mineOperator = await row
        .locator('td[data-label="Owner"]')
        .innerText();
      console.log(`Operator: ${mineOperator}`);
      const county = await row.locator('td[data-label="County"]').innerText();
      console.log(`County: ${county}`);

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
      console.log("Clicking next button");
      await page
        .locator("lightning-button.slds-p-horizontal_x-small:nth-child(4)")
        .first()
        .click({ timeout: 5000 });
    } catch (e) {
      console.log("Next button not available, assuming last page.");
      break;
    }
  }

  console.log(`Scraped a total of ${cases.length} cases`);
  for (const caseData of cases) {
    fs.writeFileSync(
      `${out_directory}/${caseData.case_govid}.json`,
      JSON.stringify(caseData, null, 2),
    );
  }
});
