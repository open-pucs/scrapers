export interface GenericAttachment {
    name: string;
    document_extension: string;
    url: string;
    attachment_type: string;
    attachment_subtype: string;
    extra_metadata: { [key: string]: any };
    hash?: string | null;
}

export interface GenericFiling {
    name: string;
    filed_date: string; // or Date
    organization_authors: string[];
    individual_authors: string[];
    filing_type: string;
    description: string;
    attachments: GenericAttachment[];
    extra_metadata: { [key: string]: any };
}

export interface GenericParty {
    name: string;
    is_corperate_entity: boolean;
    is_human: boolean;
}

export interface GenericCase {
    case_govid: string;
    opened_date?: string | null; // or Date
    case_name: string;
    case_url: string;
    case_type: string;
    description: string;
    industry: string;
    petitioner: string;
    hearing_officer: string;
    closed_date?: string | null; // or Date
    filings: GenericFiling[];
    case_parties: GenericParty[];
    extra_metadata: { [key: string]: any };
}

export interface JurisdictionInfo {
    country: string;
    state: string;
    jurisdiction: string;
}

export interface CaseWithJurisdiction {
    case: GenericCase;
    jurisdiction: JurisdictionInfo;
}
