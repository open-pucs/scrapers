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
import * as fs from "fs";

enum ScrapingMode {
  FULL = "full",
  METADATA = "meta",
  DOCUMENTS = "docs",
  PARTIES = "parties",
  DATES = "dates",
  FULL_EXTRACTION = "full-extraction",
  FILINGS_BETWEEN_DATES = "filings-between-dates",
}

interface ScrapingOptions {
  mode: ScrapingMode;
  govIds?: string[];
  dateString?: string;
  beginDate?: string;
  endDate?: string;
  fromFile?: string;
  outFile?: string;
}

class NyPucScraper implements Scraper {
  state = "ny";
  jurisdiction_name = "ny_puc";
  context: any;
  browser: Browser;
  rootPage: Page;
  max_tabs: number = 10;
  max_concurrent_browsers: number = 4;
  pageCache: Record<string, any> = {};
  urlTable: Record<string, string> = {};

  constructor(page: Page, context: any, browser: Browser) {
    this.rootPage = page;
    this.context = context;
    this.browser = browser;
  }

  pages(): any {
    return this.context.pages;
  }

  async newTab(): Promise<any> {
    const page = await this.context.newPage();
    return page;
  }

  async newWindow(): Promise<{ context: any; page: any }> {
    const context = await this.browser.newContext();
    const page = await context.newPage();
    return { context, page };
  }

  async processTasksWithQueue<T, R>(
    tasks: T[],
    taskProcessor: (task: T) => Promise<R>,
    maxConcurrent: number = this.max_concurrent_browsers,
  ): Promise<R[]> {
    return new Promise((resolve, reject) => {
      const results: R[] = [];
      const errors: Error[] = [];
      let currentIndex = 0;
      let completed = 0;
      let running = 0;

      const processNext = async () => {
        if (currentIndex >= tasks.length) return;
        if (running >= maxConcurrent) return;

        const taskIndex = currentIndex++;
        const task = tasks[taskIndex];
        running++;

        console.log(
          `Starting task ${taskIndex + 1}/${tasks.length} (${running} running, max: ${maxConcurrent})`,
        );

        try {
          const result = await taskProcessor(task);
          results[taskIndex] = result;
        } catch (error) {
          console.error(`Task ${taskIndex + 1} failed:`, error);
          errors.push(error as Error);
          results[taskIndex] = null as any; // Placeholder for failed result
        } finally {
          running--;
          completed++;
          console.log(
            `Completed task ${taskIndex + 1}/${tasks.length} (${running} still running)`,
          );

          if (completed === tasks.length) {
            if (errors.length > 0) {
              console.warn(
                `${errors.length} tasks failed, but continuing with successful results`,
              );
            }
            resolve(results.filter((r) => r !== null));
          } else {
            // Start more tasks
            while (running < maxConcurrent && currentIndex < tasks.length) {
              processNext();
            }
          }
        }
      };

      // Start initial batch of tasks
      const initialBatch = Math.min(maxConcurrent, tasks.length);
      for (let i = 0; i < initialBatch; i++) {
        processNext();
      }
    });
  }

  async getPage(url: string): Promise<any> {
    this.urlTable[url] = url;
    const cached = this.pageCache[url];
    if (cached !== undefined) {
      return cached;
    }
    const { context, page } = await this.newWindow();
    await page.goto(url);
    await page.waitForLoadState("networkidle");
    console.log(`Getting page content at ${url}...`);
    const html = await page.content();

    const $ = cheerio.load(html);
    this.pageCache[url] = $;
    page.url();
    await context.close();
    return $;
  }
  async getCaseTitle(matter_seq: string): Promise<string> {
    const url = `https://documents.dps.ny.gov/public/MatterManagement/ExpandTitle.aspx?MatterSeq=${matter_seq}`;
    const $ = await this.getPage(url);
    return $("$txtTitle");
  }

  async getCasePage(gov_id: string): Promise<any> {
    const url = `https://documents.dps.ny.gov/public/MatterManagement/CaseMaster.aspx?MatterCaseNo=${gov_id}`;
    const page = await this.getPage(url);
    return page;
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
    dateString: string,
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
    let industry_affected = $("#GridPlaceHolder_lblSearchCriteriaValue")
      .text()
      .trim();

    if (industry_affected.startsWith("Industry Affected:")) {
      industry_affected = industry_affected
        .replace("Industry Affected:", "")
        .trim();
    } else {
      industry_affected = "Unknown";
    }

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
          case_type: matter_type,
          case_subtype: matter_subtype,
          petitioner,
          industry: industry_affected,
        };
        cases.push(caseData);
        console.log(`Successfully extracted case: ${case_govid}`);
      }
    });
    return cases;
  }

  // gets ALL cases
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

  async getCaseMeta(
    gov_id: string,
    $?: any,
  ): Promise<Partial<RawGenericDocket>> {
    // get main page
    const url = `https://documents.dps.ny.gov/public/Common/SearchResults.aspx?MC=1&IA=&MT=&MST=&CN=&MNO=${gov_id}&CO=0&C=&M=&CO=0`;
    console.log(`getting cases metadata for date ${gov_id}`);
    const cases: Partial<RawGenericDocket>[] = await this.getCasesAt(url);
    return cases[0];
  }

  async getCaseDetails(
    caseData: Partial<RawGenericDocket>,
  ): Promise<RawGenericDocket> {
    if (!caseData.case_url) {
      throw new Error("Case URL is missing");
    }
    const { context, page } = await this.newWindow();

    try {
      await page.goto(caseData.case_url);
      await page.waitForLoadState("networkidle");

      // wait up to 10s for documents table, otherwise just continue
      const docsTableSelector = "#tblPubDoc > tbody";
      try {
        await page.waitForSelector(docsTableSelector, {
          timeout: 30_000,
        });
      } catch {
        console.log("Waited 30 seconds and could not find documents table.");
      }

      const documentsHtml = await page.content();
      const url = page.url();

      // get case docs
      const caseDocuments = await this.scrapeDocumentsFromHtml(
        documentsHtml,
        docsTableSelector,
        url,
      );

      // get parties
      const partiesButtonSelector = "#GridPlaceHolder_lbtContact";
      await page.click(partiesButtonSelector);
      await page.waitForLoadState("networkidle");

      const partiesTableSelector = 'select[name="tblActiveParty_length"]';
      await page.selectOption(partiesTableSelector, "-1");
      await page.waitForLoadState("networkidle");

      const partiesHtml = await page.content();
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

      await context.close();
      return fullCaseData;
    } finally {
      //
      try {
        await context.close();
      } catch {}
    }
  }

  private async scrapePartiesFromHtml(
    html: string,
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
    tableSelector: string,
    url: string,
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
                "https://documents.dps.ny.gov/public/",
              ),
              url,
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

  async scrapeDocumentsOnly(govIds: string[]): Promise<RawGenericFiling[]> {
    console.log(
      `Scraping documents for ${govIds.length} cases with max ${this.max_concurrent_browsers} concurrent browsers`,
    );

    const scrapeDocumentsForId = async (
      govId: string,
    ): Promise<RawGenericFiling[]> => {
      let windowContext = null;
      try {
        console.log(`Scraping documents for case: ${govId} (new window)`);
        const caseUrl = `https://documents.dps.ny.gov/public/MatterManagement/CaseMaster.aspx?MatterCaseNo=${govId}`;
        const { context, page } = await this.newWindow();
        windowContext = context;

        await page.goto(caseUrl);
        await page.waitForLoadState("networkidle");

        const docsTableSelector = "#tblPubDoc > tbody";
        try {
          await page.waitForSelector(docsTableSelector, { timeout: 30_000 });
        } catch {} // Ignore timeout, just means no documents table

        const documentsHtml = await page.content();
        const documents = await this.scrapeDocumentsFromHtml(
          documentsHtml,
          docsTableSelector,
          page.url(),
        );
        await windowContext.close();
        return documents;
      } catch (error) {
        console.error(`Error scraping documents for ${govId}:`, error);
        if (windowContext) {
          await windowContext.close();
        }
        return [];
      }
    };

    const documentsArrays = await this.processTasksWithQueue(
      govIds,
      scrapeDocumentsForId,
    );
    return documentsArrays.flat();
  }

  async scrapePartiesOnly(govIds: string[]): Promise<RawGenericParty[]> {
    console.log(
      `Scraping parties for ${govIds.length} cases with max ${this.max_concurrent_browsers} concurrent browsers`,
    );

    const scrapePartiesForId = async (
      govId: string,
    ): Promise<RawGenericParty[]> => {
      let windowContext = null;
      try {
        console.log(`Scraping parties for case: ${govId} (new window)`);
        const caseUrl = `https://documents.dps.ny.gov/public/MatterManagement/CaseMaster.aspx?MatterCaseNo=${govId}`;
        const { context, page } = await this.newWindow();
        windowContext = context;

        await page.goto(caseUrl);
        await page.waitForLoadState("networkidle");

        const partiesButtonSelector = "#GridPlaceHolder_lbtContact";
        await page.click(partiesButtonSelector);
        await page.waitForLoadState("networkidle");

        const partiesTableSelector = 'select[name="tblActiveParty_length"]';
        await page.selectOption(partiesTableSelector, "-1");
        await page.waitForLoadState("networkidle");

        const partiesHtml = await page.content();
        const parties = await this.scrapePartiesFromHtml(partiesHtml);
        await windowContext.close();
        return parties;
      } catch (error) {
        console.error(`Error scraping parties for ${govId}:`, error);
        if (windowContext) {
          await windowContext.close();
        }
        return [];
      }
    };

    const partiesArrays = await this.processTasksWithQueue(
      govIds,
      scrapePartiesForId,
    );
    return partiesArrays.flat();
  }

  async scrapeMetadataOnly(
    govIds: string[],
  ): Promise<Partial<RawGenericDocket>[]> {
    console.log(
      `Scraping metadata for ${govIds.length} cases with max ${this.max_concurrent_browsers} concurrent browsers`,
    );

    const scrapeMetadataForId = async (
      govId: string,
    ): Promise<Partial<RawGenericDocket> | null> => {
      try {
        console.log(`Scraping metadata for case: ${govId}`);
        const metadata = await this.getCaseMeta(govId);
        return metadata;
      } catch (error) {
        console.error(`Error scraping metadata for ${govId}:`, error);
        return null;
      }
    };

    const metadataResults = await this.processTasksWithQueue(
      govIds,
      scrapeMetadataForId,
    );
    return metadataResults.filter(
      (metadata): metadata is Partial<RawGenericDocket> => metadata !== null,
    );
  }

  async scrapeByGovIds(govIds: string[], mode: ScrapingMode): Promise<any[]> {
    console.log(
      `Scraping ${govIds.length} cases in ${mode} mode (parallel processing)`,
    );

    switch (mode) {
      case ScrapingMode.FULL:
        console.log(
          `Running full scraping for ${govIds.length} cases with max ${this.max_concurrent_browsers} concurrent browsers`,
        );
        const scrapeFullForId = async (govId: string) => {
          try {
            const metadata = await this.getCaseMeta(govId);
            if (metadata) {
              const fullCase = await this.getCaseDetails(metadata);
              return fullCase;
            }
            return null;
          } catch (error) {
            console.error(`Error processing ${govId}:`, error);
            return null;
          }
        };

        const fullResults = await this.processTasksWithQueue(
          govIds,
          scrapeFullForId,
        );
        return fullResults.filter((result) => result !== null);

      case ScrapingMode.METADATA:
        return await this.scrapeMetadataOnly(govIds);

      case ScrapingMode.DOCUMENTS:
        return await this.scrapeDocumentsOnly(govIds);

      case ScrapingMode.PARTIES:
        return await this.scrapePartiesOnly(govIds);

      case ScrapingMode.FULL_EXTRACTION:
        console.log(
          `Running full extraction for ${govIds.length} cases with max ${this.max_concurrent_browsers} concurrent browsers`,
        );
        const scrapeExtractionForId = async (govId: string) => {
          try {
            // Run all three operations in parallel for each ID
            const [metadata, documents, parties] = await Promise.all([
              this.getCaseMeta(govId),
              this.scrapeDocumentsOnly([govId]),
              this.scrapePartiesOnly([govId]),
            ]);

            if (metadata) {
              metadata.filings = documents;
              metadata.case_parties = parties;
              return metadata;
            }
            return null;
          } catch (error) {
            console.error(`Error in full extraction for ${govId}:`, error);
            return null;
          }
        };

        const extractionResults = await this.processTasksWithQueue(
          govIds,
          scrapeExtractionForId,
        );
        return extractionResults.filter((result) => result !== null);

      default:
        throw new Error(`Unsupported scraping mode: ${mode}`);
    }
  }

  formatDate(date: Date): string {
    const month = (date.getMonth() + 1).toString().padStart(2, "0");
    const day = date.getDate().toString().padStart(2, "0");
    const year = date.getFullYear();
    return `${month}/${day}/${year}`;
  }

  createSearchUrl(beginDate: Date, endDate: Date): string {
    const formattedBeginDate = this.formatDate(beginDate);
    const formattedEndDate = this.formatDate(endDate);
    return `https://documents.dps.ny.gov/public/Common/SearchResults.aspx?MC=0&IA=&MT=&MST=&CN=&C=&M=&CO=0&DFF=${formattedBeginDate}&DFT=${formattedEndDate}&DT=&CI=0&FC=`;
  }

  async getFilingsBetweenDates(
    beginDate: Date,
    endDate: Date,
  ): Promise<string[]> {
    const url = this.createSearchUrl(beginDate, endDate);
    const $ = await this.getPage(url);
    const docketGovIds: string[] = [];

    $("#tblSearchedDocumentExternal > tbody:nth-child(3) tr").each((i, row) => {
      const cells = $(row).find("td");
      const docketGovId = $(cells[4]).find("a").text().trim();
      if (docketGovId) {
        docketGovIds.push(docketGovId);
      }
    });
    const govid_set = new Set(docketGovIds);

    return [...govid_set]; // Return unique values
  }
}

function parseArguments(): ScrapingOptions | null {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    return null; // Use default CLI behavior
  }

  let mode = ScrapingMode.FULL;
  let govIds: string[] = [];
  let dateString: string | undefined;
  let beginDate: string | undefined;
  let endDate: string | undefined;
  let fromFile: string | undefined;
  let outFile: string | undefined;

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === "--mode") {
      const modeValue = args[++i];
      if (Object.values(ScrapingMode).includes(modeValue as ScrapingMode)) {
        mode = modeValue as ScrapingMode;
      } else {
        throw new Error(
          `Invalid mode: ${modeValue}. Valid modes: ${Object.values(
            ScrapingMode,
          ).join(", ")}`,
        );
      }
    } else if (arg === "--gov-ids") {
      const idsString = args[++i];
      govIds = idsString
        .split(",")
        .map((id) => id.trim())
        .filter((id) => id.length > 0);
    } else if (arg === "--date") {
      dateString = args[++i];
    } else if (arg === "--begin-date") {
      beginDate = args[++i];
    } else if (arg === "--end-date") {
      endDate = args[++i];
    } else if (arg === "--from-file") {
      fromFile = args[++i];
    } else if (arg === "-o" || arg === "--outfile") {
      outFile = args[++i];
    } else if (!arg.startsWith("--")) {
      // If it doesn't start with --, treat as JSON (for backward compatibility)
      try {
        const parsed = JSON.parse(arg);
        if (Array.isArray(parsed)) {
          return null; // Let runCli handle this
        }
      } catch {
        // Not JSON, ignore
      }
    }
  }

  // Load gov IDs from file if specified
  if (fromFile) {
    try {
      const fileContent = fs.readFileSync(fromFile, "utf-8");
      const fileIds = fileContent
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => line.length > 0 && !line.startsWith("#"));
      govIds.push(...fileIds);
    } catch (error) {
      throw new Error(`Error reading file ${fromFile}: ${error}`);
    }
  }

  return {
    mode,
    govIds,
    dateString,
    beginDate,
    endDate,
    fromFile,
    outFile,
  };
}

async function saveResultsToFile(
  results: any[],
  outFile: string,
  mode: ScrapingMode,
) {
  try {
    const jsonData = JSON.stringify(results, null, 2);
    fs.writeFileSync(outFile, jsonData, "utf-8");
    console.log(
      `✅ Successfully saved ${results.length} results to ${outFile}`,
    );
    console.log(
      `📊 Mode: ${mode}, File size: ${(jsonData.length / 1024).toFixed(2)} KB`,
    );
  } catch (error) {
    console.error(`❌ Error writing to file ${outFile}:`, error);
    throw error;
  }
}

async function runCustomScraping(
  scraper: NyPucScraper,
  options: ScrapingOptions,
) {
  console.log(`Running custom scraping with options:`, options);

  if (options.mode === ScrapingMode.DATES && options.dateString) {
    console.log(`Scraping cases for date: ${options.dateString}`);
    const cases = await scraper.getDateCases(options.dateString);
    console.log(`Found ${cases.length} cases for date ${options.dateString}`);

    if (options.outFile) {
      await saveResultsToFile(cases, options.outFile, options.mode);
    } else {
      console.log(JSON.stringify(cases, null, 2));
    }
    return;
  }

  if (
    options.mode === ScrapingMode.FILINGS_BETWEEN_DATES &&
    options.beginDate &&
    options.endDate
  ) {
    console.log(
      `Scraping filings between ${options.beginDate} and ${options.endDate}`,
    );
    const docketGovIds = await scraper.getFilingsBetweenDates(
      new Date(options.beginDate),
      new Date(options.endDate),
    );
    console.log(
      `Found ${docketGovIds.length} dockets between ${options.beginDate} and ${options.endDate}`,
    );

    if (options.outFile) {
      await saveResultsToFile(docketGovIds, options.outFile, options.mode);
    } else {
      console.log(JSON.stringify(docketGovIds, null, 2));
    }
    return;
  }

  if (options.govIds && options.govIds.length > 0) {
    const results = await scraper.scrapeByGovIds(options.govIds, options.mode);
    console.log(`Scraped ${results.length} results in ${options.mode} mode`);

    if (options.outFile) {
      await saveResultsToFile(results, options.outFile, options.mode);
    } else {
      console.log(JSON.stringify(results, null, 2));
    }
    return;
  }

  throw new Error("No government IDs provided for scraping");
}

async function main() {
  let browser: Browser | null = null;
  try {
    browser = await chromium.launch({ headless: false });
    const context = await browser.newContext();
    const rootpage = await context.newPage();
    const scraper = new NyPucScraper(rootpage, context, browser);

    const customOptions = parseArguments();

    if (customOptions) {
      // Use custom scraping logic
      await runCustomScraping(scraper, customOptions);
    } else {
      // Use default CLI behavior
      await runCli(scraper);
    }
  } catch (error) {
    console.error("Scraper failed:", error);
    process.exit(1);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

main();
