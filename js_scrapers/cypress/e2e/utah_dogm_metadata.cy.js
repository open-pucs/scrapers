describe("template spec", () => {
  it("passes", () => {
    cy.visit(
      "https://oilgas.ogm.utah.gov/oilgasweb/live-data-search/lds-well/well-lu.xhtml",
    );
    cy.get("#srchCForm\\:wellIdCloseBtn > .ui-button-text").click();
    cy.get(".ui-selectcheckboxmenu-trigger > .ui-icon").click();
    cy.get(
      ":nth-child(10) > .ui-chkbox > .ui-chkbox-box > .ui-chkbox-icon",
    ).click();
    cy.get("#srchCForm\\:isCbmFlgInput").clear("y");
    cy.get("#srchCForm\\:isCbmFlgInput").type("y");
    cy.wait(200);
    cy.get("#srchCForm\\:srchBtn > .ui-button-text").click();
    cy.get("#dataTableForm\\:srchRsltDataTable_paginator_top").click();
    cy.get("#dataTableForm\\:srchRsltDataTable\\:j_id29").select("250");

    cy.wait(500);
    cy.get(":nth-child(10) > a > img").click();
    cy.get("tbody > tr > :nth-child(9) > span").click();
    cy.get("#srchCForm\\:isCbmFlgInput").clear("n");
    cy.get("#srchCForm\\:isCbmFlgInput").type("n");
    cy.wait(200);
    cy.get("#srchCForm\\:srchBtn > .ui-button-text").click();
    cy.get("tbody > tr > :nth-child(9) > span").click();
    cy.wait(500);
    cy.get(":nth-child(10) > a > img").click();
  });
});
