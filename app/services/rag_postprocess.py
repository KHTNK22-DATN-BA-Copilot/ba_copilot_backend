import logging
from typing import Awaitable, Callable, Optional

from app.tasks.file_tasks import index_rag_task

logger = logging.getLogger(__name__)


async def queue_rag_indexing(
    *,
    step: str,
    file_id: str,
    doc_type: str,
    markdown_text: str,
    emit_event: Optional[Callable[[dict], Awaitable[None]]] = None,
) -> Optional[str]:
    if not file_id or not markdown_text:
        logger.warning(
            "Skip RAG indexing because file_id or markdown_text is missing "
            f"for step={step}, doc_type={doc_type}"
        )
        return None

    async_result = index_rag_task.delay(
        {
            "file_id": file_id,
            "md_text": markdown_text,
        }
    )

    logger.info(
        "Queued RAG indexing for step=%s doc_type=%s file_id=%s task_id=%s",
        step,
        doc_type,
        file_id,
        async_result.id,
    )

    if emit_event:
        try:
            await emit_event(
                {
                    "type": "rag_index_queued",
                    "step": step,
                    "doc_type": doc_type,
                    "file_id": file_id,
                    "task_id": async_result.id,
                }
            )
        except Exception as exc:
            logger.warning(
                "Failed to emit rag_index_queued event for file_id=%s: %s",
                file_id,
                exc,
            )

    return async_result.id