use std::collections::HashMap;

use super::*;
use crate::common::file_extension::FileExtension;
use crate::s3_stuff::make_s3_client;
use crate::types::{
    GenericAttachment, GenericCase, GenericCaseLegacy, GenericFiling, GenericFilingLegacy,
    JurisdictionInfo,
};

use chrono::{NaiveDate, Utc};
use non_empty_string::non_empty_string;
use serde_json::json;

#[tokio::test]
async fn test_process_case() {
    tracing_subscriber::fmt()
        // enable everything
        .with_max_level(tracing::Level::INFO)
        .compact()
        // Display source code file paths
        .with_file(true)
        // Display source code line numbers
        .with_line_number(true)
        // Display the thread ID an event was recorded on
        .with_thread_ids(true)
        // Don't display the event's target (module path)
        .with_target(false)
        // sets this to be the default, global collector for this application.
        .init();
    let s3_client = make_s3_client().await;

    let filing_date_1 = NaiveDate::from_ymd_opt(2021, 3, 15).unwrap();
    let filing_date_2 = NaiveDate::from_ymd_opt(2022, 7, 22).unwrap();

    // Some extra metadata that will be encoded as JSON values.
    let mut filing_meta = HashMap::new();
    filing_meta.insert("source".to_string(), json!("court‑record‑scraper"));
    filing_meta.insert("confidence".to_string(), json!(0.96));

    // Attachments for the first filing.
    let attachment_1 = GenericAttachment {
        name: non_empty_string!("Judgement PDF"),
        url: "https://example.com/judgement.pdf".to_string(),
        document_extension: FileExtension::Pdf,
        hash: None,
        extra_metadata: HashMap::new(),
        attachment_type: Default::default(),
        attachment_subtype: Default::default(),
    };

    // Attachments for the second filing (different extension, no hash).
    let attachment_2 = GenericAttachment {
        name: non_empty_string!("Exhibit Image"),
        url: "https://example.com/exhibit.png".to_string(),
        document_extension: FileExtension::Png,
        hash: None,
        extra_metadata: HashMap::new(),
        attachment_type: Default::default(),
        attachment_subtype: Default::default(),
    };

    // First filing – contains one attachment and some authors.
    let filing_1 = GenericFiling {
        name: non_empty_string!("Initial Complaint").into(),
        filed_date: filing_date_1,
        attachments: vec![attachment_1],
        description: "The plaintiff filed the initial complaint.".to_string(),
        organization_authors: vec![non_empty_string!("Acme Corp")],
        individual_authors: vec![non_empty_string!("John Doe")],
        extra_metadata: filing_meta.clone(),
        filing_type: Default::default(),
    };

    // Second filing – different date, different attachment.
    let filing_2 = GenericFiling {
        name: non_empty_string!("Supplemental Exhibit").into(),
        filed_date: filing_date_2,
        attachments: vec![attachment_2],
        description: "An additional exhibit submitted by the defence.".to_string(),
        organization_authors: Default::default(),
        individual_authors: Default::default(),
        extra_metadata: filing_meta,
        filing_type: Default::default(),
    };

    // Top‑level case.
    let case = GenericCase {
        case_govid: non_empty_string!("TEST-CASE-123"),
        opened_date: None, // we let the scraper calculate this later
        case_name: "Example Case".to_string(),
        case_url: "https://court.gov/cases/TEST-CASE-123".to_string(),
        case_type: "Civil".to_string(),
        description: "A test case used for unit‑testing".to_string(),
        industry: "Technology".to_string(),
        petitioner: "Jane Smith".to_string(),
        hearing_officer: "Hon. Angela Lee".to_string(),
        closed_date: NaiveDate::from_ymd_opt(2023, 1, 9),
        filings: vec![filing_1, filing_2],
        extra_metadata: {
            let mut m = HashMap::new();
            m.insert("source_system".to_string(), json!("internal‑scraper"));
            m
        },
        case_parties: vec![],
        indexed_at: Utc::now(),
    };
    let jurisdiction = JurisdictionInfo::new_usa("test", "test");
    let casewith = CaseWithJurisdiction { case, jurisdiction };

    let result = process_case(&casewith, &s3_client).await;
    assert!(result.is_ok());
}
