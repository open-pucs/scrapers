import { Scraper } from "../pipeline";
import {
  RawGenericDocket,
  RawGenericFiling,
  RawGenericParty,
  RawArtificalPersonType,
} from "../types";
import { Page } from "playwright";
import { Browser, chromium } from "playwright";
import { runCli } from "../cli_runner";
import * as cheerio from "cheerio";

class NyPucScraper implements Scraper {
  state = "ny";
  jurisdiction_name = "ny_puc";
  page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async getCaseList(): Promise<Partial<RawGenericDocket>[]> {
    const cases: Partial<RawGenericDocket>[] = [];
    for (const industry_number of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) {
      console.log(`Processing industry index: ${industry_number}`);
      const industry_url = `https://documents.dps.ny.gov/public/Common/SearchResults.aspx?MC=1&IA=${industry_number}`;
      console.log(`Navigating to ${industry_url}`);
      await this.page.goto(industry_url);
      await this.page.waitForLoadState("networkidle");

      console.log("Getting page content...");
      const html = await this.page.content();
      const $ = cheerio.load(html);

      console.log("Extracting industry affected...");
      const industry_affected = $("#GridPlaceHolder_lblSearchCriteriaValue")
        .text()
        .replace("Industry Affected:", "");
      console.log(`Industry affected: ${industry_affected}`);

      console.log("Extracting rows from the table...");
      const rows = $("#tblSearchedMatterExternal > tbody tr");
      console.log(`Found ${rows.length} rows.`);

      rows.each((i, row) => {
        const cells = $(row).find("td");
        if (cells.length >= 6) {
          console.log("Extracting case data from row...");
          const case_govid = $(cells[0]).find("a").text();
          const case_url = `https://documents.dps.ny.gov/public/MatterManagement/CaseMaster.aspx?MatterCaseNo=${case_govid}`;
          const matter_type = $(cells[1]).text();
          const matter_subtype = $(cells[2]).text();
          const opened_date = $(cells[3]).text();
          const case_name = $(cells[4]).text();
          const petitioner = $(cells[5]).text();

          const caseData: Partial<RawGenericDocket> = {
            case_govid,
            case_url,
            case_name,
            opened_date: new Date(opened_date).toISOString(),
            case_type: `${matter_type} - ${matter_subtype}`,
            petitioner,
            industry: industry_affected,
          };
          cases.push(caseData);
          console.log(`Successfully extracted case: ${case_govid}`);
        }
      });
    }
    return cases;
  }

  async getCaseDetails(
    caseData: Partial<RawGenericDocket>,
  ): Promise<RawGenericDocket> {
    if (!caseData.case_url) {
      throw new Error("Case URL is missing");
    }

    await this.page.goto(caseData.case_url);
    await this.page.waitForLoadState("networkidle");

    const documentsHtml = await this.page.content();
    const caseDocuments = await this.scrapeDocumentsFromHtml(
      documentsHtml,
      "#MainContent_grdCaseDocuments",
    );

    await this.page.locator("#GridPlaceHolder_lbtContact").click();
    await this.page.waitForLoadState("networkidle");

    const partiesHtml = await this.page.content();
    const caseParties = await this.scrapePartiesFromHtml(partiesHtml);

    const fullCaseData: RawGenericDocket = {
      ...caseData,
      case_type: "",
      case_subtype: "",
      description: "",
      industry: "",
      petitioner: "",
      hearing_officer: "",
      closed_date: null,
      filings: [...caseDocuments],
      case_parties: caseParties,
      extra_metadata: {},
      indexed_at: new Date().toISOString(),
    } as RawGenericDocket;

    return fullCaseData;
  }

  private async scrapePartiesFromHtml(
    html: string,
  ): Promise<RawGenericParty[]> {
    const $ = cheerio.load(html);
    const parties: RawGenericParty[] = [];
    const rows = $("#grdParty tr.gridrow, #grdParty tr.gridaltrow");

    rows.each((i, row) => {
      const cells = $(row).find("td");
      const nameCell = $(cells[1]).text();
      const emailPhoneCell = $(cells[4]).text();

      const nameParts = nameCell.split("\n");
      const fullName = nameParts[0];
      const title = nameParts.length > 1 ? nameParts[1] : "";
      const company = nameParts.length > 2 ? nameParts[2] : "";

      const emailPhoneParts = emailPhoneCell.split("\n");
      const email = emailPhoneParts.find((part) => part.includes("@")) || "";
      const phone =
        emailPhoneParts.find((part) => part.startsWith("Ph:")) || "";

      const isOrganization =
        company.includes("Inc.") ||
        company.includes("LLC") ||
        company.includes("Corp.");

      const party: RawGenericParty = {
        name: fullName,
        artifical_person_type: isOrganization
          ? RawArtificalPersonType.Organization
          : RawArtificalPersonType.Human,
        western_human_first_name: !isOrganization ? fullName.split(" ")[0] : "",
        western_human_last_name: !isOrganization
          ? fullName.split(" ").slice(1).join(" ")
          : "",
        human_title: title,
        human_associated_company: company,
        contact_email: email,
        contact_phone: phone,
      };
      parties.push(party);
    });

    return parties;
  }

  private async scrapeDocumentsFromHtml(
    html: string,
    tableSelector: string,
  ): Promise<RawGenericFiling[]> {
    console.log("Starting document extraction from HTML...");
    const $ = cheerio.load(html);
    const documents: RawGenericFiling[] = [];
    const docRows = $(`${tableSelector} tr.gridrow, ${tableSelector} tr.gridaltrow`);
    console.log(`Found ${docRows.length} document rows.`);

    docRows.each((i, docRow) => {
      const docCells = $(docRow).find("td");
      if (docCells.length > 3) {
        const documentTitle = $(docCells[3]).find("a").text();
        console.log(`Extracting document: ${documentTitle}`);
        const documentType = $(docCells[2]).text();
        const dateFiled = $(docCells[1]).text();
        const attachmentUrl = $(docCells[3]).find("a").attr("href");
        const authors = $(docCells[4]).text();

        documents.push({
          name: documentTitle,
          filed_date: new Date(dateFiled).toISOString(),
          organization_authors: [],
          individual_authors: [],
          organization_authors_blob: authors,
          individual_authors_blob: "",
          filing_type: documentType,
          description: "",
          attachments: attachmentUrl
            ? [
                {
                  name: documentTitle,
                  document_extension: attachmentUrl.split(".").pop() || "",
                  url: new URL(attachmentUrl, this.page.url()).toString(),
                  attachment_type: "primary",
                  attachment_subtype: "",
                  extra_metadata: {},
                  attachment_govid: "",
                },
              ]
            : [],
          extra_metadata: {},
          filling_govid: "",
        });
      }
    });
    console.log("Finished document extraction.");
    return documents;
  }
}

async function main() {
  let browser: Browser | null = null;
  try {
    browser = await chromium.launch();
    const context = await browser.newContext();
    const page = await context.newPage();
    const scraper = new NyPucScraper(page);
    await runCli(scraper);
  } catch (error) {
    console.error("Scraper failed:", error);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

main();
