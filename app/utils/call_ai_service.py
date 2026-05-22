import asyncio
import random
import httpx
import logging
from fastapi import HTTPException, status
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.ai_credentials import resolve_ai_headers_for_user

logger = logging.getLogger(__name__)

GENERIC_AI_ERROR = (
    "Something went wrong while processing your request. Please try again later."
)


# helper function to detect quota errors in AI responses
def _is_quota_or_token_error(data: Any) -> bool:
    text = str(data or "").lower()
    keywords = (
        "quota",
        "insufficient_quota",
        "resource_exhausted",
        "rate limit",
        "rate_limit",
        "too many requests",
        "token limit",
        "tokens",
        "billing",
        "credit",
        "credits",
        "exceeded",
    )
    return any(keyword in text for keyword in keywords)


async def call_ai_service(
    ai_service_url: str,
    payload: Dict[str, Any],
    db: Optional[Session] = None,
    user_id: Optional[int] = None,
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

    headers: Dict[str, str] = {}
    if db and user_id:
        ai_headers = resolve_ai_headers_for_user(db, user_id)
        if ai_headers:
            headers.update(ai_headers)

    for attempt in range(1, retries + 1):
        if asyncio.current_task() and asyncio.current_task().cancelled():
            logger.info(f"Task cancelled before attempt {attempt}")
            raise asyncio.CancelledError()

        try:
            logger.info(
                f"Calling AI service (attempt {attempt}/{retries}) → {ai_service_url}"
            )

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

            if response.status_code >= 400:
                last_error = f"AI error: {data}"
                logger.warning(last_error)
                if _is_quota_or_token_error(data):
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="AI service error: quota exceeded or token limit reached",
                    )

                if attempt == retries:
                    raise HTTPException(
                        status_code=502,
                        detail=GENERIC_AI_ERROR,
                    )
                continue

            if data.get("type") == "metadata_extraction":
                return data

            ai_res = data.get("response")

            content = ai_res.get("content")
            inner_status = ai_res.get("status_code", 200)

            if inner_status != 200:
                logger.error(f"AI logical error: {content}")
                if _is_quota_or_token_error(content):
                    logger.warning(
                        f"AI quota/token error detected in content: {content}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="AI service error: quota exceeded or token limit reached",
                    )
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
