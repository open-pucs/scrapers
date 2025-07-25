describe("Utah DOGM Scraper", () => {
  it("scrapes well data and appends to a CSV", () => {
    const today = new Date();
    const fiveYearsAgo = new Date(
      today.getFullYear() - 15,
      today.getMonth(),
      today.getDate(),
    );

    let startDate = fiveYearsAgo;

    while (startDate < today) {
      let endDate = new Date(
        startDate.getFullYear(),
        startDate.getMonth() + 1,
        startDate.getDate(),
      );
      if (endDate > today) {
        endDate = today;
      }

      const startDateString = `${(startDate.getMonth() + 1).toString().length === 1 ? "0" + (startDate.getMonth() + 1).toString() : (startDate.getMonth() + 1).toString()}/${startDate.getDate().toString().length === 1 ? "0" + startDate.getDate().toString() : startDate.getDate().toString()}/${startDate.getFullYear()}`;
      const endDateString = `${(endDate.getMonth() + 1).toString().length === 1 ? "0" + (endDate.getMonth() + 1).toString() : (endDate.getMonth() + 1).toString()}/${endDate.getDate().toString().length === 1 ? "0" + endDate.getDate().toString() : endDate.getDate().toString()}/${endDate.getFullYear()}`;
      const dateRange = `${startDateString},${endDateString}`;

      try {
        cy.visit(
          "https://oilgas.ogm.utah.gov/oilgasweb/live-data-search/lds-logs/logs-lu.xhtml",
        );

        cy.get("#srchCForm\\:wellIdCloseBtn").click();
        cy.wait(100);
        cy.get("#srchCForm\\:srchCCheckboxMenu_label").click();
        cy.wait(300);
        cy.get(
          ":nth-child(11) > .ui-chkbox > .ui-chkbox-box > .ui-chkbox-icon",
        ).click();
        cy.wait(300);
        cy.get(
          '[style="font-weight: bold;width: 170px;border: none;"] > label',
        ).click();
        cy.get("#srchCForm\\:logDatePostedInput").clear();
        cy.wait(300);
        cy.get("#srchCForm\\:logDatePostedInput").type(dateRange);
        cy.wait(300);
        cy.get("#srchCForm\\:logDatePostedCompOpr").select("BETWEEN");
        cy.wait(300);
        cy.get("#dataTableForm\\:srchRsltDataTable\\:j_id7").select("250");

        cy.wait(300);
        cy.get("#srchCForm\\:srchBtn > .ui-button-text").click();
        cy.wait(3000);
        // I want this call to not fuck up the entire script if it fails. if it fails I just want to extract what would normally be on the page as if the click didnt happen.
        //
        // -------------------- CRITICAL MODIFICATION START --------------------
        // Safely attempt pagination selection without failing entire test
        const paginationSelector =
          "#dataTableForm\\:srchRsltDataTable\\:j_id34";
        cy.get("body").then(($body) => {
          const $dropdown = $body.find(paginationSelector);

          if ($dropdown.length && $dropdown[0] instanceof HTMLSelectElement) {
            // Check current selection to avoid unnecessary reloads
            if ($dropdown.val() !== "250") {
              $dropdown.val("250");
              $dropdown.trigger("change");
            }
          } else {
            console.log(
              "Pagination dropdown not found. Continuing with current results count.",
            );
          }
        });
        // -------------------- CRITICAL MODIFICATION END --------------------
        cy.wait(6000); // Wait for results to load

        cy.get("body").then(($body) => {
          if (
            $body.find("#dataTableForm\\:srchRsltDataTable_data tr").length > 0
          ) {
            cy.get("#dataTableForm\\:srchRsltDataTable_data tr").then(
              ($rows) => {
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
                  cy.task("appendToCsv", {
                    filename: "cypress/downloads/utah_dogm_well_data.csv",
                    data,
                  } as { filename: string; data: string[][] });
                }
              },
            );
          }
        });
      } catch (err) {
        console.log(err);
        console.log("Encountered error, moving on to next chunk of data.");
      }

      startDate = new Date(
        startDate.getFullYear(),
        startDate.getMonth() + 1,
        startDate.getDate(),
      );
    }
  });
});
