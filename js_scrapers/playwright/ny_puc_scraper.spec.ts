import { Scraper } from "../pipeline";
import {
  RawGenericDocket,
  RawGenericFiling,
  RawGenericParty,
  RawArtificalPersonType,
} from "../types";
import { Page, context } from "playwright";
import { Browser, chromium } from "playwright";
import { runCli } from "../cli_runner";
import * as cheerio from "cheerio";

class NyPucScraper implements Scraper {
  state = "ny";
  jurisdiction_name = "ny_puc";
  page: Page;
  context: any;

  constructor(page: Page, context: any ) {
    this.page = page;
    this.context = context;
  }

  async getPage(url: string): Promise<any> {
    await this.page.goto(url);
    await this.page.waitForLoadState("networkidle");

    console.log(`Getting page content at ${url}...`);
    const html = await this.page.content();
    const $ = cheerio.load(html);
    return $;
  }
  async getCasePage(gov_id: string): Promise<any> {
    const url = `https://documents.dps.ny.gov/public/MatterManagement/CaseMaster.aspx?MatterCaseNo=${gov_id}`;
    const page = await this.getPage(url);
    return page;
  }

  async getCaseMeta(gov_id: string, $?: any): Promise<Partial<RawGenericDocket>> {
    // get main page
    // get metadata
    if ($ !== undefined) {
      
    }
  }

  async GetCaseDocument(gov_id: string, sr_no: string, $?: any) {
    if ($ === undefined) {
      $ = await this.getCasePage(gov_id);
      const url = `https://documents.dps.ny.gov/public/MatterManagement/CaseMaster.aspx?MatterCaseNo=${gov_id}`;
    }
  }

  async getDateCases(dateString: string): Promise<Partial<RawGenericDocket>[]> {
    // eg dateString = 09/09/2025
    const url = `https://documents.dps.ny.gov/public/Common/SearchResults.aspx?MC=1&IA=&MT=&MST=&CN=&SDT=${dateString}&SDF=${dateString}&C=&M=&CO=0`;
    console.log(`getting cases for date ${dateString}`);
    const cases: Partial<RawGenericDocket>[] = await this.getCasesAt(url);
    return cases;
  }
  async getDateCaseDocuments(
    dateString: string
  ): Promise<Partial<RawGenericDocket>[]> {
    // this would actually get both the new case and its openning documents in
    // one swoop
    // eg dateString = 09/09/2025
    const url = `https://documents.dps.ny.gov/public/Common/SearchResults.aspx?MC=0&IA=&MT=&MST=&CN=&SDT=9${dateString}&SDF=9${dateString}&C=&M=&CO=0&DFF=${dateString}&DFT=${dateString}&DT=&CI=0&FC=`;
    console.log(`getting cases for date ${dateString}`);
    const cases: Partial<RawGenericDocket>[] = await this.getCasesAt(url);
    return cases;
  }

  async getRows($: any) {
    return $("#tblSearchedMatterExternal > tbody tr");
  }

  async getCasesAt(url: string): Promise<Partial<RawGenericDocket>[]> {
    const cases: Partial<RawGenericDocket>[] = [];
    console.log(`Navigating to ${url}`);
    const $ = await this.getPage(url);

    console.log("Extracting industry affected...");
    const industry_affected = $("#GridPlaceHolder_lblSearchCriteriaValue")
      .text()
      .replace("Industry Affected:", "");
    console.log(`Industry affected: ${industry_affected}`);

    console.log("Extracting rows from the table...");
    const rows = await this.getRows($);
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
    return cases;
  }

  async getCaseList(): Promise<Partial<RawGenericDocket>[]> {
    const cases: Partial<RawGenericDocket>[] = [];
    for (const industry_number of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) {
      console.log(`Processing industry index: ${industry_number}`);
      const industry_url = `https://documents.dps.ny.gov/public/Common/SearchResults.aspx?MC=1&IA=${industry_number}`;
      const c = await this.getCasesAt(industry_url);
      cases.push(...c);
    }
    return cases;
  }

  async getCaseDetails(
    caseData: Partial<RawGenericDocket>
  ): Promise<RawGenericDocket> {
    if (!caseData.case_url) {
      throw new Error("Case URL is missing");
    }

    await this.page.goto(caseData.case_url);
    await this.page.waitForLoadState("networkidle");

    // wait up to 10s for documents table, otherwise just continue
    const docsTableSelector = "#tblPubDoc > tbody";
    try {
      await this.page.waitForSelector(docsTableSelector, {
        timeout: 30_000,
      });
    } catch {}

    const documentsHtml = await this.page.content();
    const caseDocuments = await this.scrapeDocumentsFromHtml(
      documentsHtml,
      docsTableSelector
    );

    const partiesButtonSelector = "#GridPlaceHolder_lbtContact";
    await this.page.click(partiesButtonSelector);
    await this.page.waitForLoadState("networkidle");

    const partiesTableSelector = 'select[name="tblActiveParty_length"]';
    await this.page.selectOption(partiesTableSelector, "-1");
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
    html: string
  ): Promise<RawGenericParty[]> {
    const $ = cheerio.load(html);
    const parties: RawGenericParty[] = [];
    const rows = $("#grdParty tr.gridrow, #grdParty tr.gridaltrow");
    console.log(`Found ${rows.length} party rows.`);

    rows.each((i, row) => {
      const cells = $(row).find("td");
      const nameCell = $(cells[1]).text();
      const emailPhoneCell = $(cells[4]).text();
      const addressCell = $(cells[3]).text();
      const companyCell = $(cells[2]).text();

      const nameParts = nameCell.split("\n");
      const fullName = nameParts[0];
      const title = nameParts.length > 1 ? nameParts[1] : "";

      const emailPhoneParts = emailPhoneCell.split("\n");
      const email = emailPhoneParts.find((part) => part.includes("@")) || "";
      const phone =
        emailPhoneParts.find((part) => part.startsWith("Ph:")) || "";

      const party: RawGenericParty = {
        name: fullName,
        artifical_person_type: RawArtificalPersonType.Human,
        western_human_last_name: fullName.split(" ")[0] || "",
        western_human_first_name: fullName.split(" ").slice(1).join(" ") || "",
        human_title: title,
        human_associated_company: companyCell,
        contact_email: email,
        contact_phone: phone,
        contact_address: addressCell,
      };
      parties.push(party);
    });

    return parties;
  }

  private async scrapeDocumentsFromHtml(
    html: string,
    tableSelector: string
  ): Promise<RawGenericFiling[]> {
    console.log("Starting document extraction from HTML...");
    const $ = cheerio.load(html);
    const filingsMap = new Map<string, RawGenericFiling>();
    const docRows = $(`${tableSelector} tr`);

    console.log(`Found ${docRows.length} document rows.`);

    docRows.each((i, docRow) => {
      const docCells = $(docRow).find("td");
      if (docCells.length > 6) {
        const filingNo = $(docCells[5]).text().trim();
        if (!filingNo) return;

        const documentTitle = $(docCells[3]).find("a").text().trim();
        const attachmentUrl = $(docCells[3]).find("a").attr("href");
        const fileName = $(docCells[6]).text().trim();

        if (!filingsMap.has(filingNo)) {
          const documentType = $(docCells[2]).text().trim();
          const dateFiled = $(docCells[1]).text().trim();
          const authors = $(docCells[4]).text().trim();

          filingsMap.set(filingNo, {
            name: documentTitle,
            filed_date: new Date(dateFiled).toISOString(),
            organization_authors: [],
            individual_authors: [],
            organization_authors_blob: authors,
            individual_authors_blob: "",
            filing_type: documentType,
            description: "",
            attachments: [],
            extra_metadata: { fileName },
            filling_govid: filingNo,
          });
        }

        const filing = filingsMap.get(filingNo);
        if (filing && attachmentUrl) {
          filing.attachments.push({
            name: documentTitle,
            document_extension: fileName.split(".").pop() || "",
            url: new URL(
              attachmentUrl.replace(
                "../",
                "https://documents.dps.ny.gov/public/"
              ),
              this.page.url()
            ).toString(),
            attachment_type: "primary",
            attachment_subtype: "",
            extra_metadata: { fileName },
            attachment_govid: "",
          });
        }
      }
    });

    console.log("Finished document extraction.");
    return Array.from(filingsMap.values());
  }
}

async function main() {
  let browser: Browser | null = null;
  try {
    browser = await chromium.launch();
    const context = await browser.newContext();
    const scraper = new NyPucScraper(context, context);
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
