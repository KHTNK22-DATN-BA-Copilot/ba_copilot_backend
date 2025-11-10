import asyncio
import httpx
import logging
from fastapi import UploadFile, HTTPException, status, File
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


async def call_ai_service(
    ai_service_url: str,
    payload: Dict[str, Any],
    files: List[UploadFile] = File([]),
    retries: int = 3,
    timeout: int = 120,
):
    """
    Gọi AI service với retry & timeout logic, hỗ trợ gửi file thật (multipart/form-data).
    """

    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # if files and len(files) > 0:

                #     file_data = [
                #         ("files", (file.filename, await file.read(), file.content_type))
                #         for file in files
                #     ]

                #     response = await client.post(
                #         ai_service_url,
                #         data=payload,
                #         files=file_data,
                #     )
                # else:
                response = await client.post(ai_service_url, json=payload)

            if response.status_code == 200:
                return response.json()

            logger.warning(
                f"AI service returned {response.status_code} (attempt {attempt}/{retries}): {response.text}"
            )

        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.warning(f"AI request failed (attempt {attempt}/{retries}): {e}")
            await asyncio.sleep(2 * attempt)

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="AI service unavailable after multiple retries",
    )
