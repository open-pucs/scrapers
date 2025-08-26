# Data Types and Processing Pipeline

## Core Data Structures

### Raw Data Types (src/types/raw.rs)

#### RawGenericDocket
Represents a raw legal case docket with all filings and metadata.

**Fields:**
- `case_govid` (NonEmptyString) - Unique government identifier for the case
- `opened_date` (Option<NaiveDate>) - When the case was opened
- `case_name` (String) - Name/title of the case
- `case_url` (String) - URL to the original case
- `case_type` (String) - Type of case (e.g., civil, criminal)
- `case_subtype` (String) - Subtype of case
- `description` (String) - Description of the case
- `industry` (String) - Related industry
- `petitioner` (String) - Petitioner in the case
- `hearing_officer` (String) - Hearing officer assigned
- `closed_date` (Option<NaiveDate>) - When the case was closed
- `filings` (Vec<RawGenericFiling>) - All filings in the case
- `case_parties` (Vec<GenericParty>) - Parties involved in the case
- `extra_metadata` (HashMap<String, serde_json::Value>) - Additional metadata
- `indexed_at` (DateTime<Utc>) - When the case was indexed

#### RawGenericFiling
Represents a raw filing within a case.

**Fields:**
- `filed_date` (Option<NaiveDate>) - When the filing was filed
- `filling_govid` (String) - Government identifier for the filing
- `name` (String) - Name/title of the filing
- `organization_authors` (Vec<String>) - Organizations that authored the filing
- `individual_authors` (Vec<String>) - Individuals that authored the filing
- `organization_authors_blob` (String) - Raw organization authors text
- `individual_authors_blob` (String) - Raw individual authors text
- `filing_type` (String) - Type of filing
- `description` (String) - Description of the filing
- `attachments` (Vec<RawGenericAttachment>) - Attachments to the filing
- `extra_metadata` (HashMap<String, serde_json::Value>) - Additional metadata

#### RawGenericAttachment
Represents a raw attachment to a filing.

**Fields:**
- `name` (String) - Name of the attachment
- `document_extension` (FileExtension) - File extension
- `attachment_govid` (String) - Government identifier for the attachment
- `url` (String) - URL to the attachment
- `attachment_type` (String) - Type of attachment
- `attachment_subtype` (String) - Subtype of attachment
- `extra_metadata` (HashMap<String, serde_json::Value>) - Additional metadata
- `hash` (Option<Blake2bHash>) - Blake2b hash of the attachment content

### Processed Data Types (src/types/processed.rs)

#### ProcessedGenericDocket
Represents a processed legal case docket with standardized structure.

**Fields:**
- `case_govid` (NonEmptyString) - Unique government identifier for the case
- `opened_date` (NaiveDate) - When the case was opened
- `case_name` (String) - Name/title of the case
- `case_url` (String) - URL to the original case
- `case_type` (String) - Type of case
- `case_subtype` (String) - Subtype of case
- `description` (String) - Description of the case
- `industry` (String) - Related industry
- `petitioner` (String) - Petitioner in the case
- `hearing_officer` (String) - Hearing officer assigned
- `closed_date` (Option<NaiveDate>) - When the case was closed
- `filings` (HashMap<u64, ProcessedGenericFiling>) - All filings in the case (indexed)
- `case_parties` (Vec<GenericParty>) - Parties involved in the case
- `extra_metadata` (HashMap<String, serde_json::Value>) - Additional metadata
- `indexed_at` (DateTime<Utc>) - When the case was indexed
- `processed_at` (DateTime<Utc>) - When the case was processed

#### ProcessedGenericFiling
Represents a processed filing within a case.

**Fields:**
- `filed_date` (Option<NaiveDate>) - When the filing was filed
- `openscrapers_filling_id` (u64) - Internal identifier
- `index_in_docket` (u64) - Index in the docket
- `filling_govid` (String) - Government identifier for the filing
- `name` (String) - Name/title of the filing
- `organization_authors` (Vec<OrgName>) - Processed organization authors
- `individual_authors` (Vec<OrgName>) - Processed individual authors
- `filing_type` (String) - Type of filing
- `description` (String) - Description of the filing
- `attachments` (HashMap<u64, ProcessedGenericAttachment>) - Attachments (indexed)
- `extra_metadata` (HashMap<String, serde_json::Value>) - Additional metadata

#### ProcessedGenericAttachment
Represents a processed attachment to a filing.

**Fields:**
- `name` (String) - Name of the attachment
- `openscrapers_attachment_id` (u64) - Internal identifier
- `index_in_filling` (u64) - Index in the filing
- `document_extension` (FileExtension) - File extension
- `attachment_govid` (String) - Government identifier for the attachment
- `url` (String) - URL to the attachment
- `attachment_type` (String) - Type of attachment
- `attachment_subtype` (String) - Subtype of attachment
- `extra_metadata` (HashMap<String, serde_json::Value>) - Additional metadata
- `hash` (Option<Blake2bHash>) - Blake2b hash of the attachment content

## Processing Pipeline

### Data Transformation Flow

1. **Raw Data Ingestion**
   - Raw cases are submitted via API or fetched from sources
   - Stored in S3 as raw objects (`objects_raw/{country}/{state}/{jurisdiction}/{case_name}.json`)

2. **Processing**
   - Raw data is transformed to processed format using `ProcessFrom` trait
   - Date validation and normalization
   - Author name parsing and cleaning
   - Attachment matching and indexing
   - Processed data is stored in S3 (`objects/{country}/{state}/{jurisdiction}/{case_name}.json`)

3. **Attachment Processing**
   - Attachments without hashes are downloaded
   - Content is processed and stored separately
   - Metadata and file content are stored in S3

### Key Processing Traits (src/types/data_processing_traits.rs)

#### ProcessFrom<T>
Transforms raw data type `T` into processed format.

```rust
pub trait ProcessFrom<T> {
    type ParseError: Error;
    type ExtraData;
    async fn process_from(
        input: T,
        cached: Option<Self>,
        extra_data: Self::ExtraData,
    ) -> Result<Self, Self::ParseError>
    where
        Self: Sized;
}
```

#### DownloadIncomplete
Downloads incomplete data (e.g., attachments without content).

```rust
pub trait DownloadIncomplete {
    type ExtraData;
    type SucessData;
    async fn download_incomplete(
        &mut self,
        extra: &Self::ExtraData,
    ) -> anyhow::Result<Self::SucessData>;
}
```

#### Revalidate
Revalidates and corrects processed data.

```rust
pub trait Revalidate {
    fn revalidate(&mut self) {}
}
```

## S3 Storage Structure

### Raw Objects
- Path: `objects_raw/{country}/{state}/{jurisdiction}/{case_name}.json`
- Contains: Raw case data as submitted

### Processed Objects
- Path: `objects/{country}/{state}/{jurisdiction}/{case_name}.json`
- Contains: Processed case data with standardized format

### Raw Attachments
- Metadata: `raw/metadata/{hash}.json`
- File Content: `raw/file/{hash}`