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
  METADATA = "meta",
  FILLINGS = "fillings",
  PARTIES = "parties",
  ALL = "all",
}

interface ScrapingOptions {
  mode: ScrapingMode;
  govIds?: string[];
  dateString?: string;
  beginDate?: string;
  endDate?: string;
  fromFile?: string;
  outFile?: string;
  headed?: boolean;
  missing?: boolean;
}

// class NyPucScraper implements Scraper {
class NyPucScraper {
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

  async getDateCases(dateString: string): Promise<Partial<RawGenericDocket>[]> {
    // eg dateString = 09/09/2025
    const url = `https://documents.dps.ny.gov/public/Common/SearchResults.aspx?MC=1&IA=&MT=&MST=&CN=&SDT=${dateString}&SDF=${dateString}&C=&M=&CO=0`;
    console.log(`getting cases for date ${dateString}`);
    const cases: Partial<RawGenericDocket>[] = await this.getCasesAt(url);
    return cases;
  }
  // FIXME: This function is totally wrong its trying to extract caserows
  // async getDateCaseDocuments(
  //   dateString: string,
  // ): Promise<Partial<RawGenericDocket>[]> {
  //   // this would actually get both the new case and its openning documents in
  //   // one swoop
  //   // eg dateString = 09/09/2025
  //   const url = `https://documents.dps.ny.gov/public/Common/SearchResults.aspx?MC=0&IA=&MT=&MST=&CN=&SDT=9${dateString}&SDF=9${dateString}&C=&M=&CO=0&DFF=${dateString}&DFT=${dateString}&DT=&CI=0&FC=`;
  //   console.log(`getting cases for date ${dateString}`);
  //   const cases: Partial<RawGenericDocket>[] = await this.getCasesAt(url);
  //   return cases;
  // }

  async getGeneralRows($: any) {
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
    const rows = await this.getGeneralRows($);
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

  // TODO: This should probably get filtered out to the general task running layer.
  async filterOutExisting(
    cases: Partial<RawGenericDocket>[],
  ): Promise<Partial<RawGenericDocket>[]> {
    const caseDiffUrl =
      "http://localhost:33399/public/caselist/ny/ny_puc/casedata_differential";

    try {
      const response = await fetch(caseDiffUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cases),
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const data = await response.json();

      if (!data || !Array.isArray(data.to_process)) {
        throw new Error("Invalid response format: missing 'to_process' array");
      }

      // Assume the backend returns objects in the correct RawGenericDocket shape
      return data.to_process as RawGenericDocket[];
    } catch (err) {
      console.error("filterOutExisting failed:", err);
      return [];
    }
  }

  // gets ALL cases
  async getAllCaseList(): Promise<Partial<RawGenericDocket>[]> {
    const industry_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    const promises = industry_numbers.map((industry_number) => {
      console.log(`Processing industry index: ${industry_number}`);
      const industry_url = `https://documents.dps.ny.gov/public/Common/SearchResults.aspx?MC=1&IA=${industry_number}`;
      return this.getCasesAt(industry_url);
    });
    const results = await Promise.all(promises);
    return results.flat();
  }
  async getAllMissingCaseList(): Promise<Partial<RawGenericDocket>[]> {
    const cases = await this.getAllCaseList();
    const filtered_cases = await this.filterOutExisting(cases);
    return filtered_cases;
  }

  async getCaseMeta(gov_id: string): Promise<Partial<RawGenericDocket>> {
    // get main page
    const url = `https://documents.dps.ny.gov/public/Common/SearchResults.aspx?MC=1&IA=&MT=&MST=&CN=&MNO=${gov_id}&CO=0&C=&M=&CO=0`;
    console.log(`getting cases metadata for date ${gov_id}`);
    const cases: Partial<RawGenericDocket>[] = await this.getCasesAt(url);
    return cases[0];
  }

  private async scrapePartiesFromHtml(
    html: string,
  ): Promise<RawGenericParty[]> {
    const $ = cheerio.load(html);
    const parties: RawGenericParty[] = [];
    const partiesTablebodySelector = "#tblActiveParty > tbody";
    const rows = $(`${partiesTablebodySelector} tr`);
    console.log(`Found ${rows.length} party rows.`);

    rows.each((i, row) => {
      const cells = $(row).find("td");
      const nameCellHtml = $(cells[1]).html() || "";
      const emailPhoneCell = $(cells[4]).text();
      const addressCell = $(cells[3]).text();
      const companyCell = $(cells[2]).text();

      // Parse HTML content by splitting on <br> tags to properly handle the structure:
      // <td>Yates, William<br>Director of Research<br>Public Utility Law Project of New York, Inc.</td>
      const nameCellParts = nameCellHtml
        .split(/<br\s*\/?>/i)
        .map((part) => part.trim())
        .filter((part) => part.length > 0);

      console.log(`Row ${i} name cell parts:`, nameCellParts);

      let fullName = "";
      let title = "";
      let firstName = "";
      let lastName = "";

      if (nameCellParts.length > 0) {
        const rawName = nameCellParts[0].trim();

        // Check if name is in "Last, First" format
        if (rawName.includes(",")) {
          const nameComponents = rawName.split(",").map((part) => part.trim());
          lastName = nameComponents[0] || "";
          firstName = nameComponents[1] || "";
          fullName = `${firstName} ${lastName}`.trim();
        } else {
          // Assume it's already in "First Last" format or single name
          fullName = rawName;
          const nameWords = rawName.split(" ");
          if (nameWords.length >= 2) {
            firstName = nameWords.slice(0, -1).join(" ");
            lastName = nameWords[nameWords.length - 1];
          } else {
            firstName = rawName;
            lastName = "";
          }
        }

        // Extract title from second part if available
        if (nameCellParts.length > 1) {
          title = nameCellParts[1].trim();
        }
      }

      // Parse email and phone
      const emailPhoneCellText = $(cells[4]).text();
      let email = "";
      let phone = "";

      const phoneMatch = emailPhoneCellText.match(/Ph:\s*(.*)/);
      if (phoneMatch) {
        phone = phoneMatch[1].trim();
        const emailPart = emailPhoneCellText
          .substring(0, phoneMatch.index)
          .trim();
        if (emailPart.includes("@")) {
          email = emailPart;
        }
      } else if (emailPhoneCellText.includes("@")) {
        email = emailPhoneCellText.trim();
      } else {
        phone = emailPhoneCellText.trim();
      }

      const party: RawGenericParty = {
        name: fullName,
        artifical_person_type: RawArtificalPersonType.Human,
        western_human_last_name: lastName,
        western_human_first_name: firstName,
        human_title: title,
        human_associated_company: companyCell,
        contact_email: email,
        contact_phone: phone,
        contact_address: addressCell,
        extra_metadata: {
          name_cell_html: nameCellHtml,
          name_cell_parts: nameCellParts,
          raw_name_input: nameCellParts[0] || "",
          parsed_name_format: fullName.includes(",")
            ? "last_first"
            : "first_last",
        },
      };

      console.log(`Parsed party ${i}:`, {
        raw_input: nameCellParts[0] || "",
        full_name: fullName,
        first_name: firstName,
        last_name: lastName,
        title: title,
      });

      parties.push(party);
    });

    return parties;
  }

  async fetchFilingMetadata(fillingUrl: string): Promise<{
    description?: string;
    filedBy?: string;
    dateFiled?: string;
    filingNo?: string;
    filingOnBehalfOf?: string;
  } | null> {
    try {
      console.log(`Fetching filing metadata from: ${fillingUrl}`);
      const $ = await this.getPage(fillingUrl);

      const filingInfo = $("#filing_info");
      if (filingInfo.length === 0) {
        console.log("No filing_info section found on page");
        return null;
      }

      const metadata: any = {};

      // Extract Description of Filing
      const descriptionElement = filingInfo.find("#lblDescriptionofFilingval");
      if (descriptionElement.length > 0) {
        metadata.description = descriptionElement.text().trim();
      }

      // Extract Filed By
      const filedByElement = filingInfo.find("#lblFiledByval");
      if (filedByElement.length > 0) {
        metadata.filedBy = filedByElement.text().trim();
      }

      // Extract Date Filed
      const dateFiledElement = filingInfo.find("#lblDateFiledval");
      if (dateFiledElement.length > 0) {
        metadata.dateFiled = dateFiledElement.text().trim();
      }

      // Extract Filing No.
      const filingNoElement = filingInfo.find("#lblItemNoval");
      if (filingNoElement.length > 0) {
        metadata.filingNo = filingNoElement.text().trim();
      }

      // Extract Filing on behalf of
      const filingOnBehalfOfElement = filingInfo.find(
        "#lblFilingonbehalfofval",
      );
      if (filingOnBehalfOfElement.length > 0) {
        metadata.filingOnBehalfOf = filingOnBehalfOfElement.text().trim();
      }

      console.log(`Extracted filing metadata:`, metadata);
      return metadata;
    } catch (error) {
      console.error(
        `Error fetching filing metadata from ${fillingUrl}:`,
        error,
      );
      return null;
    }
  }

  private async enhanceFilingWithMetadata(
    filing: RawGenericFiling,
  ): Promise<void> {
    try {
      const metadata = await this.fetchFilingMetadata(filing.filling_url);
      if (metadata) {
        // Merge the metadata into the filing object
        if (metadata.description) {
          filing.description = metadata.description;
        }
        if (metadata.filedBy) {
          // Convert "Last,First" format to "[First Last]"
          const filedByFormatted = metadata.filedBy.includes(",")
            ? metadata.filedBy
                .split(",")
                .reverse()
                .map((n) => n.trim())
                .join(" ")
            : metadata.filedBy;
          filing.individual_authors = [filedByFormatted];
          filing.individual_authors_blob = metadata.filedBy;
        }
        if (metadata.filingOnBehalfOf) {
          filing.organization_authors_blob = metadata.filingOnBehalfOf;
        }
        // Store original metadata in extra_metadata for cross-checking
        filing.extra_metadata = {
          ...filing.extra_metadata,
          fetched_metadata: metadata,
        };
      }
    } catch (error) {
      console.error(
        `Failed to fetch metadata for filing ${filing.filling_govid}:`,
        error,
      );
    }
  }

  private async enhanceFilingsWithMetadata(
    filings: RawGenericFiling[],
  ): Promise<RawGenericFiling[]> {
    console.log("Enhancing filings with additional metadata...");
    for (const filing of filings) {
      await this.enhanceFilingWithMetadata(filing);
    }
    return filings;
  }

  private extractFilingUrlFromOnclick(onclickAttr: string): string {
    if (!onclickAttr) return "";

    // Parse the onclick: "javascript:return OpenGridPopupWindow('../MatterManagement/MatterFilingItem.aspx','FilingSeq=360722&amp;MatterSeq=64595');"
    const match = onclickAttr.match(/OpenGridPopupWindow\('([^']+)','([^']+)'\)/);
    if (!match) return "";

    const [, relativePath, params] = match;
    // Convert ../MatterManagement/MatterFilingItem.aspx to full URL
    const fullPath = relativePath.replace("../", "https://documents.dps.ny.gov/public/");
    // Decode HTML entities in parameters (&amp; -> &)
    const decodedParams = params.replace(/&amp;/g, "&");
    return `${fullPath}?${decodedParams}`;
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

        const onclickAttr = $(docCells[5]).find("a").attr("onclick") || "";
        const fillingUrl = this.extractFilingUrlFromOnclick(onclickAttr);

        // Skip this filing if we couldn't extract a valid URL
        if (!fillingUrl) {
          console.warn(`Skipping filing ${filingNo}: could not extract valid URL from onclick attribute`);
          return;
        }

        const documentTitle = $(docCells[3]).find("a").text().trim();
        const attachmentUrlRaw = $(docCells[3]).find("a").attr("href");

        const attachmentUrl = new URL(
          attachmentUrlRaw.replace(
            "../",
            "https://documents.dps.ny.gov/public/",
          ),
          url,
        ).toString();
        const fileName = $(docCells[6]).text().trim();

        if (!filingsMap.has(filingNo)) {
          const documentType = $(docCells[2]).text().trim();
          const dateFiled = $(docCells[1]).text().trim();
          const authors = $(docCells[4]).text().trim();

          filingsMap.set(filingNo, {
            name: documentTitle,
            filed_date: new Date(dateFiled).toISOString(),
            filling_url: fillingUrl,
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
            url: attachmentUrl,
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

  // To enable enhanced filing metadata, call with: scrapeDocumentsOnly(govId, true)
  async scrapeDocumentsOnly(
    govId: string,
    enhanceWithMetadata: boolean = false,
  ): Promise<RawGenericFiling[]> {
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
      let documents = await this.scrapeDocumentsFromHtml(
        documentsHtml,
        docsTableSelector,
        page.url(),
      );
      await windowContext.close();

      // Enhance with metadata if requested
      if (enhanceWithMetadata) {
        documents = await this.enhanceFilingsWithMetadata(documents);
      }

      return documents;
    } catch (error) {
      console.error(`Error scraping documents for ${govId}:`, error);
      if (windowContext) {
        await windowContext.close();
      }
      return [];
    }
  }

  async scrapePartiesOnly(govId: string): Promise<RawGenericParty[]> {
    let windowContext = null;
    try {
      console.log(`Scraping parties for case: ${govId} (new window)`);
      const caseUrl = `https://documents.dps.ny.gov/public/MatterManagement/CaseMaster.aspx?MatterCaseNo=${govId}`;
      const { context, page } = await this.newWindow();
      windowContext = context;

      await page.goto(caseUrl);
      // Removing this because it tries to wait until all the documents on the page are loaded, instead I am going to set a manual timer to wait 1 second and then try the navigation
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(10000);

      const partiesButtonSelector = "#GridPlaceHolder_lbtContact";
      await page.click(partiesButtonSelector);
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(1000);

      const partiesTableSelector = 'select[name="tblActiveParty_length"]';
      await page.selectOption(partiesTableSelector, "-1");
      await page.waitForLoadState("networkidle");

      await page.waitForFunction(
        () => {
          const tableBody = document.querySelector("#tblActiveParty > tbody");
          if (!tableBody) return false;
          const tableHtml = tableBody.innerHTML;
          return !tableHtml.includes("No data available in table");
        },
        { timeout: 10000 },
      );

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
  }

  async scrapeMetadataOnly(
    govId: string,
  ): Promise<Partial<RawGenericDocket> | null> {
    try {
      console.log(`Scraping metadata for case: ${govId}`);
      const metadata = await this.getCaseMeta(govId);
      return metadata;
    } catch (error) {
      console.error(`Error scraping metadata for ${govId}:`, error);
      return null;
    }
  }

  async scrapeByPartialDocket(
    partialDockets: Partial<RawGenericDocket>[],
    mode: ScrapingMode,
  ): Promise<Partial<RawGenericDocket>[]> {
    // Collect valid case_govid values
    const govIds = partialDockets
      .map((d) => d.case_govid)
      .filter(
        (id): id is string => typeof id === "string" && id.trim().length > 0,
      );

    // Call the existing scraper with those IDs
    return this.scrapeByGovIds(govIds, mode);
  }

  async scrapeByGovIds(
    govIds: string[],
    mode: ScrapingMode,
  ): Promise<Partial<RawGenericDocket>[]> {
    console.log(
      `Scraping ${govIds.length} cases in ${mode} mode (parallel processing)`,
    );

    const processId = async (
      govId: string,
    ): Promise<Partial<RawGenericDocket> | null> => {
      try {
        switch (mode) {
          case ScrapingMode.METADATA:
            return await this.scrapeMetadataOnly(govId);

          case ScrapingMode.FILLINGS: {
            const filings = await this.scrapeDocumentsOnly(govId);
            return { case_govid: govId, filings };
          }

          case ScrapingMode.PARTIES: {
            const parties = await this.scrapePartiesOnly(govId);
            return { case_govid: govId, case_parties: parties };
          }

          case ScrapingMode.ALL: {
            const [metadata, documents, parties] = await Promise.all([
              this.getCaseMeta(govId),
              this.scrapeDocumentsOnly(govId),
              this.scrapePartiesOnly(govId),
            ]);
            let return_case: Partial<RawGenericDocket> = { case_govid: govId };
            if (metadata) {
              return_case = metadata;
              return_case.case_govid = govId;
            }

            return_case.filings = documents;
            return_case.case_parties = parties;

            // TODO: Make this an optional paramater that can be set with the CLI TOOL
            return return_case;
          }
        }
      } catch (error) {
        console.error(`Error processing ${govId} in mode ${mode}:`, error);
        return null;
      }
    };
    const processIdAndUpload = async (
      govID: string,
    ): Promise<Partial<RawGenericDocket> | null> => {
      let return_result = null;
      try {
        return_result = await processId(govID);
        if (return_result !== null) {
          console.log(return_result.case_govid);
          try {
            await pushResultsToUploader([return_result], mode);
          } catch (e) {
            console.log(e);
          }
        } else {
          console.log("Result was equal to null.");
        }
        return return_result;
      } catch (err) {
        console.error(err);
        return return_result;
      }
    };

    const results = await this.processTasksWithQueue(
      govIds,
      processIdAndUpload,
    );
    return results.filter(
      (result): result is Partial<RawGenericDocket> => result !== null,
    );
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

  async getDocketIdsWithFilingsBetweenDates(
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

  async getCasesBetweenDates(
    beginDate: Date,
    endDate: Date,
  ): Promise<Partial<RawGenericDocket>[]> {
    let docket_ids = await this.getDocketIdsWithFilingsBetweenDates(
      beginDate,
      endDate,
    );
    let dockets = docket_ids.map((id) => {
      return { case_govid: id };
    });
    return dockets;
  }
}

function parseArguments(): ScrapingOptions | null {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    return null; // No arguments, will be handled in main
  }

  let mode = ScrapingMode.ALL;
  let govIds: string[] = [];
  let dateString: string | undefined;
  let beginDate: string | undefined;
  let endDate: string | undefined;
  let fromFile: string | undefined;
  let outFile: string | undefined;
  let headed = false; // Default to headless
  let missing = false; // Default to not checking for missing

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
    } else if (arg === "--headed") {
      headed = true;
    } else if (arg === "--missing") {
      missing = true;
    } else if (!arg.startsWith("--")) {
      // Backward compatibility for JSON array
      try {
        const parsed = JSON.parse(arg);
        if (Array.isArray(parsed)) {
          return null; // Let old runCli handle this
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
    headed,
    missing,
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
// TODO: This should 100% be in the }task handling layer.
// (And actually it might be a good idea for the task runner to just save the stuff to s3 directly? Food for thought.)
async function pushResultsToUploader(
  results: Partial<RawGenericDocket>[],
  mode: ScrapingMode,
) {
  let upload_type = "all";
  if (mode == ScrapingMode.FILLINGS) {
    upload_type = "only_fillings";
  }
  if (mode == ScrapingMode.PARTIES) {
    upload_type = "only_parties";
  }
  if (mode == ScrapingMode.METADATA) {
    upload_type = "only_metadata";
  }
  if (mode == ScrapingMode.ALL) {
    upload_type = "all";
  }
  const url = "http://localhost:33399/admin/cases/upload_raw";

  console.log(`Uploading ${results.length} with mode ${mode} to uploader.`);

  try {
    const payload = results.map((docket) => ({
      docket,
      upload_type,
      jurisdiction: {
        country: "usa",
        jurisdiction: "ny_puc",
        state: "ny",
      },
    }));
    const response = await fetch(url, {
      method: "POST",
      headers: {
        accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(
        `Upload failed: ${response.status} ${response.statusText} - ${errorText}`,
      );
    }
    let govid_list = results.map((x) => x.case_govid);
    console.log(`Successfully uploaded dockets to s3: ${govid_list}`);

    return "successfully uploaded docket";
  } catch (err) {
    console.error("Error uploading results:", err);
    // throw err;
    return null;
  }
}

async function runCustomScraping(
  scraper: NyPucScraper,
  options: ScrapingOptions,
) {
  console.log(`Running custom scraping with options:`, options);

  let casesToScrape: Partial<RawGenericDocket>[] = [];
  let govIds: string[] = [];

  // Determine which cases to scrape based on provided arguments
  if (options.govIds && options.govIds.length > 0) {
    // Explicit gov IDs provided
    govIds = options.govIds;
    console.log(`Using ${govIds.length} explicitly provided gov IDs`);
  } else if (options.dateString) {
    // Single date provided
    console.log(`Getting cases for date: ${options.dateString}`);
    casesToScrape = await scraper.getDateCases(options.dateString);
    console.log(
      `Found ${casesToScrape.length} cases for date ${options.dateString}`,
    );
  } else if (options.beginDate && options.endDate) {
    // Date range provided
    console.log(
      `Getting cases between ${options.beginDate} and ${options.endDate}`,
    );
    casesToScrape = await scraper.getCasesBetweenDates(
      new Date(options.beginDate),
      new Date(options.endDate),
    );
    console.log(
      `Found ${casesToScrape.length} cases between ${options.beginDate} and ${options.endDate}`,
    );
  } else {
    // No specific cases provided
    if (options.missing) {
      console.log("No specific cases provided, getting all missing cases");
      casesToScrape = await scraper.getAllMissingCaseList();
      console.log(`Found ${casesToScrape.length} missing cases`);
    } else {
      console.log("No specific cases provided, getting all cases");
      casesToScrape = await scraper.getAllCaseList();
      console.log(`Found ${casesToScrape.length} cases`);
    }
  }

  // Extract gov IDs from cases if we have partial dockets
  if (casesToScrape.length > 0) {
    govIds = casesToScrape
      .map((c) => c.case_govid)
      .filter(
        (id): id is string => typeof id === "string" && id.trim().length > 0,
      );
  }

  if (govIds.length === 0) {
    throw new Error("No cases found to scrape");
  }

  // Now scrape the cases with the specified mode
  console.log(`Scraping ${govIds.length} cases in ${options.mode} mode`);
  const results = await scraper.scrapeByGovIds(govIds, options.mode);

  console.log(`Scraped ${results.length} results in ${options.mode} mode`);

  // Save or output results
  if (options.outFile) {
    await saveResultsToFile(results, options.outFile, options.mode);
  } else {
    console.log(JSON.stringify(results, null, 2));
  }
}

async function main() {
  let browser: Browser | null = null;
  try {
    const customOptions = parseArguments();

    if (!customOptions) {
      console.error("Error: No scraping arguments provided. Exiting.");
      console.log(
        "Please provide arguments to run the scraper, e.g. --mode full-all-missing",
      );
      process.exit(1);
    }

    // Launch the browser based on the 'headed' option
    browser = await chromium.launch({ headless: !customOptions.headed });
    const context = await browser.newContext();
    const rootpage = await context.newPage();
    const scraper = new NyPucScraper(rootpage, context, browser);

    // Use custom scraping logic
    await runCustomScraping(scraper, customOptions);
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
