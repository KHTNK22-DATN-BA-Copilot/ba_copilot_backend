import traceback
from fastapi import HTTPException
from app.api.v1.design import generate_design
from app.core.step_task_registry import StepTaskRegistry
import logging

logger = logging.getLogger(__name__)

async def run_design_step(
    project_id: int,
    project_name: str,
    description: str,
    documents: list,
    db,
    current_user,
    notifier,
):
    try:
        await notifier.send({"type": "step_start", "step": "design"})

        for index, doc in enumerate(documents):
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

            except HTTPException as he:

                error_payload = {
                    "code": he.status_code,
                    "message": he.detail,
                }

                logger.warning(f"[DESIGN][{doc_type}] {error_payload}")

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
                error_payload = {
                    "code": 500,
                    "message": str(e),
                }

                logger.exception(f"[DESIGN][{doc_type}] UNEXPECTED ERROR")

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

        await notifier.send(
            {
                "type": "step_finished",
                "step": "design",
            }
        )

    except Exception as e:

        logger.info(f"FATAL DESIGN ERROR: {str(e)}")
        await notifier.send(
            {"type": "step_error", "step": "design", "message": str(e)}
        )
    finally:

        StepTaskRegistry.finish(project_id, "design")
