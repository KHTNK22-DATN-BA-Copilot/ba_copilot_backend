import asyncio
import logging

from fastapi import HTTPException

from app.api.v2.analysis import (
    generate_analysis_doc,
)
from app.core.step_task_registry import StepTaskRegistry
from app.core.database import SessionLocal
from app.core.rbac import check_permission
from app.core.rbac import Permission
from app.services.rag_postprocess import queue_rag_indexing
from app.models.user import User

logger = logging.getLogger(__name__)


async def run_analysis_step(
    project_id: int,
    project_name: str,
    description: str,
    documents: list,
    current_user_id,
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

            db = SessionLocal()

            try:
                current_user = db.query(User).filter(User.id == current_user_id).first()

                if not current_user:
                    raise HTTPException(status_code=401, detail="User not found")

                access = check_permission(
                    project_id=project_id,
                    current_user=current_user,
                    db=db,
                    permission=Permission.FILE_WRITE,
                )

                result = await generate_analysis_doc(
                    project_id=project_id,
                    project_name=doc_type,
                    doc_type=doc_type,
                    description=description,
                    access=access,
                    db=db,
                )

                await notifier.send(
                    {
                        "type": "doc_completed",
                        "step": "analysis",
                        "index": index,
                        "doc_type": doc_type,
                        "data": result.model_dump(mode="json"),
                    }
                )

                await queue_rag_indexing(
                    step="analysis",
                    file_id=result.document_id,
                    doc_type=doc_type,
                    markdown_text=result.document,
                    emit_event=notifier.send,
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
                if he.status_code in [401, 403]:
                    break
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
            finally:
                    db.close()

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
