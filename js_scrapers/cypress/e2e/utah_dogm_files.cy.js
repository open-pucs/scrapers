describe("template spec", () => {
  it("passes", () => {
    cy.visit(
      "https://oilgas.ogm.utah.gov/oilgasweb/live-data-search/lds-logs/logs-lu.xhtml",
    );

    cy.get("#srchCForm\\:wellIdCloseBtn").click();

    // cy.get(".ui-selectcheckboxmenu-trigger").click();
    // cy.get(
    //   "li.ui-selectcheckboxmenu-item:nth-child(11) > div:nth-child(1) > div:nth-child(2)",
    // ).click();
    //
    cy.get("#srchCForm\\:srchCCheckboxMenu_label").click();

    cy.wait(100);
    cy.get(
      ":nth-child(11) > .ui-chkbox > .ui-chkbox-box > .ui-chkbox-icon",
    ).click();

    cy.wait(100);
    cy.get(
      '[style="font-weight: bold;width: 170px;border: none;"] > label',
    ).click();
    cy.get("#srchCForm\\:logDatePostedInput").clear();
    cy.wait(300);
    cy.get("#srchCForm\\:logDatePostedInput").type("01/01/2024,01/01/2025");

    cy.wait(100);
    cy.get("#srchCForm\\:logDatePostedCompOpr").select("BETWEEN");

    /* ==== Generated with Cypress Studio ==== */
    cy.get("#srchCForm\\:logDatePostedInput").clear();
    cy.get("#srchCForm\\:logDatePostedInput").type("01/01/2010,01/01/2026");
    cy.get("#dataTableForm\\:srchRsltDataTable\\:j_id34").select("250");
    /* ==== End Cypress Studio ==== */

    cy.wait(400);
    cy.get("#srchCForm\\:srchBtn > .ui-button-text").click();

    cy.get(":nth-child(10) > a > img").click();
  });
});
// Click on the button with this css selector.
// #srchCForm\:wellIdCloseBtn
//
// Click on this selector button:
// .ui-selectcheckboxmenu-trigger
//
// then go ahead and enable this field:
// li.ui-selectcheckboxmenu-item:nth-child(11) > div:nth-child(1) > div:nth-child(2)
//
// Then go ahead and type the string into the input field
//#srchCForm\:logDatePostedInput
// Select date posted to web and throw it in this value.
// "01/01/2024,01/01/2025""

// Then select the between option of this selector
//#srchCForm\:logDatePostedCompOpr
//
// If the selection for the option would be best here that is
//#srchCForm\:logDatePostedCompOpr > option:nth-child(3)
//
// Now that all this is done go ahead and click the search button at:
//  #srchCForm\:srchBtn
