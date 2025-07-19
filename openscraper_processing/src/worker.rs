use crate::processing::process_case;
use crate::s3_stuff::make_s3_client;
use crate::types::GenericCase;
use std::collections::VecDeque;
use std::convert::Infallible;
use std::sync::{Arc, LazyLock};
use std::time::Duration;
use tokio::sync::{Mutex, Semaphore};
use tokio::time::sleep;
use tracing::{Instrument, warn};

static CASE_PROCESSING_SEMAPHORE: Semaphore = Semaphore::const_new(10);

static CASE_PROCESSING_QUEUE: LazyLock<Mutex<VecDeque<GenericCase>>> =
    LazyLock::new(|| Mutex::new(VecDeque::with_capacity(100)));

pub async fn push_case_to_queue(case: GenericCase) -> usize {
    let mut unlocked_queue = (*CASE_PROCESSING_QUEUE).lock().await;
    unlocked_queue.push_back(case);
    unlocked_queue.len()
}
pub async fn get_case_from_queue() -> (Option<GenericCase>, usize) {
    let mut unlocked_queue = (*CASE_PROCESSING_QUEUE).lock().await;
    let res = unlocked_queue.pop_front();
    (res, unlocked_queue.len())
}

pub async fn start_workers() -> anyhow::Result<Infallible> {
    println!("Starting workers, logged outside of a tracer");
    tracing::info!("Starting workers!!");
    let s3_client = Arc::new(make_s3_client().await);

    let case_sem_ref = &CASE_PROCESSING_SEMAPHORE;

    let mut cases_without_ingest = 0;
    tracing::info!("Finished worker startup process, entering main loop.");
    loop {
        if let (Some(case), queue_length) = get_case_from_queue().await {
            tracing::info!(case_number= %(case.case_number), queue_length,"Got case waiting to process.");
            cases_without_ingest = 0;
            let s3_client_clone = s3_client.clone();
            let sephaor_perm = case_sem_ref
                .acquire()
                .await
                .expect("Apparently the semaphore can only give an error if its closed, which this should never be??");
            tokio::spawn(
                async move {
                    tracing::info!(
                        availible_permits = %case_sem_ref.available_permits(),
                        case_number= %(case.case_number),
                        "Got semaphore beginning to process case");
                    if let Err(e) = process_case(&case, &s3_client_clone).await {
                        warn!(error = e.to_string(), "Error processing case");
                    }
                    drop(sephaor_perm);
                }
                .in_current_span(),
            );
        } else {
            cases_without_ingest += 1;
            if cases_without_ingest >= 20 {
                tracing::info!(availible_permits = %case_sem_ref.available_permits(),"Checked {cases_without_ingest} times for cases and found nothing.");
                cases_without_ingest = 0;
            }
            sleep(Duration::from_secs(2)).await;
        }
    }
}
