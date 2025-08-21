describe("Utah DOGM files Scraper", () => {
  it("scrapes well data and appends to a CSV", () => {
    const root_url = "https://ogm.utah.gov/coal-files/";

    const make_oil_service_url = (coal_permit_id: string) =>
      `https://ogm.utah.gov/coal-files/?tabType=Specific+Project&selectedRowId=a0B8z000000iHHjEAM&selectedPermitName=${coal_permit_id}`;
  });

  try {
    cy.visit(root_url);
  } catch {}
});
