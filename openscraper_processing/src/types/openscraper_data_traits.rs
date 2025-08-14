use std::collections::HashMap;

use chrono::NaiveDate;

use crate::types::{
    data_processing_traits::{Revalidate, UpdateFromCache},
    openscraper_types::{GenericAttachment, GenericCase, GenericFiling},
};

impl Revalidate for GenericCase {
    fn revalidate(&mut self) {
        if self.opened_date.is_some() {
            return;
        }
        let mut opened_date = NaiveDate::MAX;
        for filling in &self.filings {
            if filling.filed_date < opened_date {
                opened_date = filling.filed_date
            }
        }
        self.opened_date = Some(opened_date);
        for filling in &mut self.filings {
            filling.revalidate();
        }
    }
}

impl Revalidate for GenericFiling {
    fn revalidate(&mut self) {
        if !self.name.is_empty() {
            return;
        }
        if let Some(attach) = self.attachments.first() {
            self.name = attach.name.clone().into();
        }
    }
}

// Cache update logic
impl UpdateFromCache for GenericAttachment {
    fn update_from_cache(&mut self, cache: &Self) {
        if self.hash.is_none() {
            self.hash = cache.hash
        }
    }
}

impl UpdateFromCache for GenericFiling {
    fn update_from_cache(&mut self, cache: &Self) {
        let url_map = cache
            .attachments
            .iter()
            .map(|att| (&*att.url, att))
            .collect::<HashMap<_, _>>();
        for attach in self.attachments.iter_mut() {
            if let Some(attach_cache) = url_map.get(&*attach.url) {
                attach.update_from_cache(attach_cache);
            }
        }
    }
}
