describe("template spec", () => {
  it("passes", () => {
    cy.visit("https://utahdnr.my.site.com/s/coal-document-display");
    /* ==== Generated with Cypress Studio ==== */
    cy.wait(100);
    cy.get("c-uttm_-coal_-public-documents-component").click();
    // I want to get the inner html for this table and parse it out
    // css selector( For both docket table and fillings table )
    //.slds-table > tbody:nth-child(2)
    //.slds-table > tbody:nth-child(2)
    // For the docket, a single <tr>'s html looks like this:
    //<th lwc-392cvb27u8q="" class="private-ssr-placeholder-class" role="rowheader" aria-readonly="true" scope="row" tabindex="0" data-label="View" data-col-key-value="0-button-icon-0"><lightning-primitive-cell-factory lwc-392cvb27u8q="" data-label="View" lwc-f1qthpifoh-host="" class=""><span lwc-f1qthpifoh="" class="slds-grid slds-grid_align-center"><div lwc-f1qthpifoh="" class="private-ssr-placeholder-class"><lightning-primitive-cell-button lwc-f1qthpifoh="" data-navigation="enable" data-action-triggers="enter,space" tabindex="-1"><lightning-button-icon variant="border-filled" lwc-485vfn4rmof-host=""><button lwc-485vfn4rmof="" class="slds-button slds-button_icon slds-button_icon-border-filled" title="Preview" type="button" part="button button-icon"><lightning-primitive-icon lwc-485vfn4rmof="" exportparts="icon" variant="bare" lwc-1of0md8cufd-host=""><svg focusable="false" aria-hidden="true" viewBox="0 0 520 520" part="icon" lwc-1of0md8cufd="" data-key="enter" class="slds-button__icon"><g lwc-1of0md8cufd=""><path d="M440 305s1 16-15 16H152c-9 0-13-12-7-18l56-56c6-6 6-15 0-21l-21-21c-6-6-15-6-21 0L24 340c-6 6-6 15 0 21l136 135c6 6 15 6 21 0l21-21c6-6 6-15 0-21l-56-56c-6-7-2-17 7-17h332c7 0 15-8 15-16V35c0-7-7-15-15-15h-30c-8 0-15 8-15 15v270z" lwc-1of0md8cufd=""></path></g></svg></lightning-primitive-icon><span class="slds-assistive-text" lwc-485vfn4rmof="">SELECT</span></button></lightning-button-icon></lightning-primitive-cell-button></div></span></lightning-primitive-cell-factory></th><td lwc-392cvb27u8q="" class="private-ssr-placeholder-class" role="gridcell" aria-readonly="true" tabindex="-1" data-label="Mine Name" data-col-key-value="permitMineName-text-1" data-cell-value="White Oak Mine"><lightning-primitive-cell-factory lwc-392cvb27u8q="" data-label="Mine Name" lwc-f1qthpifoh-host=""><span lwc-f1qthpifoh="" class="slds-grid slds-grid_align-spread"><div lwc-f1qthpifoh="" class="slds-truncate"><lightning-base-formatted-text lwc-f1qthpifoh="" lwc-444t2t1prhe-host="">White Oak Mine</lightning-base-formatted-text></div></span></lightning-primitive-cell-factory></td><td lwc-392cvb27u8q="" class="private-ssr-placeholder-class" role="gridcell" aria-readonly="true" tabindex="-1" data-label="Permit ID" data-col-key-value="permitName-text-2" data-cell-value="C0070001"><lightning-primitive-cell-factory lwc-392cvb27u8q="" data-label="Permit ID" lwc-f1qthpifoh-host=""><span lwc-f1qthpifoh="" class="slds-grid slds-grid_align-spread"><div lwc-f1qthpifoh="" class="slds-truncate"><lightning-base-formatted-text lwc-f1qthpifoh="" lwc-444t2t1prhe-host="">C0070001</lightning-base-formatted-text></div></span></lightning-primitive-cell-factory></td><td lwc-392cvb27u8q="" class="private-ssr-placeholder-class" role="gridcell" aria-readonly="true" tabindex="-1" data-label="County" data-col-key-value="permitCountyName-text-3" data-cell-value="07 CARBON"><lightning-primitive-cell-factory lwc-392cvb27u8q="" data-label="County" lwc-f1qthpifoh-host=""><span lwc-f1qthpifoh="" class="slds-grid slds-grid_align-spread"><div lwc-f1qthpifoh="" class="slds-truncate"><lightning-base-formatted-text lwc-f1qthpifoh="" lwc-444t2t1prhe-host="">07 CARBON</lightning-base-formatted-text></div></span></lightning-primitive-cell-factory></td><td lwc-392cvb27u8q="" class="private-ssr-placeholder-class" role="gridcell" aria-readonly="true" tabindex="-1" data-label="Owner" data-col-key-value="permitOwner-text-4" data-cell-value="Unknown Operator"><lightning-primitive-cell-factory lwc-392cvb27u8q="" data-label="Owner" lwc-f1qthpifoh-host=""><span lwc-f1qthpifoh="" class="slds-grid slds-grid_align-spread"><div lwc-f1qthpifoh="" class="slds-truncate"><lightning-base-formatted-text lwc-f1qthpifoh="" lwc-444t2t1prhe-host="">Unknown Operator</lightning-base-formatted-text></div></span></lightning-primitive-cell-factory></td>
    // for each row I want you to extract it into a json object with this schema:
    // specifically throw the permit id in case_govid, put the mine operator in petitioner. Set the industry as "Coal", set the case name as the Mine Name, (in this case white oak mine,), under extra metadata log the county that the mine is in.
    // #[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
    // pub struct RawGenericCase {
    //     pub case_govid: NonEmptyString,
    //     // This shouldnt be an optional field in the final submission, since it can be calculated from
    //     // the minimum of the fillings, and the scraper should calculate it.
    //     #[serde(default)]
    //     pub opened_date: Option<NaiveDate>,
    //     #[serde(default)]
    //     pub case_name: String,
    //     #[serde(default)]
    //     pub case_url: String,
    //     #[serde(default)]
    //     pub case_type: String,
    //     #[serde(default)]
    //     pub case_subtype: String,
    //     #[serde(default)]
    //     pub description: String,
    //     #[serde(default)]
    //     pub industry: String,
    //     #[serde(default)]
    //     pub petitioner: String,
    //     #[serde(default)]
    //     pub hearing_officer: String,
    //     #[serde(default)]
    //     pub closed_date: Option<NaiveDate>,
    //     #[serde(default)]
    //     pub filings: Vec<RawGenericFiling>,
    //     #[serde(default)]
    //     pub case_parties: Vec<GenericParty>,
    //     #[serde(default)]
    //     pub extra_metadata: HashMap<String, serde_json::Value>,

    // After you have created the json object, save it to a file <permit-id>.json

    // cy.get('c-uttm_-coal_-public-documents-component').click();
    // cy.get('c-uttm_-coal_-public-documents-component').click();
    // cy.get('c-uttm_-coal_-public-documents-component').click();
    // cy.get('c-uttm_-coal_-public-documents-component').click();
    // cy.get('c-uttm_-coal_-public-documents-component').click();
    // cy.get('c-uttm_-coal_-public-documents-component').click();
    // cy.get('c-uttm_-coal_-public-documents-component').click();
    // cy.get('c-uttm_-coal_-public-documents-component').click();
    // cy.get('c-uttm_-coal_-public-documents-component').click();
    /* ==== End Cypress Studio ==== */
  });
});
