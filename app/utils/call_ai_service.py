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
    files: List[UploadFile],
    retries: int = 3,
    timeout: int = 120,
):
    """
    Gọi AI service với retry & timeout logic, hỗ trợ gửi file multipart/form-data.
    """
    form_data = {
        key: ("" if value is None else str(value)) for key, value in payload.items()
    }

    file_data = []
    if files:
        for f in files:
            if not f.filename or not has_extension(f.filename):
                continue
            content = await f.read()
            file_data.append(
                ("files", (f.filename, io.BytesIO(content), f.content_type))
            )

    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    ai_service_url,
                    data=form_data,
                    files=file_data if file_data else None,
                )

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
