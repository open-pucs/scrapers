use std::{collections::HashMap, convert::Infallible};

use chrono::{NaiveDate, Utc};
use futures_util::{StreamExt, stream};
use rand::random;
use tracing::warn;

use crate::processing::llm_prompts::{clean_up_author_list, split_and_fix_author_blob};
use crate::processing::match_raw_processed::{
    match_raw_attaches_to_processed_attaches, match_raw_fillings_to_processed_fillings,
};
use crate::types::processed::{
    ProcessedGenericAttachment, ProcessedGenericDocket, ProcessedGenericFiling,
};
use crate::types::{
    data_processing_traits::{ProcessFrom, Revalidate},
    raw::{RawGenericAttachment, RawGenericDocket, RawGenericFiling},
};

impl Revalidate for ProcessedGenericDocket {
    fn revalidate(&mut self) {
        for (_, filling) in &mut self.filings.iter_mut() {
            filling.revalidate();
        }
    }
}

impl Revalidate for ProcessedGenericFiling {
    fn revalidate(&mut self) {
        // Name stuff
        if !self.name.is_empty() {
            return;
        }
        for (_, attach) in self.attachments.iter() {
            if !attach.name.is_empty() {
                self.name = attach.name.clone();
                return;
            }
        }
    }
}

impl ProcessFrom<RawGenericDocket> for ProcessedGenericDocket {
    type ParseError = Infallible;
    type ExtraData = ();
    async fn process_from(
        input: RawGenericDocket,
        cached: Option<Self>,
        _: Self::ExtraData,
    ) -> Result<Self, Self::ParseError> {
        let opened_date_from_fillings = {
            let original_date = input.opened_date;
            let mut min_date = original_date;
            for filling_date in input
                .filings
                .iter()
                .filter_map(|filling| filling.filed_date)
            {
                if let Some(real_min_date) = min_date
                    && filling_date < real_min_date
                {
                    min_date = Some(filling_date);
                    if let Some(real_original_date) = original_date {
                        warn!(docket_opened_date =%real_original_date, oldest_date_found=%filling_date,"Found filling with date older then the docket opened date");
                    };
                };
            }
            // This should almost never happen, because the chances of corruption happening on the
            // docket date, and all the filling dates are very small.
            min_date.unwrap_or(NaiveDate::MAX)
        };
        let cached_fillings = cached.map(|d| d.filings);
        let matched_fillings =
            match_raw_fillings_to_processed_fillings(input.filings, cached_fillings);
        let processed_fillings = stream::iter(matched_fillings.into_iter())
            .enumerate()
            .map(|(index, (f_raw, f_cached))| {
                let filling_index_data = IndexExtraData {
                    index: index as u64,
                };
                async {
                    ProcessedGenericFiling::process_from(f_raw, f_cached, filling_index_data).await
                }
            })
            .buffer_unordered(5)
            .collect::<Vec<_>>()
            .await;
        let mut proc_filling_map = HashMap::new();
        for filling in processed_fillings {
            // Destructure here is fine since the filling process cannot error out.
            let Ok(filling) = filling;
            proc_filling_map.insert(filling.openscrapers_filling_id, filling);
        }
        let final_processed_docket = ProcessedGenericDocket {
            processed_at: Utc::now(),
            case_govid: input.case_govid.clone(),
            filings: proc_filling_map,
            opened_date: opened_date_from_fillings,
            case_name: input.case_name.clone(),
            case_url: input.case_url.clone(),
            industry: input.industry.clone(),
            case_type: input.case_type.clone(),
            case_subtype: input.case_subtype.clone(),
            indexed_at: input.indexed_at,
            closed_date: input.closed_date,
            case_parties: input.case_parties.clone(),
            description: input.description.clone(),
            extra_metadata: input.extra_metadata.clone(),
            hearing_officer: input.hearing_officer.clone(),
            petitioner: input.petitioner.clone(),
        };
        Ok(final_processed_docket)
    }
}
impl ProcessFrom<RawGenericFiling> for ProcessedGenericFiling {
    type ParseError = Infallible;
    type ExtraData = IndexExtraData;
    async fn process_from(
        input: RawGenericFiling,
        cached: Option<Self>,
        index_data: Self::ExtraData,
    ) -> Result<Self, Self::ParseError> {
        let (processed_attach_map, cached_orgauthorlist, cached_individualauthorllist) =
            match cached {
                Some(filling) => (
                    Some(filling.attachments),
                    Some(filling.organization_authors),
                    Some(filling.individual_authors),
                ),
                None => (None, None, None),
            };
        let matched_attach_list =
            match_raw_attaches_to_processed_attaches(input.attachments, processed_attach_map);
        // Async match the raw attachments with the cached versions, and process them async 5 at a
        // time.
        let processed_attachments = stream::iter(matched_attach_list.into_iter())
            .enumerate()
            .map(|(attach_index, (raw_attach, cached_attach))| {
                let attach_index_data = IndexExtraData {
                    index: attach_index as u64,
                };
                async {
                    ProcessedGenericAttachment::process_from(
                        raw_attach,
                        cached_attach,
                        attach_index_data,
                    )
                    .await
                }
            })
            .buffer_unordered(5)
            .collect::<Vec<_>>()
            .await;
        let mut proc_attach_map = HashMap::new();
        for attach in processed_attachments {
            let Ok(attach) = attach;
            proc_attach_map.insert(attach.openscrapers_attachment_id, attach);
        }
        // Process org and individual author names.
        let organization_authors = {
            if let Some(org_authors) = cached_orgauthorlist {
                org_authors
            } else if input.organization_authors.is_empty() {
                split_and_fix_author_blob(&input.organization_authors_blob).await
            } else {
                clean_up_author_list(input.organization_authors)
            }
        };

        let individual_authors = {
            if let Some(individual_authors) = cached_individualauthorllist {
                individual_authors
            } else if input.individual_authors.is_empty() {
                split_and_fix_author_blob(&input.individual_authors_blob).await
            } else {
                clean_up_author_list(input.individual_authors)
            }
        };

        let proc_filling = Self {
            openscrapers_filling_id: index_data.index,
            filed_date: input.filed_date,
            index_in_docket: index_data.index,
            attachments: proc_attach_map,
            name: input.name.clone(),
            filling_govid: input.filling_govid.clone(),
            filing_type: input.filing_type.clone(),
            description: input.description.clone(),
            extra_metadata: input.extra_metadata.clone(),
            organization_authors,
            individual_authors,
        };
        Ok(proc_filling)
    }
}

pub struct IndexExtraData {
    index: u64,
}
impl ProcessFrom<RawGenericAttachment> for ProcessedGenericAttachment {
    type ParseError = Infallible;
    type ExtraData = IndexExtraData;
    async fn process_from(
        input: RawGenericAttachment,
        cached: Option<Self>,
        index_data: Self::ExtraData,
    ) -> Result<Self, Self::ParseError> {
        let id = cached
            .as_ref()
            .map(|val| val.openscrapers_attachment_id)
            .unwrap_or(random());
        let hash = (input.hash).or_else(|| cached.and_then(|v| v.hash));
        let return_res = Self {
            openscrapers_attachment_id: id,
            index_in_filling: index_data.index,
            name: input.name.clone(),
            document_extension: input.document_extension.clone(),
            attachment_govid: input.attachment_govid.clone(),
            attachment_type: input.attachment_type.clone(),
            attachment_subtype: input.attachment_subtype.clone(),
            url: input.url.clone(),
            extra_metadata: input.extra_metadata.clone(),
            hash,
        };
        Ok(return_res)
    }
}
