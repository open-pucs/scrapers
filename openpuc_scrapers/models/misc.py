from typing import Any, List
import asyncio
import aiohttp
from openpuc_scrapers.models.filing import Filing
from pydantic import BaseModel


class RequestData(BaseModel):
    url: str
    data: Any


async def post_objects_to_endpoint(
    requests: List[RequestData], max_simul_requests: int
) -> List[dict]:
    semaphore = asyncio.Semaphore(max_simul_requests)  #

    async with aiohttp.ClientSession() as session:

        async def post_single(request: RequestData) -> dict:
            async with semaphore:  # Acquire semaphore before making request
                try:
                    async with session.post(
                        request.url,
                        json=request.data.to_dict(),  # Convert Filing object to dict
                        headers={"Content-Type": "application/json"},
                    ) as response:
                        response.raise_for_status()  # Raise exception for bad status codes
                        print(
                            "Successfully uploaded file with response:", response.status
                        )
                        return await response.json()
                except Exception as e:
                    print(f"Error uploading data: {str(e)}")
                    return {"error": str(e), "data": str(request.data)}

        tasks = [post_single(request) for request in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        for response in responses:
            if isinstance(response, BaseException):
                raise response

        return responses


async def upload_schemas_to_kessler(files: List[Filing], api_url: str):
    file_post_url = api_url + "ingest_v1/add-task/ingest"
    requests = [RequestData(url=file_post_url, data=file) for file in files]
    await post_objects_to_endpoint(requests, 30)
