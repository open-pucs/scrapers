use std::path::Path;

use aws_config::{BehaviorVersion, Region};
use aws_sdk_s3::config::Credentials;
use tokio::fs::File;

use crate::types::{
    RawAttachment,
    env_vars::{
        OPENSCRAPERS_S3_ACCESS_KEY, OPENSCRAPERS_S3_CLOUD_REGION, OPENSCRAPERS_S3_ENDPOINT,
        OPENSCRAPERS_S3_OBJECT_BUCKET, OPENSCRAPERS_S3_SECRET_KEY,
    },
    hash::Blake2bHash,
};
use aws_sdk_s3::{Client as S3Client, primitives::ByteStream};

pub fn get_raw_attach_obj_key(hash: Blake2bHash) -> String {
    format!("raw/metadata/{hash}.json")
}

pub fn get_raw_attach_file_key(hash: Blake2bHash) -> String {
    format!("raw/file/{hash}")
}

pub fn generate_s3_object_uri_from_key(key: &str) -> String {
    format!(
        "https://{}.s3.amazonaws.com/{}",
        &*OPENSCRAPERS_S3_OBJECT_BUCKET, key
    )
}
pub async fn make_s3_client() -> S3Client {
    let region = Region::new(&*OPENSCRAPERS_S3_CLOUD_REGION);
    let creds = Credentials::new(
        &*OPENSCRAPERS_S3_ACCESS_KEY,
        &*OPENSCRAPERS_S3_SECRET_KEY,
        None, // no session token
        None, // no expiration
        "manual",
    );

    // Start from the env-loader so we still pick up other settings (timeouts, retry, etc)
    let cfg_loader = aws_config::defaults(BehaviorVersion::latest())
        .region(region)
        .credentials_provider(creds)
        .endpoint_url(&*OPENSCRAPERS_S3_ENDPOINT);

    let sdk_config = cfg_loader.load().await;
    S3Client::new(&sdk_config)
}

pub async fn push_raw_attach_to_s3(
    s3_client: &S3Client,
    raw_att: RawAttachment,
    file_path: &str,
) -> anyhow::Result<()> {
    let dumped_data = serde_json::to_string(&raw_att)?;
    let obj_key = get_raw_attach_obj_key(raw_att.hash);
    let file_key = get_raw_attach_file_key(raw_att.hash);

    s3_client
        .put_object()
        .bucket(&*OPENSCRAPERS_S3_OBJECT_BUCKET)
        .key(obj_key)
        .body(ByteStream::from(dumped_data.into_bytes()))
        .send()
        .await?;

    let body = ByteStream::from_path(Path::new(file_path)).await?;
    s3_client
        .put_object()
        .bucket(&*OPENSCRAPERS_S3_OBJECT_BUCKET)
        .key(file_key)
        .body(body)
        .send()
        .await?;

    Ok(())
}

pub async fn download_file(url: &str) -> anyhow::Result<String> {
    let response = reqwest::get(url).await?;
    let temp_file_path = "temp_file";
    let mut dest = File::create(temp_file_path).await?;
    let content = response.bytes().await?;
    tokio::io::copy(&mut content.as_ref(), &mut dest).await?;
    Ok(temp_file_path.to_string())
}

// async def fetch_case_filing_from_s3(
//     case_name: str, jurisdiction_name: str, state: str, country: str = "usa"
// ) -> GenericCase:
//     s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
//     key = get_case_s3_key(
//         case_name=case_name,
//         jurisdiction_name=jurisdiction_name,
//         state=state,
//         country=country,
//     )
//     raw_case = await s3.download_s3_file_to_string_async(file_name=key)
//     return GenericCase.model_validate_json(raw_case)
//
//
// async def fetch_attachment_data_from_s3(hash: Blake2bHash) -> RawAttachment:
//     obj_key = get_raw_attach_obj_key(hash)
//     s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
//     result_str = await s3.download_s3_file_to_string_async(file_name=obj_key)
//     raw_attach = RawAttachment.model_validate_json(result_str)
//     return raw_attach
//
//
// async def fetch_attachment_file_from_s3(hash: Blake2bHash) -> Path:
//     obj_key = get_raw_attach_file_key(hash)
//     s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
//     result_path = await s3.download_s3_file_to_path_async(
//         file_name=obj_key, serve_cache=True
//     )
//     if result_path is None:
//         raise Exception("Failed to get file from s3")
//     return result_path
//
//
// async def push_raw_attach_to_s3_and_db(
//     raw_att: RawAttachment, file_path: Optional[Path], file_only: bool = False
// ) -> None:
//
//     dumped_data = raw_att.model_dump_json()
//     obj_key = get_raw_attach_obj_key(raw_att.hash)
//     file_key = get_raw_attach_file_key(raw_att.hash)
//     s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
//     if not file_only:
//         await s3.save_string_to_remote_file_async(key=obj_key, content=dumped_data)
//     # Immutable is true for this line since any file will always get saved with the same hash.
//     if file_path is None:
//         does_exist = await s3.check_if_file_exists(file_upload_key=file_key)
//         if does_exist:
//             default_logger.info(
//                 f"File with hash {raw_att.hash} already exists on s3. Skipping upload"
//             )
//             return None
//         else:
//             error_string = f"File with hash {raw_att.hash} does not exist on s3 and no uploaded file was provided."
//             default_logger.error(error_string)
//             raise FileNotFoundError(error_string)
//     await s3.push_file_to_s3_async(
//         filepath=file_path, file_upload_key=file_key, immutable=True
//     )
//
//
// async def does_openscrapers_attachment_exist(hash: Blake2bHash) -> bool:
//     bucket = OPENSCRAPERS_S3_OBJECT_BUCKET
//     s3 = S3FileManager(bucket=bucket)
//     obj_key = get_raw_attach_obj_key(hash)
//     file_key = get_raw_attach_file_key(hash)
//     try:
//         do_files_exist_list = await asyncio.gather(
//             s3.check_if_file_exists(file_upload_key=obj_key, bucket=bucket),
//             s3.check_if_file_exists(file_upload_key=file_key, bucket=bucket),
//         )
//         return do_files_exist_list[0] and do_files_exist_list[1]
//     except Exception as e:
//         return False
//
//
// async def push_case_to_s3_and_db(
//     case: GenericCase, jurisdiction_name: str, state: str, country: str = "usa"
// ) -> GenericCase:
//     key = get_case_s3_key(
//         case_name=case.case_number,
//         jurisdiction_name=jurisdiction_name,
//         state=state,
//         country=country,
//     )
//     case.indexed_at = rfc_time_now()
//     s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
//     case_jsonified = case.model_dump_json()
//     # Maybe async this in its own thread?
//     await s3.save_string_to_remote_file_async(key=key, content=case_jsonified)
//     case_info = CaseInfo(
//         case=case, jurisdiction_name=jurisdiction_name, state=state, country=country
//     )
//     await set_case_as_updated(case_info=case_info)
//     return case
//
//
// async def list_cases_for_jurisdiction(
//     jurisdiction_name: str, state: str, country: str = "usa"
// ) -> List[str]:
//     """
//     Returns all case names stored in S3 for a given jurisdiction.
//
//     Args:
//         jurisdiction_name: Name of the legal jurisdiction
//         state: State abbreviation
//         country: Country code (default: 'usa')
//
//     Returns:
//         List of case numbers/filenames found in the S3 bucket
//     """
//     s3 = S3FileManager(bucket=OPENSCRAPERS_S3_OBJECT_BUCKET)
//     prefix = f"objects/{country}/{state}/{jurisdiction_name}/"
//
//     # Get all keys matching the jurisdiction prefix
//     keys = await s3.list_objects_with_prefix_async(prefix)
//
//     # Extract case names from S3 keys
//     case_names = []
//     for key in keys:
//         if key.endswith(".json"):
//             # Split key path and remove .json extension
//             filename = key.split("/")[-1]
//             case_name = filename[:-5]
//             case_names.append(case_name)
//
//     return case_names
