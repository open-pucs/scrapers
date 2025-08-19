use async_trait::async_trait;
use routing::CHECK_TASK_URL_LEAF;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
pub mod routing;
pub mod workers;

pub fn display_error_as_json(err: &impl std::error::Error) -> serde_json::Value {
    json!({
        "error_string":err.to_string(),
        "error_debug": format!("{:?}", err),
        "error_type": std::any::type_name_of_val(err)
    })
}

#[async_trait]
pub trait ExecuteUserTask: 'static + Send {
    async fn execute_task(self: Box<Self>) -> Result<Value, Value>;
    async fn execute_task_raw(self: Box<Self>, status: &mut TaskStatus) {
        let return_result = self.execute_task().await;
        let status_val = match return_result {
            Ok(_) => TaskState::Successful,
            Err(_) => TaskState::Errored,
        };
        status.status = status_val;
        status.return_value = Some(return_result);
    }
    fn get_task_label_static() -> &'static str
    where
        Self: Sized;
    fn get_task_label(&self) -> &'static str;
}

#[derive(Clone, Copy, Serialize, Deserialize, JsonSchema, Debug, PartialEq, Eq)]
pub enum TaskState {
    Waiting,
    Processing,
    Successful,
    Errored,
}
impl TaskState {
    pub fn is_completed(&self) -> bool {
        (*self == Self::Successful) || (*self == Self::Errored)
    }
}

#[derive(Clone, Debug)]
pub struct TaskStatus {
    pub task_id: u64,
    pub status: TaskState,
    pub task_type_label: &'static str,
    pub return_value: Option<Result<Value, Value>>,
}
impl TaskStatus {
    fn new(task_id: u64, obj: &dyn ExecuteUserTask) -> Self {
        TaskStatus {
            task_id,
            task_type_label: obj.get_task_label(),
            status: TaskState::Waiting,
            return_value: None,
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize, JsonSchema)]
pub struct TaskStatusDisplay {
    task_id: u64,
    status: TaskState,
    completed: bool,
    task_type_label: &'static str,
    check_url_leaf: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    sucess_info: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error_info: Option<Value>,
}

impl From<TaskStatus> for TaskStatusDisplay {
    fn from(value: TaskStatus) -> Self {
        let (success_val, err_val) = match value.return_value {
            None => (None, None),
            Some(Ok(success)) => (Some(success), None),
            Some(Err(error)) => (None, Some(error)),
        };
        let url_leaf = format!("{CHECK_TASK_URL_LEAF}/{}", value.task_id);

        TaskStatusDisplay {
            task_id: value.task_id,
            status: value.status,
            check_url_leaf: url_leaf,
            completed: value.status.is_completed(),
            task_type_label: value.task_type_label,
            sucess_info: success_val,
            error_info: err_val,
        }
    }
}
