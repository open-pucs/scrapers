import { test, Page } from "@playwright/test";
import { Scraper, runScraper } from "../pipeline";
import { GenericCase, GenericFiling } from "../types";

class NyPucScraper implements Scraper {
  state = "ny";
  jurisdiction_name = "ny_puc";
  page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async getCaseList(): Promise<Partial<GenericCase>[]> {
    await this.page.goto(
      "https://documents.dps.ny.gov/public/MatterManagement/CaseMaster.aspx",
    );
    await this.page.waitForLoadState("networkidle");

    // Click search to get all cases
    await this.page.locator('input[name="btnSearch"]').click();
    await this.page.waitForLoadState("networkidle");

    const cases: Partial<GenericCase>[] = [];
    let caseListPage = 1;

    while (true) {
      console.log(`Scraping case list page ${caseListPage}`);
      await this.page.waitForLoadState("networkidle");
      const rows = await this.page
        .locator("#grdCaseMaster tr.gridrow, #grdCaseMaster tr.gridaltrow")
        .all();
      console.log(`Found ${rows.length} rows on the page`);

      for (const row of rows) {
        const cells = await row.locator("td").all();
        const caseNumber = await cells[1].innerText();
        const caseTitle = await cells[2].innerText();
        const dateFiled = await cells[3].innerText();

        const caseData: Partial<GenericCase> = {
          case_govid: caseNumber,
          opened_date: new Date(dateFiled).toISOString(),
          case_name: caseTitle,
          case_url: `https://documents.dps.ny.gov/public/MatterManagement/CaseMaster.aspx?CaseNumber=${caseNumber}`,
        };
        cases.push(caseData);
      }

      const pagerButtons = await this.page
        .locator("#grdCaseMaster_pg td a")
        .all();
      if (pagerButtons.length > 1) {
        const nextButton = pagerButtons[pagerButtons.length - 1];
        const nextButtonText = await nextButton.innerText();
        if (nextButtonText === ">") {
          console.log("Clicking next button for case list");
          await nextButton.click({ timeout: 5000 });
          caseListPage++;
        } else {
          console.log("No next button found, assuming last page of cases.");
          break;
        }
      } else {
        console.log("No pagination for cases found.");
        break;
      }
    }
    return cases;
  }

  async getCaseDetails(
    caseData: Partial<GenericCase>,
    savepath_generator: (input: string) => string,
  ): Promise<GenericCase> {
    if (!caseData.case_url) {
      throw new Error("Case URL is missing");
    }

    await this.page.goto(caseData.case_url);
    await this.page.waitForLoadState("networkidle");

    const caseDocuments = await this.scrapeDocuments(
      "#MainContent_grdCaseDocuments",
    );

    const fullCaseData: GenericCase = {
      ...caseData,
      case_type: "",
      case_subtype: "",
      description: "",
      industry: "",
      petitioner: "",
      hearing_officer: "",
      closed_date: null,
      filings: [...caseDocuments],
      case_parties: [],
      extra_metadata: {},
    } as GenericCase;

    return fullCaseData;
  }

  private async scrapeDocuments(
    tableSelector: string,
  ): Promise<GenericFiling[]> {
    const documents: GenericFiling[] = [];
    while (true) {
      await this.page.waitForLoadState("networkidle");
      const docRows = await this.page
        .locator(`${tableSelector} tr.gridrow, ${tableSelector} tr.gridaltrow`)
        .all();

      for (const docRow of docRows) {
        const docCells = await docRow.locator("td").all();
        if (docCells.length > 3) {
          const documentTitle = await docCells[0].innerText();
          const documentType = await docCells[1].innerText();
          const dateFiled = await docCells[2].innerText();
          const fileUrl = await docCells[3].locator("a").getAttribute("href");

          documents.push({
            name: documentTitle,
            filed_date: new Date(dateFiled).toISOString(),
            organization_authors: [],
            individual_authors: [],
            filing_type: documentType,
            description: "",
            attachments: fileUrl
              ? [
                  {
                    name: documentTitle,
                    document_extension: fileUrl.split(".").pop() || "",
                    url: new URL(fileUrl, this.page.url()).toString(),
                    attachment_type: "primary",
                    attachment_subtype: "",
                    extra_metadata: {},
                  },
                ]
              : [],
            extra_metadata: {},
          });
        }
      }

      const pagerButtons = await this.page
        .locator(`${tableSelector}_pg td a`)
        .all();
      if (pagerButtons.length > 1) {
        const nextButton = pagerButtons[pagerButtons.length - 1];
        const nextButtonText = await nextButton.innerText();
        if (nextButtonText === ">") {
          console.log("Clicking next button for documents");
          await nextButton.click({ timeout: 5000 });
        } else {
          break;
        }
      } else {
        break;
      }
    }
    return documents;
  }
}

test("Run New York PUC Scraper", async ({ page }) => {
  const scraper = new NyPucScraper(page);
  await runScraper(scraper);
});
