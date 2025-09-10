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

class NyPucScraper implements Scraper {
  state = "ny";
  jurisdiction_name = "ny_puc";
  page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async getCaseList(): Promise<Partial<RawGenericDocket>[]> {
    await this.page.goto(
      "https://documents.dps.ny.gov/public/MatterManagement/CaseMaster.aspx",
    );
    await this.page.waitForLoadState("networkidle");

    // Click search to get all cases
    await this.page.locator('input[name="btnSearch"]').click();
    await this.page.waitForLoadState("networkidle");

    const cases: Partial<RawGenericDocket>[] = [];
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

        const caseData: Partial<RawGenericDocket> = {
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
    caseData: Partial<RawGenericDocket>,
  ): Promise<RawGenericDocket> {
    if (!caseData.case_url) {
      throw new Error("Case URL is missing");
    }

    await this.page.goto(caseData.case_url);
    await this.page.waitForLoadState("networkidle");

    const caseDocuments = await this.scrapeDocuments(
      "#MainContent_grdCaseDocuments",
    );
    const caseParties = await this.scrapeParties();

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
  private async scrapeParties(): Promise<RawGenericParty[]> {
    // To begin take the page and then click on this element.
    // #GridPlaceHolder_lbtContact
    await this.page.locator("#GridPlaceHolder_lbtContact").click();
    await this.page.waitForLoadState("networkidle");

    const parties: RawGenericParty[] = [];
    const rows = await this.page
      .locator("#grdParty tr.gridrow, #grdParty tr.gridaltrow")
      .all();

    for (const row of rows) {
      const cells = await row.locator("td").all();
      const nameCell = await cells[1].innerText();
      const emailPhoneCell = await cells[4].innerText();

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
    }

    return parties;
    // then after you use the same table selector as scrapeDocuments you will run across a table with these rows:
    // <tr role="row" class="even"><td class="sorting_1">2</td><td>Yates, William<br>Director of Research
    // <br>Public Utility Law Project of New York, Inc.
    // </td><td>Public Utility Law Project of New York, Inc.<br></td><td>194 Washington Ave.
    // <br>Albany,
    // NY
    // 12210
    // </td><td><a href="mailto:wyates@utilityproject.org">wyates@utilityproject.org</a><br>Ph: 877-669-2572<br></td><td>Yes</td><td><a href="#" onclick="javascript:return Navigate('''','''MatterSeq=55825&amp;MemberSeq=35224&amp;ConsentType=PARTY&amp;FullName=Yates, William''')"> Request </a></td><td>03/27/2023</td></tr>
    //
    //
    // then save them in a json schema generated by this rust code:
    //
    // #[derive(Serialize, Deserialize, Debug, JsonSchema, Clone, Copy, Default)]
    // #[serde(rename_all = "snake_case")]
    // pub enum RawArtificalPersonType {
    //     #[default]
    //     Unknown,
    //     Human,
    //     Organization,
    // }
    //
    // #[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
    // pub struct RawGenericParty {
    //     pub name: String,
    //     pub artifical_person_type: RawArtificalPersonType,
    //     pub western_human_first_name: String,
    //     pub western_human_last_name: String,
    //     pub human_title: String,
    //     pub human_associated_company: String,
    //     pub contact_email: String,
    //     pub contact_phone: String,
    // }
  }

  private async scrapeDocuments(
    tableSelector: string,
  ): Promise<RawGenericFiling[]> {
    const documents: RawGenericFiling[] = [];
    while (true) {
      await this.page.waitForLoadState("networkidle");
      const docRows = await this.page
        .locator(`${tableSelector} tr.gridrow, ${tableSelector} tr.gridaltrow`)
        .all();
      // Row html
      // <tr role="row" class="odd"><td>1</td><td class="sorting_1">09/05/2025</td><td>Motions</td><td><a href="../Common/ViewDoc.aspx?DocRefId={A0BB1A99-0000-C83E-BF7C-C53B5F2A6A03}" target="_blank">Request for Nondisclosure<img class="new-window-icon" aria-label="Open file in new window" alt="Opens in new window" src="../Style/icons/open-in-new-window.png"></a></td><td>New York State Electric &amp; Gas Corporation, Rochester Gas and Electric Corporation</td><td><a href="#" class="dt_item-number" aria-label="Item Number 995" onclick="javascript:return OpenGridPopupWindow('''../MatterManagement/MatterFilingItem.aspx''','''FilingSeq=369300&amp;MatterSeq=55825''');">995<img class="new-window-icon" aria-label="Opens item in new window" alt="Opens in new window" src="../Style/icons/open-in-new-window.png"></a></td><td>RequestForNondisclosure.pdf</td><td><img src="../images/pdf.gif" alt="pdf"></td><td>2.23 KB</td></tr>
      // when I click the open grid popup window it redirects me to: documents.dps.ny.gov/public/MatterManagement/MatterFilingItem.aspx?FilingSeq=369300&MatterSeq=55825

      for (const docRow of docRows) {
        const docCells = await docRow.locator("td").all();
        if (docCells.length > 3) {
          const documentTitle = await docCells[3].locator("a").innerText();
          const documentType = await docCells[2].innerText();
          const dateFiled = await docCells[1].innerText();
          const attachmentUrl = await docCells[3]
            .locator("a")
            .getAttribute("href");
          const authors = await docCells[4].innerText();

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
