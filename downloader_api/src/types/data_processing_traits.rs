use std::error::Error;

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum RevalidationOutcome {
    NoChanges,
    DidChange,
    Invalid,
}

impl RevalidationOutcome {
    pub fn or(&self, other: &Self) -> Self {
        match self {
            Self::NoChanges => *other,
            Self::Invalid => Self::Invalid,
            Self::DidChange => {
                if *other == Self::Invalid {
                    Self::Invalid
                } else {
                    Self::DidChange
                }
            }
        }
    }
    pub fn did_change(&self) -> bool {
        match self {
            Self::NoChanges => false,
            _ => true,
        }
    }
}
pub trait Revalidate {
    async fn revalidate(&mut self) -> RevalidationOutcome;
}

pub trait ProcessFrom<T> {
    type ParseError: Error;
    type ExtraData;
    async fn process_from(
        input: T,
        cached: Option<Self>,
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
