import traceback
from fastapi import HTTPException
import asyncio
from app.api.v1.planning import generate_planning_doc
from app.core.step_task_registry import StepTaskRegistry
import logging

logger = logging.getLogger(__name__)

async def run_planning_step(
    project_id: int,
    project_name: str,
    description: str,
    documents: list,
    db,
    current_user,
    notifier,
):
    try:  
        await notifier.send(
            {
                "type": "step_start",
                "step": "planning",
            }
        )

        for index, doc in enumerate(documents):
            if asyncio.current_task().cancelled():
                raise asyncio.CancelledError()
            doc_type = doc["type"]

            await notifier.send(
                {
                    "type": "doc_start",
                    "step": "planning",
                    "index": index,
                    "doc_type": doc_type,
                }
            )

            try: 
                result = await generate_planning_doc(
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
                        "step": "planning",
                        "index": index,
                        "doc_type": doc_type,
                        "data": result.model_dump(),
                    }
                )

            except asyncio.CancelledError:
                logger.warning(f"[PLANNING][{doc_type}] Generation CANCELLED by user.")
                raise

            except HTTPException as he:

                error_payload = {
                    "code": he.status_code,
                    "message": he.detail,
                }

                logger.warning(f"[PLANNING][{doc_type}] {error_payload}")

                await notifier.send(
                    {
                        "type": "doc_error",
                        "step": "planning",
                        "index": index,
                        "doc_type": doc_type,
                        "error": error_payload,
                    }
                )
                continue

            except Exception as e:
                error_payload = {
                    "code": 500,
                    "message": str(e),
                }

                logger.exception(f"[PLANNING][{doc_type}] UNEXPECTED ERROR")

                await notifier.send(
                    {
                        "type": "doc_error",
                        "step": "planning",
                        "index": index,
                        "doc_type": doc_type,
                        "error": error_payload,
                    }
                )
                continue

        await notifier.send(
            {
                "type": "step_finished",
                "step": "planning",
            }
        )

    except asyncio.CancelledError:
        logger.info(f"Process for project {project_id} fully stopped.")

    except Exception as e:

        logger.info(f"FATAL PLANNING ERROR: {str(e)}")
        await notifier.send(
            {"type": "step_error", "step": "planning", "message": str(e)}
        )
    finally:

        StepTaskRegistry.finish(project_id, "planning")
