from typing import Any, List
import asyncio
import aiohttp
from pydantic import BaseModel


class RequestData(BaseModel):
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
