from typing import Any, List
import asyncio
import aiohttp
from openpuc_scrapers.db.airflow_basemodel import AirflowBaseModel


class RequestData(AirflowBaseModel):
    url: str
    data: Any


async def post_multiple_objects_to_endpoints(
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


async def post_list_to_endpoint_split(
    objects: List[Any],
    post_endpoint: str,
    max_request_size: int = 1000,
    max_simul_requests: int = 10,
) -> List[dict]:
    request_data_list = []

    for i in range(0, len(objects), max_request_size):
        chunk = objects[i : i + max_request_size]
        request = RequestData(url=post_endpoint, data=chunk)
        request_data_list.append(request)

    return await post_multiple_objects_to_endpoints(
        request_data_list, max_simul_requests=max_simul_requests
    )
