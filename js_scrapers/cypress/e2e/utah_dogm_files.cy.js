describe("Utah DOGM Scraper", () => {
  it("scrapes well data and appends to a CSV", () => {
    const today = new Date();
    const fiveYearsAgo = new Date(today.getFullYear() - 5, today.getMonth(), today.getDate());

    let startDate = fiveYearsAgo;

    while (startDate < today) {
      let endDate = new Date(startDate.getFullYear(), startDate.getMonth() + 1, startDate.getDate());
      if (endDate > today) {
        endDate = today;
      }

      const startDateString = `${(startDate.getMonth() + 1).toString().padStart(2, '0')}/${startDate.getDate().toString().padStart(2, '0')}/${startDate.getFullYear()}`;
      const endDateString = `${(endDate.getMonth() + 1).toString().padStart(2, '0')}/${endDate.getDate().toString().padStart(2, '0')}/${endDate.getFullYear()}`;
      const dateRange = `${startDateString},${endDateString}`;

      cy.visit("https://oilgas.ogm.utah.gov/oilgasweb/live-data-search/lds-logs/logs-lu.xhtml");

      cy.get("#srchCForm\\:wellIdCloseBtn").click();
      cy.wait(100);
      cy.get("#srchCForm\\:srchCCheckboxMenu_label").click();
      cy.wait(300);
      cy.get(":nth-child(11) > .ui-chkbox > .ui-chkbox-box > .ui-chkbox-icon").click();
      cy.wait(300);
      cy.get('[style="font-weight: bold;width: 170px;border: none;"] > label').click();
      cy.get("#srchCForm\\:logDatePostedInput").clear();
      cy.wait(300);
      cy.get("#srchCForm\\:logDatePostedInput").type(dateRange);
      cy.wait(300);
      cy.get("#srchCForm\\:logDatePostedCompOpr").select("BETWEEN");
      cy.wait(300);
      cy.get("#dataTableForm\\:srchRsltDataTable\\:j_id7").select("250");
      cy.wait(300);
      cy.get("#srchCForm\\:srchBtn > .ui-button-text").click();
      cy.wait(5000); // Wait for results to load

      cy.get("#dataTableForm\\:srchRsltDataTable_data tr").if("exists").then(($rows) => {
        const data = [];
        $rows.each((index, row) => {
          const columns = Cypress.$(row).find("td");
          const rowData = [];
          columns.each((i, col) => {
            rowData.push(`"${Cypress.$(col).text().trim()}"`);
          });
          data.push(rowData);
        });

        if (data.length > 0) {
          cy.task("appendToCsv", { filename: "cypress/downloads/utah_dogm_well_data.csv", data });
        }
      });

      startDate = new Date(startDate.getFullYear(), startDate.getMonth() + 1, startDate.getDate());
    }
  });
});