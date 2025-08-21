describe("Utah Coal Scraper", () => {
  it("scrapes and parses coal data", () => {
    cy.visit("https://utahdnr.my.site.com/s/coal-document-display");
    cy.wait(5000); // Wait for the page to load

    cy.get(".slds-table > tbody:nth-child(2)").find("tr").each(($row) => {
      // Extract data from the row
      const permitId = $row.find('[data-label="Permit ID"]').text().trim();
      const mineName = $row.find('[data-label="Mine Name"]').text().trim();
      const mineOperator = $row.find('[data-label="Operator"]').text().trim();
      const county = $row.find('[data-label="County"]').text().trim();

      // Create the JSON object
      const caseData = {
        case_govid: permitId,
        opened_date: null,
        case_name: mineName,
        case_url: "",
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

      // Save the JSON object to a file
      cy.writeFile(`cypress/fixtures/${permitId}.json`, JSON.stringify(caseData, null, 2));
    });
  });
});
