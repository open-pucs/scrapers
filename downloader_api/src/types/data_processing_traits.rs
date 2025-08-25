use std::error::Error;
pub trait Revalidate {
    fn revalidate(&mut self) {}
}

pub trait ProcessFrom<T> {
    type ParseError: Error;
    type ExtraData;
    async fn process_from(
        input: &T,
        cached: Option<&Self>,
        extra_data: Self::ExtraData,
    ) -> Result<Self, Self::ParseError>
    where
        Self: Sized;
}

pub trait DownloadIncomplete {
    type ExtraData;
    type SucessData;
    async fn download_incomplete(
        &mut self,
        extra: &Self::ExtraData,
    ) -> anyhow::Result<Self::SucessData>;
}
