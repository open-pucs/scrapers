
describe("Utah Coal Everything Scraper", () => {
  it("scrapes and parses coal data into a single file", () => {
    cy.visit(
      "https://utahdnr.my.site.com/s/coal-document-display?tabType=Specific%20Project&selectedRowId=a0B8z000000iHHiEAM&selectedPermitName=C0070001",
    );
    cy.wait(5000); // Wait for the page to load

    const filings = [];

    cy.get(".slds-table > tbody:nth-child(2)")
      .find("tr")
      .each(($row) => {
        // Extract data from the row
        const docDate = $row.find('[data-label="Document Date"]').text().trim();
        const docFrom = $row.find('[data-label="DOC FROM"]').text().trim();
        const docTo = $row.find('[data-label="DOC TO"]').text().trim();
        const docRegarding = $row.find('[data-label="DOC REGARDING"]').text().trim();
        const docLocation = $row.find('[data-label="Location"]').text().trim();
        const viewLink = $row.find('a').first().invoke('attr', 'href');

        const filing = {
          filed_date: docDate,
          filling_govid: "",
          name: docRegarding,
          organization_authors: [docTo],
          individual_authors: [docFrom],
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
              extra_metadata: {},
              hash: null,
            },
          ],
          extra_metadata: {},
        };

        filings.push(filing);
      })
      .then(() => {
        // Save the JSON object to a file
        cy.writeFile(
          "cypress/fixtures/coal-permits-page-1.json",
          JSON.stringify(filings, null, 2),
        );
      });
  });
});
