use std::collections::HashMap;

use crate::types::{
    processed::{ProcessedGenericAttachment, ProcessedGenericFiling},
    raw::{RawGenericAttachment, RawGenericFiling},
};

pub fn match_raw_attaches_to_processed_attaches(
    raw_attaches: Vec<RawGenericAttachment>,
    processed_attaches: Option<HashMap<u64, ProcessedGenericAttachment>>,
) -> Vec<(RawGenericAttachment, Option<ProcessedGenericAttachment>)> {
    // the raw generic attachments and the processed attachments each
    let Some(mut processed_attaches) = processed_attaches else {
        return raw_attaches.into_iter().map(|att| (att, None)).collect();
    };
    let mut return_vec = Vec::with_capacity(raw_attaches.len());
    for attach in raw_attaches {
        let processed_option = match_individual_attach(&attach, &processed_attaches);
        if let Some(processed_actual) = processed_option {
            let attach_id = processed_actual.openscrapers_attachment_id;
            let proc_attach_owned = processed_attaches.remove(&attach_id);
            return_vec.push((attach, proc_attach_owned))
        } else {
            return_vec.push((attach, None))
        }
    }
    return_vec
}

fn match_individual_attach<'a>(
    raw_attachment: &RawGenericAttachment,
    processed_attaches: &'a HashMap<u64, ProcessedGenericAttachment>,
) -> Option<&'a ProcessedGenericAttachment> {
    let govid = &*raw_attachment.attachment_govid;
    if !govid.is_empty() {
        // iterate through the list and find the correct result.
        let found_result = processed_attaches.iter().find_map(|(_, attach)| {
            match attach.attachment_govid == govid {
                false => None,
                true => Some(attach),
            }
        });
        return found_result;
    }
    None
}
pub fn match_raw_fillings_to_processed_fillings(
    raw_fillings: Vec<RawGenericFiling>,
    processed_fillings: Option<HashMap<u64, ProcessedGenericFiling>>,
) -> Vec<(RawGenericFiling, Option<ProcessedGenericFiling>)> {
    let Some(mut processed_fillings) = processed_fillings else {
        return raw_fillings
            .into_iter()
            .map(|filling| (filling, None))
            .collect();
    };
    let mut return_vec = Vec::with_capacity(raw_fillings.len());
    for attach in raw_fillings {
        let processed_option = match_individual_filling(&attach, &processed_fillings);

        if let Some(processed_actual) = processed_option {
            let attach_id = processed_actual.openscrapers_filling_id;
            let proc_attach_owned = processed_fillings.remove(&attach_id);
            return_vec.push((attach, proc_attach_owned))
        } else {
            return_vec.push((attach, None))
        }
    }
    return_vec
}
fn match_individual_filling<'a>(
    raw_filling: &RawGenericFiling,
    processed_fillings: &'a HashMap<u64, ProcessedGenericFiling>,
) -> Option<&'a ProcessedGenericFiling> {
    let govid = &*raw_filling.filling_govid;
    if !govid.is_empty() {
        // iterate through the hashmap and find the correct result.
        let found_result = processed_fillings.iter().find_map(|(_, filling)| {
            match filling.filling_govid == govid {
                false => None,
                true => Some(filling),
            }
        });
        return found_result;
    }
    None
}
