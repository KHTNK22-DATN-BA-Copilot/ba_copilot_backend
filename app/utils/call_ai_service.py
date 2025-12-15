import asyncio
import io
import httpx
import logging
from fastapi import UploadFile, HTTPException, status, File
from typing import List, Dict, Any, Optional
from app.utils.file_handling import has_extension

logger = logging.getLogger(__name__)


async def call_ai_service(
    ai_service_url: str,
    payload: Dict[str, Any],
    retries: int = 3,
    timeout: int = 120,
):
    last_error: Optional[str] = None

    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    ai_service_url,
                    json=payload,
                )

            if response.status_code == 200:
                return response.json()

            last_error = f"Status {response.status_code}: {response.text}"
            logger.warning(
                f"AI service returned {response.status_code} "
                f"(attempt {attempt}/{retries})"
            )

        except httpx.RequestError as e:
            last_error = str(e)
            logger.warning(f"AI request error (attempt {attempt}/{retries}): {repr(e)}")

        await asyncio.sleep(2 * attempt)

    logger.error(
        f"AI service unavailable after {retries} retries. Last error: {last_error}"
    )

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="AI service unavailable after multiple retries",
    )
