import asyncio
import logging
from app.api.v1.design import (
    generate_design,
)
from app.core.step_task_registry import StepTaskRegistry
from fastapi import HTTPException

logger = logging.getLogger(__name__)


async def run_design_step(
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
        await notifier.send({"type": "step_start", "step": "design"})

        for index, doc in enumerate(documents):

            if stop_event and stop_event.is_set():
                logger.info(
                    f"Project {project_id}: design generation stopped by user request."
                )
                await notifier.send(
                    {
                        "type": "step_stopped",
                        "step": "design",
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
                    "step": "design",
                    "index": index,
                    "doc_type": doc_type,
                }
            )

            try:

                result = await generate_design(
                    project_id=project_id,
                    project_name=doc_type,
                    design_type=doc_type,
                    description=description,
                    db=db,
                    current_user=current_user,
                )

                await notifier.send(
                    {
                        "type": "doc_completed",
                        "step": "design",
                        "index": index,
                        "doc_type": doc_type,
                        "data": result.model_dump(),
                    }
                )

            except asyncio.CancelledError:
                logger.warning(
                    f"[design][{doc_type}] Generation CANCELLED (Hard stop)."
                )
                raise

            except HTTPException as he:
                error_payload = {"code": he.status_code, "message": he.detail}
                logger.warning(f"[design][{doc_type}] {error_payload}")
                await notifier.send(
                    {
                        "type": "doc_error",
                        "step": "design",
                        "index": index,
                        "doc_type": doc_type,
                        "error": error_payload,
                    }
                )
                continue

            except Exception as e:
                logger.exception(f"[design][{doc_type}] UNEXPECTED ERROR")
                await notifier.send(
                    {
                        "type": "doc_error",
                        "step": "design",
                        "index": index,
                        "doc_type": doc_type,
                        "error": {"code": 500, "message": str(e)},
                    }
                )
                continue

        await notifier.send(
            {
                "type": "step_finished",
                "step": "design",
            }
        )

    except asyncio.CancelledError:
        logger.info(
            f"Process for project {project_id} fully stopped (Connection Lost)."
        )

    except Exception as e:
        logger.error(f"FATAL design ERROR: {str(e)}")
        await notifier.send(
            {"type": "step_error", "step": "design", "message": str(e)}
        )
    finally:
        StepTaskRegistry.finish(project_id,current_user.id, "design")
