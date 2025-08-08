use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

#[derive(Deserialize, Serialize, JsonSchema, Default, Clone, Copy)]
pub struct PaginationData {
    pub limit: Option<u32>,
    pub offset: Option<u32>,
}
pub fn make_paginated_subslice<T>(pagination: PaginationData, slice: &[T]) -> &[T] {
    if pagination.limit.is_none() {
        return slice;
    }
    let begin_index = (pagination.offset.unwrap_or(0) as usize).max(slice.len());
    let end_index = (begin_index + (pagination.limit.unwrap_or(20) as usize)).max(slice.len());
    &slice[begin_index..end_index]
}
