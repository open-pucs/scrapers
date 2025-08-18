use aide::{
    axum::{
        ApiRouter, IntoApiResponse,
        routing::{get_with, post},
    },
    transform::TransformOperation,
};
use axum::{Json, extract::Path, response::IntoResponse};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

use crate::common::tasks::workers::{add_task_to_queue_and_wait_to_see_if_done, read_task_status};
use std::time::Duration;

use super::{ExecuteUserTask, TaskStatusDisplay, workers::add_task_to_queue};
pub const CHECK_TASK_URL_LEAF: &str = "/tasks";

#[derive(Clone, Copy, Serialize, Deserialize, JsonSchema)]
pub struct TaskIDNumber {
    task_id: u64,
}
pub async fn check_task_status(
    Path(TaskIDNumber { task_id }): Path<TaskIDNumber>,
) -> impl IntoApiResponse {
    let status = read_task_status(task_id).await;
    match status {
        None => (axum::http::StatusCode::NOT_FOUND, format!("Could not find task with task_id: {task_id}")).into_response()
, // Return a 404 error with an error string "Could not find task with that id"
        Some(status) => {
            let display_status: TaskStatusDisplay = status.into();
            // Return a 200 code with the status that wants to be returned.
(axum::http::StatusCode::OK, Json(display_status)).into_response()
        }
    }
}

pub fn check_task_status_docs(op: TransformOperation) -> TransformOperation {
    op.description("Fetch attachment data from S3.")
        .response::<200, Json<TaskStatusDisplay>>()
        .response_with::<404, String, _>(|res| {
            res.description("Could not find task with that task_id")
        })
}

pub fn define_generic_task_routes(router: ApiRouter) -> ApiRouter {
    let check_path = CHECK_TASK_URL_LEAF.to_string() + "/{task_id}";
    router.api_route(
        &check_path,
        get_with(check_task_status, check_task_status_docs),
    )
}

#[derive(Clone, Copy, Default, Serialize, Deserialize, JsonSchema)]
pub struct PriorityExtractor {
    pub priority: i32,
}

#[derive(Deserialize, JsonSchema)]
pub struct GeneralExtractor<T: JsonSchema + ExecuteUserTask> {
    #[serde(default)]
    pub priority: Option<i32>,
    pub object: T,
}

pub async fn handle_generic_task_route<
    T: for<'de> Deserialize<'de> + JsonSchema + ExecuteUserTask,
>(
    Json(extractor): Json<GeneralExtractor<T>>,
) -> Json<TaskStatusDisplay> {
    const WAIT_DURATION: Duration = Duration::from_secs(2);
    let obj = extractor.object;
    let priority = extractor.priority.unwrap_or(0);
    let taskinfo = add_task_to_queue_and_wait_to_see_if_done(obj, priority, WAIT_DURATION).await;
    Json(taskinfo.into())
}

pub fn declare_task_route<T: for<'de> Deserialize<'de> + JsonSchema + ExecuteUserTask>(
    router: ApiRouter,
) -> ApiRouter {
    router.api_route(
        &format!("/tasks/types/{}", T::get_task_label_static()),
        post(handle_generic_task_route::<T>),
    )
}
