import traceback
import logging
from fastapi import HTTPException  # <--- Import thêm
from app.api.v1.analysis import generate_analysis_doc
from app.core.step_task_registry import StepTaskRegistry
logger = logging.getLogger(__name__)

async def run_analysis_step(
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
                "step": "analysis",
            }
        )

        for index, doc in enumerate(documents):
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

            except HTTPException as he:

                error_payload = {
                    "code": he.status_code,
                    "message": he.detail,
                }

                logger.warning(f"[ANALYSIS][{doc_type}] {error_payload}")

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
                error_payload = {
                    "code": 500,
                    "message": str(e),
                }

                logger.exception(f"[ANALYSIS][{doc_type}] UNEXPECTED ERROR")

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

        await notifier.send(
            {
                "type": "step_finished",
                "step": "analysis",
            }
        )

    except Exception as e:

        logger.info(f"FATAL ANALYSIS ERROR: {str(e)}")
        await notifier.send(
            {"type": "step_error", "step": "analysis", "message": str(e)}
        )
    finally:

        StepTaskRegistry.finish(project_id, "analysis")
