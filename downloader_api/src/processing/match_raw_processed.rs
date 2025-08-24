use std::collections::HashMap;

use crate::types::{
    processed::{ProcessedGenericAttachment, ProcessedGenericFiling},
    raw::{RawGenericAttachment, RawGenericFiling},
};

pub fn match_raw_attaches_to_processed_attaches<'a>(
    raw_attaches: &'a [RawGenericAttachment],
    processed_attaches: Option<&'a HashMap<u64, ProcessedGenericAttachment>>,
) -> Vec<(
    &'a RawGenericAttachment,
    Option<&'a ProcessedGenericAttachment>,
)> {
    // the raw generic attachments and the processed attachments each
    let Some(processed_attaches) = processed_attaches else {
        return raw_attaches.iter().map(|att| (att, None)).collect();
    };
    let mut temporary_map: HashMap<u64, &'a _> =
        processed_attaches.iter().map(|(k, v)| (*k, v)).collect();
    let mut return_vec = Vec::with_capacity(raw_attaches.len());
    for attach in raw_attaches {
        let processed_option = match_individual_attach(attach, &temporary_map);
        return_vec.push((attach, processed_option));
        if let Some(processed_actual) = processed_option {
            temporary_map.remove(&processed_actual.openscrapers_attachment_id);
        }
    }
    return_vec
}

fn match_individual_attach<'a>(
    raw_attachment: &'a RawGenericAttachment,
    processed_attaches: &HashMap<u64, &'a ProcessedGenericAttachment>,
) -> Option<&'a ProcessedGenericAttachment> {
    let govid = &*raw_attachment.attachment_govid;
    todo!();
    None
}
fn match_raw_fillings_to_processed_fillings<'a>(
    raw_fillings: &'a [RawGenericFiling],
    processed_fillings: Option<&'a HashMap<u64, ProcessedGenericFiling>>,
) -> Vec<(&'a RawGenericFiling, Option<&'a ProcessedGenericFiling>)> {
    let Some(processed_fillings) = processed_fillings else {
        return raw_fillings.iter().map(|filling| (filling, None)).collect();
    };
    let mut temporary_map: HashMap<u64, &'a _> =
        processed_fillings.iter().map(|(k, v)| (*k, v)).collect();
    let mut return_vec = Vec::with_capacity(raw_fillings.len());
    for attach in raw_fillings {
        let processed_option = match_individual_filling(attach, &temporary_map);
        return_vec.push((attach, processed_option));
        if let Some(processed_actual) = processed_option {
            temporary_map.remove(&processed_actual.openscrapers_filling_id);
        }
    }
    return_vec
}
fn match_individual_filling<'a>(
    raw_attachment: &'a RawGenericFiling,
    processed_attaches: &HashMap<u64, &'a ProcessedGenericFiling>,
) -> Option<&'a ProcessedGenericFiling> {
    let govid = &*raw_attachment.filling_govid;
    todo!();
    None
}
