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

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(ai_service_url, json=payload)

            # try:
            #     logger.info(f"AI Response json={response.json()}")
            # except Exception as e:
            #     logger.error(f"AI Response not json: {response.text}")

            # ---------- HTTP LEVEL ----------
            if response.status_code != 200:
                if 400 <= response.status_code < 500:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=response.text,
                    )

                last_error = f"Status {response.status_code}: {response.text}"
                raise httpx.HTTPStatusError(
                    message=last_error,
                    request=response.request,
                    response=response,
                )

            # ---------- BODY LEVEL ----------
            try:
                data = response.json()
            except Exception:
                raise HTTPException(
                    status_code=502,
                    detail="AI response is not valid JSON",
                )
            ai_inner_res = data.get("response", {})

            logger.info(f"AI response, [response: {ai_inner_res}]")
            
            content = ""
            if isinstance(ai_inner_res, dict):
                content = ai_inner_res.get("content", "")
            elif isinstance(ai_inner_res, str):
                content = ai_inner_res

            lowered = content.lower()

            if "error generating document" in lowered or "error code:" in lowered:
                logger.error(f"AI logical error (wrapped 200): {content}")
                raise HTTPException(
                    status_code=502,
                    detail=content
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
