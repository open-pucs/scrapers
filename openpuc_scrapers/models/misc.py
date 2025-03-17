from typing import Any, List
import asyncio
import aiohttp
from openpuc_scrapers.models.filing import GenericFiling
from pydantic import BaseModel


class RequestData(BaseModel):
    url: str
    data: Any


async def post_objects_to_endpoint(
    requests: List[RequestData], max_simul_requests: int
) -> List[dict]:
    semaphore = asyncio.Semaphore(max_simul_requests)

    async with aiohttp.ClientSession() as session:

        async def post_single(request: RequestData) -> dict:
            async with semaphore:  # Acquire semaphore before making request
                async with session.post(
                    request.url,
                    json=request.data.to_dict(),  # Convert GenericFiling object to dict
                    headers={"Content-Type": "application/json"},
                ) as response:
                    response.raise_for_status()  # Raise exception for bad status codes
                    print("Successfully uploaded file with response:", response.status)
                    return await response.json()

        tasks = [post_single(request) for request in requests]
        try:
            # Will raise the first exception encountered
            responses = await asyncio.gather(*tasks)
            return responses  # type: List[dict]
        except Exception as e:
            print(f"Error during batch upload: {str(e)}")
            raise  # Re-raise the exception


async def upload_schemas_to_kessler(files: List[GenericFiling], api_url: str):
    file_post_url = api_url + "ingest_v1/add-task/ingest"
    requests = [RequestData(url=file_post_url, data=file) for file in files]
    await post_objects_to_endpoint(requests, 30)
