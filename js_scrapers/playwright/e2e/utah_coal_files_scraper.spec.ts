import { test, expect } from "@playwright/test";
import * as fs from "fs";

test("Utah Coal Files Scraper", async ({ page }) => {
  // this function should be callable with a specific permit name like so:
  const permitID = "C0070001";
  const permitURL = `https://utahdnr.my.site.com/s/coal-document-display?tabType=Specific%20Project&selectedRowId=a0B8z000000iHHiEAM&selectedPermitName=${permitID}`;

  await page.goto(permitURL);
  await page.waitForLoadState("networkidle");

  const filings = [];

  while (true) {
    console.log("Starting a new page iteration");
    await page.waitForLoadState("networkidle");
    const rows = await page
      .locator(".slds-table > tbody:nth-child(2) tr")
      .all();
    console.log(`Found ${rows.length} rows on the page`);

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
      // const docLocation = await row
      //   .locator('td[data-label="Doc Location"]')
      //   .innerText();
      const docLocation = "Incoming";
      // const permitID = await row
      //   .locator('td[data-label="Permit ID"]')
      //   .innerText();
      // const viewLink = await row.locator("a").first().getAttribute("href");
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
              permitID: permitID,
            },
            hash: null,
          },
        ],
        extra_metadata: {
          doc_location: docLocation,
          permitID: permitID,
        },
      };

      filings.push(filing);
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

  console.log(`Scraped a total of ${filings.length} filings`);
  fs.writeFileSync(
    `cypress/fixtures/utah-coal-permit-${permitID}.json`,
    JSON.stringify(filings, null, 2),
  );
});
