import asyncio
import logging
from app.api.v1.analysis import (
    generate_analysis_doc,
)
from app.core.step_task_registry import StepTaskRegistry
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def run_analysis_step(
    project_id: int,
    project_name: str,
    description: str,
    documents: list,
    db,
    current_user,
    notifier,
    stop_event: asyncio.Event = None,
):
    try:
        await notifier.send({"type": "step_start", "step": "analysis"})

        for index, doc in enumerate(documents):

            if stop_event and stop_event.is_set():
                logger.info(
                    f"Project {project_id}: analysis generation stopped by user request."
                )
                await notifier.send(
                    {
                        "type": "step_stopped",
                        "step": "analysis",
                        "message": "User requested stop. Remaining tasks skipped.",
                    }
                )
                break
            # ------------------------------------

            if asyncio.current_task().cancelled():
                raise asyncio.CancelledError()

            doc_type = doc["type"]

            await notifier.send(
                {
                    "type": "doc_start",
                    "step": "analysis",
                    "index": index,
                    "doc_type": doc_type,
                }
            )

            try:

                result = await generate_analysis_doc(
                    project_id=project_id,
                    project_name=doc_type,
                    doc_type=doc_type,
                    description=description,
                    db=db,
                    current_user=current_user,
                )

                await notifier.send(
                    {
                        "type": "doc_completed",
                        "step": "analysis",
                        "index": index,
                        "doc_type": doc_type,
                        "data": result.model_dump(),
                    }
                )

            except asyncio.CancelledError:
                logger.warning(
                    f"[analysis][{doc_type}] Generation CANCELLED (Hard stop)."
                )
                raise

            except HTTPException as he:
                error_payload = {"code": he.status_code, "message": he.detail}
                logger.warning(f"[analysis][{doc_type}] {error_payload}")
                await notifier.send(
                    {
                        "type": "doc_error",
                        "step": "analysis",
                        "index": index,
                        "doc_type": doc_type,
                        "error": error_payload,
                    }
                )
                continue

            except Exception as e:
                logger.exception(f"[analysis][{doc_type}] UNEXPECTED ERROR")
                await notifier.send(
                    {
                        "type": "doc_error",
                        "step": "analysis",
                        "index": index,
                        "doc_type": doc_type,
                        "error": {"code": 500, "message": str(e)},
                    }
                )
                continue

        await notifier.send(
            {
                "type": "step_finished",
                "step": "analysis",
            }
        )

    except asyncio.CancelledError:
        logger.info(
            f"Process for project {project_id} fully stopped (Connection Lost)."
        )

    except Exception as e:
        logger.error(f"FATAL analysis ERROR: {str(e)}")
        await notifier.send(
            {"type": "step_error", "step": "analysis", "message": str(e)}
        )
    finally:
        StepTaskRegistry.finish(project_id, current_user.id,"analysis")
