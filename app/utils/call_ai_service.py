import asyncio
import random
import httpx
import logging
from fastapi import HTTPException, status
from typing import Dict, Any, Optional

from app.services.ai_credentials import resolve_ai_headers_for_user

logger = logging.getLogger(__name__)

GENERIC_AI_ERROR = (
    "Something went wrong while processing your request. Please try again later."
)

async def call_ai_service(
    ai_service_url: str,
    payload: Dict[str, Any],
    ai_provider: Optional[str] = None,
    ai_model: Optional[str] = None,
    ai_api_key: Optional[str] = None,
    retries: int = 3,
    connect_timeout: int = 10,
    read_timeout: int = 180,
):
    last_error: Optional[str] = None

    timeout = httpx.Timeout(
        connect=connect_timeout,
        read=read_timeout,
        write=10,
        pool=10,
    )

    for attempt in range(1, retries + 1):
        if asyncio.current_task() and asyncio.current_task().cancelled():
            logger.info(f"Task cancelled before attempt {attempt}")
            raise asyncio.CancelledError()

        try:
            logger.info(
                f"Calling AI service (attempt {attempt}/{retries}) → {ai_service_url}"
            )

            headers: Dict[str, str] = {}
            if ai_provider:
                headers["X-AI-Provider"] = ai_provider
            if ai_model:
                headers["X-AI-Model"] = ai_model
            if ai_api_key:
                headers["X-AI-API-Key"] = ai_api_key

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    ai_service_url,
                    json=payload,
                    headers=headers or None,
                )

            # try:
            #     logger.info(f"AI Response json={response.json()}")
            # except Exception as e:
            #     logger.error(f"AI Response not json: {response.text}")

            # ---------- BODY LEVEL ----------
            try:
                data = response.json()
            except Exception:
                logger.error(f"AI returned non-JSON: {response.text}")
                raise HTTPException(
                    status_code=502,
                    detail=GENERIC_AI_ERROR,
                )

            ai_res = data.get("response")

            summary = ai_res.get("summary", "AI Response")
            content = ai_res.get("content")
            inner_status = ai_res.get("status_code", 200)

            if inner_status != 200:
                logger.error(f"AI logical error: {content}")
                raise HTTPException(
                    status_code=502,
                    detail=GENERIC_AI_ERROR,
                )

            return data

        except asyncio.CancelledError:
            logger.warning(f"AI Service Call cancelled at {ai_service_url}")
            raise

        except HTTPException:
            raise

        except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            last_error = str(e)
            logger.warning(f"AI timeout (attempt {attempt}/{retries})")

        except httpx.RequestError as e:
            last_error = str(e)
            logger.warning(f"AI request error (attempt {attempt}/{retries}): {repr(e)}")

        if attempt < retries:
            delay = min(2**attempt, 10) + random.uniform(0, 1)
            await asyncio.sleep(delay)

    logger.error(
        f"AI service unavailable after {retries} retries. Last error: {last_error}"
    )

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="AI service unavailable after multiple retries",
    )
