pub trait Revalidate {
    fn revalidate(&mut self) {}
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
