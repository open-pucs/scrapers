use std::{
    any::{Any, TypeId},
    cmp::Ordering,
    collections::{BinaryHeap, HashMap},
    convert::Infallible,
    sync::LazyLock,
    time::{Duration, Instant},
};

use aide::{
    axum::{ApiRouter, IntoApiResponse, routing::get_with},
    transform::TransformOperation,
};
use async_trait::async_trait;
use axum::{Json, extract::Path, response::IntoResponse};
use rand::random;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use tokio::{
    sync::{Mutex, RwLock, Semaphore},
    time::sleep,
};
use tracing::{Instrument, info};

struct PriorityTaskObject {
    priority: i32,
    timestamp: Instant,
    task_id: u64,
    task_object: Box<dyn ExecuteUserTask>,
}
impl PriorityTaskObject {
    pub fn new(obj: Box<dyn ExecuteUserTask>, priority: i32) -> Self {
        Self::new_with_id(obj, priority, random())
    }
    pub fn new_with_id(obj: Box<dyn ExecuteUserTask>, priority: i32, id: u64) -> Self {
        PriorityTaskObject {
            priority,
            task_object: obj,
            timestamp: Instant::now(),
            task_id: id,
        }
    }
    pub fn get_task_type(&self) -> TypeId {
        (*self.task_object).type_id()
    }
    pub fn get_task_type_string(&self) -> String {
        typeid_debug(self.get_task_type())
    }
}
pub fn typeid_debug(t: TypeId) -> String {
    format!("{t:?}")
}

impl PartialEq for PriorityTaskObject {
    fn eq(&self, other: &Self) -> bool {
        self.priority == other.priority
            && self.timestamp == other.timestamp
            && self.task_id == other.task_id
    }
}
impl Eq for PriorityTaskObject {}

/* -------------------------- Ordering ------------------------------------- */

impl PartialOrd for PriorityTaskObject {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        // The total ordering is defined in `Ord::cmp`, so we just forward to it.
        Some(self.cmp(other))
    }
}

impl Ord for PriorityTaskObject {
    fn cmp(&self, other: &Self) -> Ordering {
        // 1️⃣  Higher `priority` wins → normal `i32::cmp`.
        // 2️⃣  Earlier (`lower`) timestamp wins → reverse the `Instant` ordering.
        // 3️⃣  Larger `task_id` wins → normal `u64::cmp` (deterministic tie‑breaker).
        self.priority
            .cmp(&other.priority)
            .then_with(|| other.timestamp.cmp(&self.timestamp)) // reverse
            .then_with(|| self.task_id.cmp(&other.task_id))
    }
}

static TASK_PRIORITY_QUEUE: Mutex<BinaryHeap<PriorityTaskObject>> =
    Mutex::const_new(BinaryHeap::new());

static TASK_STATUS_DATA: LazyLock<RwLock<HashMap<u64, TaskStatus>>> =
    LazyLock::new(|| RwLock::new(HashMap::new()));

pub async fn add_task_to_queue(obj: Box<dyn ExecuteUserTask>, priority: i32) -> TaskStatus {
    let task_object = PriorityTaskObject::new(obj, priority);
    let task_id = task_object.task_id;
    let task_status = TaskStatus::new(task_id, &*(task_object.task_object));
    let mut task_status_writelock = (*TASK_STATUS_DATA).write().await;
    task_status_writelock.insert(task_id, task_status.clone());
    drop(task_status_writelock);

    let mut queue_guard = TASK_PRIORITY_QUEUE.lock().await;
    queue_guard.push(task_object);
    drop(queue_guard);
    task_status
}

async fn pop_task_from_queue() -> Option<PriorityTaskObject> {
    let mut queue_guard = TASK_PRIORITY_QUEUE.lock().await;
    let option = queue_guard.pop();
    drop(queue_guard);
    match option {
        None => None,
        Some(val) => {
            let mut task_status_writelock = (*TASK_STATUS_DATA).write().await;
            let optref = task_status_writelock.get_mut(&val.task_id);
            if let Some(mutref) = optref {
                mutref.status = TaskState::Processing
            };
            Some(val)
        }
    }
}

const SIMULTANEOUS_USER_TASKS: usize = 20;
static USER_TASK_SEMAPHORE: Semaphore = Semaphore::const_new(SIMULTANEOUS_USER_TASKS);

pub async fn start_workers() -> Infallible {
    let mut trips_since_last_task: u64 = 0;
    loop {
        let permit = USER_TASK_SEMAPHORE.acquire().await.unwrap();
        match pop_task_from_queue().await {
            None => {
                trips_since_last_task += 1;
                if trips_since_last_task.is_power_of_two() {
                    info!(seconds=%trips_since_last_task,"Have not gotten a new task dispite waiting at least n seconds.")
                }
                drop(permit);
                sleep(Duration::from_secs(1)).await
            }
            Some(res) => {
                tokio::spawn(async move {
                    let task_id = res.task_id;
                    let obj = res.task_object;
                    let task_status_readlock = (*TASK_STATUS_DATA).read().await;
                    let mut task_obj = task_status_readlock
                        .get(&task_id)
                        .cloned()
                        .unwrap_or_else(|| TaskStatus::new(task_id, &*obj));
                    drop(task_status_readlock);
                    obj.execute_task_raw(&mut task_obj).await;

                    let mut task_status_writelock = (*TASK_STATUS_DATA).write().await;
                    task_status_writelock.insert(task_id, task_obj);
                    drop(task_status_writelock);
                    drop(permit);
                });
            }
        }
    }
}

pub fn spawn_worker_loop() {
    tokio::spawn(start_workers().in_current_span());
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
        return TaskStatus {
            task_id,
            task_type_label: obj.get_task_label(),
            status: TaskState::Waiting,
            return_value: None,
        };
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

const CHECK_TASK_URL_LEAF: &str = "/tasks/check_status";

#[derive(Clone, Copy, Serialize, Deserialize, JsonSchema)]
pub struct TaskIDNumber {
    task_id: u64,
}
pub async fn check_task_status(
    Path(TaskIDNumber { task_id }): Path<TaskIDNumber>,
) -> impl IntoApiResponse {
    let read_guard = (*TASK_STATUS_DATA).read().await;
    let status = read_guard.get(&task_id).cloned();
    drop(read_guard);
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
