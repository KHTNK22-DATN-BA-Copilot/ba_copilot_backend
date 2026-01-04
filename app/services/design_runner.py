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
                    project_name=project_name,
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
                error_msg = str(he.detail)
                logger.info(f"SKIP PLANNING ERROR {doc_type}: {error_msg}")

                await notifier.send(
                    {
                        "type": "doc_error",
                        "step": "design",
                        "index": index,
                        "doc_type": doc_type,
                        "error": error_msg,
                    }
                )
                continue 

            except Exception as e:

                error_msg = str(e.detail) if isinstance(e, HTTPException) else str(e)
                logger.info(f" SKIP ERROR {doc_type}: {error_msg}")

                await notifier.send(
                    {
                        "type": "doc_error",
                        "step": "design",
                        "index": index,
                        "doc_type": doc_type,
                        "error": error_msg,
                    }
                )

                continue

        await notifier.send({"type": "step_finished", "step": "design"})

    except Exception as e:

        logger.info(f"FATAL ERROR: {str(e)}")
        await notifier.send({"type": "step_error", "step": "design", "message": str(e)})
    finally:
        StepTaskRegistry.finish(project_id, "design")
