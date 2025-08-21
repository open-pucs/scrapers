describe("template spec", () => {
  it("passes", () => {
    cy.visit(
      "https://utahdnr.my.site.com/s/coal-document-display?tabType=Specific%20Project&selectedRowId=a0B8z000000iHHiEAM&selectedPermitName=C0070001",
    );
    /* ==== Generated with Cypress Studio ==== */
    cy.wait(100);
    cy.get("c-uttm_-coal_-public-documents-component").click();
    // I want to get the inner html for this table and parse it out
    // css selector( For both docket table and fillings table )
    //.slds-table > tbody:nth-child(2)
    //.slds-table > tbody:nth-child(2)
    // For the filling, a single <tr>'s html looks like this:
    // for each row I want you to extract it into a json object with this schema:
    //<th lwc-392cvb27u8q="" class="private-ssr-placeholder-class" role="rowheader" aria-readonly="true" scope="row" tabindex="0" data-label="View" data-col-key-value="0-button-icon-0"><lightning-primitive-cell-factory lwc-392cvb27u8q="" data-label="View" lwc-f1qthpifoh-host="" class=""><span lwc-f1qthpifoh="" class="slds-grid slds-grid_align-center"><div lwc-f1qthpifoh="" class="private-ssr-placeholder-class"><lightning-primitive-cell-button lwc-f1qthpifoh="" data-navigation="enable" data-action-triggers="enter,space" tabindex="-1"><lightning-button-icon variant="border" lwc-485vfn4rmof-host=""><button lwc-485vfn4rmof="" class="slds-button slds-button_icon slds-button_icon-border" name="viewClicked" type="button" part="button button-icon"><lightning-primitive-icon lwc-485vfn4rmof="" exportparts="icon" variant="bare" lwc-3pd22r3mk56-host=""><svg focusable="false" aria-hidden="true" viewBox="0 0 520 520" part="icon" lwc-3pd22r3mk56="" data-key="preview" class="slds-button__icon"><g lwc-3pd22r3mk56=""><path d="M518 251a288 288 0 00-516 0 20 20 0 000 18 288 288 0 00516 0 20 20 0 000-18zM260 370c-61 0-110-49-110-110s49-110 110-110 110 49 110 110-49 110-110 110zm0-180c-39 0-70 31-70 70s31 70 70 70 70-31 70-70-31-70-70-70z" lwc-3pd22r3mk56=""></path></g></svg></lightning-primitive-icon></button></lightning-button-icon></lightning-primitive-cell-button></div></span></lightning-primitive-cell-factory></th><td lwc-392cvb27u8q="" class="private-ssr-placeholder-class" role="gridcell" aria-readonly="true" tabindex="-1" data-label="Permit" data-col-key-value="permitName-text-1" data-cell-value="C0070001"><lightning-primitive-cell-factory lwc-392cvb27u8q="" data-label="Permit" lwc-f1qthpifoh-host=""><span lwc-f1qthpifoh="" class="slds-grid slds-grid_align-spread"><div lwc-f1qthpifoh="" class="slds-truncate"><lightning-base-formatted-text lwc-f1qthpifoh="" lwc-444t2t1prhe-host="">C0070001</lightning-base-formatted-text></div></span></lightning-primitive-cell-factory></td><td lwc-392cvb27u8q="" class="private-ssr-placeholder-class" role="gridcell" aria-readonly="true" tabindex="-1" data-label="Doc  Year " data-col-key-value="docYear-text-2" data-cell-value="1975"><lightning-primitive-cell-factory lwc-392cvb27u8q="" data-label="Doc  Year " lwc-f1qthpifoh-host=""><span lwc-f1qthpifoh="" class="slds-grid slds-grid_align-spread"><div lwc-f1qthpifoh="" class="slds-truncate"><lightning-base-formatted-text lwc-f1qthpifoh="" lwc-444t2t1prhe-host="">1975</lightning-base-formatted-text></div></span></lightning-primitive-cell-factory></td><td lwc-392cvb27u8q="" class="private-ssr-placeholder-class" role="gridcell" aria-readonly="true" tabindex="-1" data-label="Document Date" data-col-key-value="documentDate-text-3" data-cell-value="1975-10-24"><lightning-primitive-cell-factory lwc-392cvb27u8q="" data-label="Document Date" lwc-f1qthpifoh-host=""><span lwc-f1qthpifoh="" class="slds-grid slds-grid_align-spread"><div lwc-f1qthpifoh="" class="slds-truncate"><lightning-base-formatted-text lwc-f1qthpifoh="" lwc-444t2t1prhe-host="">1975-10-24</lightning-base-formatted-text></div></span></lightning-primitive-cell-factory></td><td lwc-392cvb27u8q="" class="private-ssr-placeholder-class" role="gridcell" aria-readonly="true" tabindex="-1" data-label="Doc Location " data-col-key-value="docLocation-text-4" data-cell-value="Incoming"><lightning-primitive-cell-factory lwc-392cvb27u8q="" data-label="Doc Location " lwc-f1qthpifoh-host=""><span lwc-f1qthpifoh="" class="slds-grid slds-grid_align-spread"><div lwc-f1qthpifoh="" class="slds-truncate"><lightning-base-formatted-text lwc-f1qthpifoh="" lwc-444t2t1prhe-host="">Incoming</lightning-base-formatted-text></div></span></lightning-primitive-cell-factory></td><td lwc-392cvb27u8q="" class="private-ssr-placeholder-class" role="gridcell" aria-readonly="true" tabindex="-1" data-label="Doc To" data-col-key-value="docTo-text-5" data-cell-value="Gordon Harmston"><lightning-primitive-cell-factory lwc-392cvb27u8q="" data-label="Doc To" lwc-f1qthpifoh-host=""><span lwc-f1qthpifoh="" class="slds-grid slds-grid_align-spread"><div lwc-f1qthpifoh="" class="slds-truncate"><lightning-base-formatted-text lwc-f1qthpifoh="" lwc-444t2t1prhe-host="">Gordon Harmston</lightning-base-formatted-text></div></span></lightning-primitive-cell-factory></td><td lwc-392cvb27u8q="" class="private-ssr-placeholder-class" role="gridcell" aria-readonly="true" tabindex="-1" data-label="Doc From" data-col-key-value="docFrom-text-6" data-cell-value="James Travis"><lightning-primitive-cell-factory lwc-392cvb27u8q="" data-label="Doc From" lwc-f1qthpifoh-host=""><span lwc-f1qthpifoh="" class="slds-grid slds-grid_align-spread"><div lwc-f1qthpifoh="" class="slds-truncate"><lightning-base-formatted-text lwc-f1qthpifoh="" lwc-444t2t1prhe-host="">James Travis</lightning-base-formatted-text></div></span></lightning-primitive-cell-factory></td><td lwc-392cvb27u8q="" class="private-ssr-placeholder-class" role="gridcell" aria-readonly="true" tabindex="-1" data-label="Doc Regarding" data-col-key-value="docRegarding-text-7" data-cell-value="Plan submittal"><lightning-primitive-cell-factory lwc-392cvb27u8q="" data-label="Doc Regarding" lwc-f1qthpifoh-host=""><span lwc-f1qthpifoh="" class="slds-grid slds-grid_align-spread"><div lwc-f1qthpifoh="" class="slds-truncate"><lightning-base-formatted-text lwc-f1qthpifoh="" lwc-444t2t1prhe-host="">Plan submittal</lightning-base-formatted-text></div></span></lightning-primitive-cell-factory></td><td lwc-392cvb27u8q="" class="private-ssr-placeholder-class" role="gridcell" aria-readonly="true" tabindex="-1" data-label="Task Id" data-col-key-value="docTaskId-text-8"><lightning-primitive-cell-factory lwc-392cvb27u8q="" data-label="Task Id" lwc-f1qthpifoh-host=""><span lwc-f1qthpifoh="" class="slds-grid slds-grid_align-spread"><div lwc-f1qthpifoh="" class="slds-truncate"><lightning-base-formatted-text lwc-f1qthpifoh="" lwc-444t2t1prhe-host=""></lightning-base-formatted-text></div></span></lightning-primitive-cell-factory></td>
    //
    // Specifically in this row, go ahead and make the fillings and there associated attachments.
    //
    // Since every file has only one attachment just go ahead and make the one attachment:
    // set the filling date to the document date (disregard the year)
    //
    // set the individual_authors vec to a vec with one string from the DOC FROM field
    // set the organization_authors vec to a vec with one string from the DOC TO field
    //
    // set the name of both the filling and the attachment to the field DOC REGARDING.
    //
    // set the doc_type to the field doc_location.
    //
    //
    // and most importantly set the attachment url field to the link in the first view collumn.
    //
    // when you are complete, bundle all these json objects in a list, and save them as something like coal-permits-page-1.json
    //
    //
    // #[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
    // pub struct RawGenericFiling {
    //     pub filed_date: NaiveDate,
    //     #[serde(default)]
    //     pub filling_govid: String,
    //     #[serde(default)]
    //     pub name: String,
    //     #[serde(default)]
    //     pub organization_authors: Vec<String>,
    //     #[serde(default)]
    //     pub individual_authors: Vec<String>,
    //     #[serde(default)]
    //     pub filing_type: String,
    //     #[serde(default)]
    //     pub description: String,
    //     #[serde(default)]
    //     pub attachments: Vec<RawGenericAttachment>,
    //     #[serde(default)]
    //     pub extra_metadata: HashMap<String, serde_json::Value>,

    // #[derive(Serialize, Deserialize, Debug, JsonSchema, Clone)]
    // pub struct RawGenericAttachment {
    //     #[serde(default)]
    //     pub name: String,
    //     pub document_extension: FileExtension,
    //     #[serde(default)]
    //     pub attachment_govid: String,
    //     #[serde(default)]
    //     pub url: String,
    //     #[serde(default)]
    //     pub attachment_type: String,
    //     #[serde(default)]
    //     pub attachment_subtype: String,
    //     #[serde(default)]
    //     pub extra_metadata: HashMap<String, serde_json::Value>,
    //     #[serde(default)]
    //     pub hash: Option<Blake2bHash>,
    // }
    //
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
