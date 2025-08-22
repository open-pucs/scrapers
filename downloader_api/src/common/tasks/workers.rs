use std::{
    any::TypeId,
    cmp::Ordering,
    collections::{BinaryHeap, HashMap},
    convert::Infallible,
    env,
    sync::LazyLock,
    time::{Duration, Instant},
};

use rand::random;
use tokio::{
    sync::{Mutex, RwLock, Semaphore},
    time::sleep,
};
use tracing::{Instrument, info};

use crate::common::misc::prettyprint_duration;

use super::{ExecuteUserTask, TaskState, TaskStatus};

pub struct PriorityTaskObject {
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
    pub fn get_task_type_label(&self) -> &'static str {
        self.task_object.get_task_label()
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

pub static TASK_PRIORITY_QUEUE: Mutex<BinaryHeap<PriorityTaskObject>> =
    Mutex::const_new(BinaryHeap::new());

pub static TASK_STATUS_DATA: LazyLock<RwLock<HashMap<u64, TaskStatus>>> =
    LazyLock::new(|| RwLock::new(HashMap::new()));

pub async fn add_task_to_queue(obj: impl ExecuteUserTask, priority: i32) -> TaskStatus {
    let boxed_obj = Box::new(obj);
    let task_object = PriorityTaskObject::new(boxed_obj, priority);
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

pub async fn read_task_status(task_id: u64) -> Option<TaskStatus> {
    let read_guard = (*TASK_STATUS_DATA).read().await;
    
    read_guard.get(&task_id).cloned()
}
pub async fn add_task_to_queue_and_wait_to_see_if_done(
    obj: impl ExecuteUserTask,
    priority: i32,
    wait: Duration,
) -> TaskStatus {
    let entry_status = add_task_to_queue(obj, priority).await;
    let task_id = entry_status.task_id;
    let is_running_task = task_poll_now().await;
    if is_running_task {
        sleep(wait).await;
        let new_status = read_task_status(task_id).await;
        new_status.unwrap_or(entry_status)
    } else {
        entry_status
    }
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

const DEFAULT_SIMULTANEOUS_TASKS: usize = 2;
static SIMULTANEOUS_TASKS: LazyLock<usize> = LazyLock::new(|| {
    env::var("SIMULTANEOUS_TASKS")
        .ok()
        .and_then(|val| str::parse(&val).ok())
        .unwrap_or(DEFAULT_SIMULTANEOUS_TASKS)
});
static USER_TASK_SEMAPHORE: LazyLock<Semaphore> =
    LazyLock::new(|| Semaphore::new(*SIMULTANEOUS_TASKS));
pub async fn start_workers() -> Infallible {
    let mut trips_since_last_task: u64 = 0;
    loop {
        let was_poll_successful = task_poll_now().await;
        if !was_poll_successful {
            trips_since_last_task += 1;
            if trips_since_last_task.is_power_of_two() {
                let time_since_last_task =
                    prettyprint_duration(Duration::from_secs(trips_since_last_task));
                info!(%time_since_last_task,"Have not gotten a new task dispite waiting a long time")
            }
            sleep(Duration::from_secs(1)).await
        }
    }
}

pub async fn task_poll_now() -> bool {
    let Ok(permit) = USER_TASK_SEMAPHORE.try_acquire() else {
        return false;
    };
    match pop_task_from_queue().await {
        None => {
            drop(permit);
            false
        }
        Some(res) => {
            let task_id = res.task_id;
            let obj = res.task_object;
            let task_type_label = obj.get_task_label();
            tokio::spawn(
                async move {
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
                }
                .instrument(tracing::info_span!(
                    "task_execution",
                    task_id = task_id,
                    task_type = task_type_label
                )),
            );
            true
        }
    }
}

pub fn spawn_worker_loop() {
    tokio::spawn(start_workers().in_current_span());
}
