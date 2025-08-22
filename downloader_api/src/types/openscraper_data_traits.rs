use std::mem;
use std::{collections::HashMap, convert::Infallible};

use chrono::NaiveDate;
use futures_util::{StreamExt, join, stream};

use mycorrhiza_common::llm_deepinfra::guess_at_filling_title;

use crate::types::{
    data_processing_traits::{ReParse, Revalidate, UpdateFromCache},
    raw::{RawGenericAttachment, RawGenericCase, RawGenericFiling},
};
use mycorrhiza_common::llm_deepinfra::split_mutate_author_list;

impl Revalidate for RawGenericCase {
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

impl Revalidate for RawGenericFiling {
    fn revalidate(&mut self) {
        self.organization_authors = mem::take(&mut self.organization_authors)
            .into_iter()
            .filter(|x| !x.is_empty())
            .collect();
        self.individual_authors = mem::take(&mut self.individual_authors)
            .into_iter()
            .filter(|x| !x.is_empty())
            .collect();
        // Name stuff
        if !self.name.is_empty() {
            return;
        }
        if let Some(attach) = self.attachments.first() {
            self.name = attach.name.clone();
        }
    }
}

impl ReParse for RawGenericCase {
    type ParseError = Infallible;
    async fn re_parse(&mut self) -> Result<(), Self::ParseError> {
        // Call re_parse on each of the fillings, and await the futures all at once
        let futs = self.filings.iter_mut().map(ReParse::re_parse);
        stream::iter(futs).buffer_unordered(40).count().await;
        Ok(())
    }
}
impl ReParse for RawGenericFiling {
    type ParseError = Infallible;
    async fn re_parse(&mut self) -> Result<(), Self::ParseError> {
        async fn replace_name(nameref: &mut String, attaches: &[RawGenericAttachment]) {
            if nameref.is_empty() {
                let attach_names = attaches.iter().map(|f| &*f.name).collect::<Vec<_>>();
                let guess = guess_at_filling_title(&attach_names).await;
                *nameref = guess;
            }
        }
        let _x = join!(
            replace_name(&mut self.name, &self.attachments),
            split_mutate_author_list(&mut self.organization_authors),
            split_mutate_author_list(&mut self.individual_authors),
        );

        Ok(())
    }
}

// Cache update logic
impl UpdateFromCache for RawGenericAttachment {
    fn update_from_cache(&mut self, cache: &Self) {
        if self.hash.is_none() {
            self.hash = cache.hash
        }
    }
}

impl UpdateFromCache for RawGenericFiling {
    fn update_from_cache(&mut self, cache: &Self) {
        let cache_urls = cache
            .attachments
            .iter()
            .map(|att| (&*att.url, att))
            .collect::<HashMap<_, _>>();
        for attach in self.attachments.iter_mut() {
            if !attach.url.is_empty()
                && let Some(cache_attach) = cache_urls.get(&*attach.url)
            {
                attach.update_from_cache(cache_attach);
            }
        }
    }
}

impl UpdateFromCache for RawGenericCase {
    fn update_from_cache(&mut self, cache: &Self) {
        let mut cache_urls = HashMap::new();
        for filling in cache.filings.iter() {
            for attach in filling.attachments.iter() {
                cache_urls.insert(&*attach.url, attach);
            }
        }
        for filling in self.filings.iter_mut() {
            for attach in filling.attachments.iter_mut() {
                if !attach.url.is_empty()
                    && let Some(cache_attach) = cache_urls.get(&*attach.url)
                {
                    attach.update_from_cache(cache_attach);
                }
            }
        }

        // Old approach that compars on file name and other metadata instead of just using the urls for all attachments
        // in a filling.
        // type ToCompare<'a> = (&'a NaiveDate, usize, &'a str, &'a str); // Date filed,number of attachments, Name, Description,
        // fn make_compare(filling: &GenericFiling) -> ToCompare<'_> {
        //     (
        //         &filling.filed_date,
        //         filling.attachments.len(),
        //         &filling.name,
        //         &filling.description,
        //     )
        // }
        // let filling_comparison = cache
        //     .filings
        //     .iter()
        //     .map(|f| (make_compare(f), f))
        //     .collect::<HashMap<_, _>>();
        // for filling in self.filings.iter_mut() {
        //     if let Some(cached_filling) = filling_comparison.get(&make_compare(filling)) {
        //         filling.update_from_cache(cached_filling);
        //     }
        // }
    }
}
