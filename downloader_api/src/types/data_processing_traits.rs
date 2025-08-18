use std::error::Error;
pub trait Revalidate {
    fn revalidate(&mut self) {}
}

pub trait ReParse: Revalidate {
    type ParseError: Error;
    async fn re_parse(&mut self) -> Result<(), Self::ParseError>;
}

pub trait UpdateFromCache {
    fn update_from_cache(&mut self, cache: &Self);
}

pub trait DownloadIncomplete {
    type ExtraData;
    type SucessData;
    async fn download_incomplete(
        &mut self,
        extra: &Self::ExtraData,
    ) -> anyhow::Result<Self::SucessData>;
}
