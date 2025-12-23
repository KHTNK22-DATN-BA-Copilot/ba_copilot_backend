import asyncio
import random
import httpx
import logging
from fastapi import HTTPException, status
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


async def call_ai_service(
    ai_service_url: str,
    payload: Dict[str, Any],
    retries: int = 3,
    connect_timeout: int = 10,
    read_timeout: int = 180,  # QUAN TRỌNG
):
    last_error: Optional[str] = None

    timeout = httpx.Timeout(
        connect=connect_timeout,
        read=read_timeout,
        write=10,
        pool=10,
    )

    for attempt in range(1, retries + 1):
        try:
            logger.info(
                f"Calling AI service (attempt {attempt}/{retries}) → {ai_service_url}"
            )

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    ai_service_url,
                    json=payload,
                )

            # --- SUCCESS ---
            if response.status_code == 200:
                return response.json()

            # --- KHÔNG retry 4xx ---
            if 400 <= response.status_code < 500:
                logger.error(
                    f"AI service returned {response.status_code}: {response.text}"
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.text,
                )

            # --- 5xx → retry ---
            last_error = f"Status {response.status_code}: {response.text}"
            logger.warning(
                f"AI service error {response.status_code} "
                f"(attempt {attempt}/{retries})"
            )

        except httpx.ReadTimeout as e:
            last_error = f"ReadTimeout: {e}"
            logger.warning(f"AI read timeout (attempt {attempt}/{retries})")

        except httpx.ConnectTimeout as e:
            last_error = f"ConnectTimeout: {e}"
            logger.warning(f"AI connect timeout (attempt {attempt}/{retries})")

        except httpx.RequestError as e:
            last_error = str(e)
            logger.warning(f"AI request error (attempt {attempt}/{retries}): {repr(e)}")

        # --- BACKOFF + JITTER ---
        if attempt < retries:
            delay = min(2**attempt, 10) + random.uniform(0, 1)
            logger.info(f"Retrying in {delay:.1f}s...")
            await asyncio.sleep(delay)

    logger.error(
        f"AI service unavailable after {retries} retries. Last error: {last_error}"
    )

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="AI service unavailable after multiple retries",
    )
