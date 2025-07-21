describe('template spec', () => {
  it('passes', () => {
    cy.visit('https://example.cypress.io')
    /* ==== Generated with Cypress Studio ==== */
    cy.get('.dropdown-toggle').click();
    cy.get('.dropdown-menu > :nth-child(5) > a').click();
    cy.get(':nth-child(1) > :nth-child(3) > a').click();
    cy.visit('https://google.com');
    cy.get('.pull-right > li > a').click();
    /* ==== End Cypress Studio ==== */
  })
})