export interface JurisdictionInfo {
  country: string;
  state: string;
  jurisdiction: string;
}

export enum RawArtificalPersonType {
  Unknown = "unknown",
  Human = "human",
  Organization = "organization",
}

export interface RawGenericParty {
  name: string;
  artifical_person_type: RawArtificalPersonType;
  western_human_first_name: string;
  western_human_last_name: string;
  human_title: string;
  human_associated_company: string;
  contact_email: string;
  contact_phone: string;
  contact_address: string;
}

export interface RawGenericAttachment {
  name: string;
  document_extension: string; // This is a FileExtension in rust
  attachment_govid: string;
  url: string;
  attachment_type: string;
  attachment_subtype: string;
  extra_metadata: { [key: string]: any };
  hash?: string | null; // This is a Option<Blake2bHash> in rust
}

export interface RawGenericFiling {
  filed_date?: string | null; // or Date
  filling_govid: string;
  name: string;
  organization_authors: string[];
  individual_authors: string[];
  organization_authors_blob: string;
  individual_authors_blob: string;
  filing_type: string;
  description: string;
  attachments: RawGenericAttachment[];
  extra_metadata: { [key: string]: any };
}

export interface RawGenericDocket {
  case_govid: string; // This is a NonEmptyString in rust
  opened_date?: string | null; // or Date
  case_name: string;
  case_url: string;
  case_type: string;
  case_subtype: string;
  description: string;
  industry: string;
  petitioner: string;
  hearing_officer: string;
  closed_date?: string | null; // or Date
  filings: RawGenericFiling[];
  case_parties: RawGenericParty[];
  extra_metadata: { [key: string]: any };
  indexed_at: string; // This is a DateTime<Utc> in rust
}

export interface RawDocketWithJurisdiction {
  docket: RawGenericDocket;
  jurisdiction: JurisdictionInfo;
}
