import os
import io
import logging
import asyncio
from fastapi import UploadFile
from markitdown import MarkItDown

from app.core.celery_app import celery_app
from app.core.database import get_db
from app.core.rag_database import get_rag_db
from app.models.file import Files
from app.core.config import settings
from app.utils.file_handling import upload_to_supabase
from app.utils.call_ai_service import call_ai_service
from app.utils.metadata_utils import create_user_upload_metadata
from app.utils.rag_indexer import index_rag_chunks
from app.core.event_emitter import emitter

logger = logging.getLogger(__name__)


@celery_app.task(name="process_markdown_task", bind=True, max_retries=2)
def process_markdown_task(self, file_id: str, temp_path: str, supabase_folder: str):
    db_gen = get_db()
    db = next(db_gen)

    try:
        logger.info(f"[START] Markdown task file_id={file_id}")

        file_record = db.query(Files).filter(Files.id == file_id).first()
        if not file_record:
            raise Exception(f"File {file_id} not found")

        file_record.status = "processing"
        db.commit()

        emitter.emit(
            {
                "project_id": file_record.project_id,
                "step": "upload",
                "type": "file_status",
                "file_id": str(file_id),
                "status": "processing",
            }
        )

        if file_record.extension == ".md":
            markdown_text = file_record.content
            md_url = file_record.storage_path
        else:
            if not os.path.exists(temp_path):
                raise Exception(f"Temp file not found: {temp_path}")

            md_engine = MarkItDown(enable_plugins=True)
            result = md_engine.convert(temp_path)

            markdown_text = result.text_content
            if not markdown_text:
                raise Exception("Markdown empty")

            md_filename = f"/{file_record.created_by}/{file_record.project_id}/user/{supabase_folder}/{file_record.name}_convert.md"

            md_file_obj = UploadFile(
                filename=f"{file_record.name}.md",
                file=io.BytesIO(markdown_text.encode("utf-8")),
            )

            md_url = asyncio.run(upload_to_supabase(md_file_obj, md_filename))

            if not md_url:
                raise Exception("Upload failed")

        file_record.storage_md_path = md_url

        db.commit()

        logger.info(f"[SUCCESS] Markdown done file_id={file_id}")

        return {
            "file_id": str(file_id),
            "md_text": str(markdown_text),
        }

    except Exception as e:
        logger.error(f"[RETRY] Markdown failed file_id={file_id} error={str(e)}")

        try:
            raise self.retry(exc=e, countdown=5)
        except self.MaxRetriesExceededError:
            logger.error(f"[FAILED] Markdown max retries exceeded file_id={file_id}")

            db.rollback()
            file_record = db.query(Files).filter(Files.id == file_id).first()
            if file_record:
                file_record.status = "failed"
                db.commit()

            emitter.emit(
                {
                    "project_id": file_record.project_id,
                    "step": "upload",
                    "type": "file_status",
                    "file_id": str(file_id),
                    "status": "failed",
                }
            )
            
            raise e

    finally:
        db_gen.close()
        if os.path.exists(temp_path):
            os.remove(temp_path)


@celery_app.task(name="extract_metadata_task", bind=True)
def extract_metadata_task(self, payload: dict):
    db_gen = get_db()
    db = next(db_gen)

    file_id = payload.get("file_id")

    try:
        markdown_text = payload["md_text"]

        logger.info(f"[START] Metadata task file_id={file_id}")

        file_record = db.query(Files).filter(Files.id == file_id).first()
        if not file_record:
            raise Exception(f"File {file_id} not found")

        metadata_payload = {
            "document_id": f"task-{file_id}",
            "content": markdown_text,
            "filename": file_record.name,
        }

        metadata_response = asyncio.run(
            call_ai_service(
                ai_service_url=settings.ai_service_url_metadata_extraction,
                payload=metadata_payload,
                db=db,
                user_id=file_record.created_by,
            )
        )

        if not metadata_response:
            raise Exception("AI empty response")

        file_metadata = create_user_upload_metadata(
            metadata_response=metadata_response,
            content=markdown_text,
            filename=file_record.name,
        )

        if not file_metadata:
            raise Exception("Metadata creation failed")

        file_record.file_type = file_metadata['file_type']
        file_record.file_metadata = file_metadata
        file_record.status = "completed"
        db.commit()

        emitter.emit(
            {
                "project_id": file_record.project_id,
                "step": "upload",
                "type": "file_status",
                "file_id": str(file_id),
                "status": "completed",
            }
        )

        logger.info(f"[SUCCESS] Metadata done file_id={file_id}")

        # Include md_text in returned payload so downstream tasks (indexing)
        # can access the markdown content without re-downloading.
        return {"status": "completed", "file_id": file_id, "md_text": markdown_text}

    except Exception as e:
        logger.error(f"[FAILED] Metadata task file_id={file_id} error={str(e)}")

        db.rollback()

        file_record = db.query(Files).filter(Files.id == file_id).first()
        if file_record:
            file_record.status = "failed"
            db.commit()

        emitter.emit({
            "project_id": file_record.project_id,
            "step": "upload",
            "type": "file_status",
            "file_id": str(file_id),
            "status": "failed",
        })

        raise Exception(str(e))

    finally:
        db_gen.close()


@celery_app.task(name="index_rag_task", bind=True)
def index_rag_task(self, payload: dict):
    local_db_gen = get_db()
    local_db = next(local_db_gen)
    rag_db_gen = get_rag_db()
    rag_db = next(rag_db_gen)

    file_id = payload.get("file_id")

    try:
        markdown_text = payload.get("md_text", "")
        if not markdown_text or not file_id:
            return payload

        file_record = local_db.query(Files).filter(Files.id == file_id).first()
        if not file_record:
            return payload

        metadata = file_record.file_metadata or {}

        # "unknown" since already have fall-back as "stakeholder_requirements", 
        # which if not working by now, should be "unkown" to be treated as error
        document_type = metadata.get("file_type", "unknown") 

        emitter.emit(
            {
                "project_id": file_record.project_id,
                "step": "rag",
                "type": "rag_status",
                "file_id": str(file_record.id),
                "document_type": document_type,
                "status": "processing",
            }
        )

        inserted = index_rag_chunks(
            rag_db,
            file_id=str(file_record.id),
            project_id=file_record.project_id,
            document_type=document_type,
            markdown_text=markdown_text,
        )

        rag_db.commit()
        payload["rag_indexed"] = inserted > 0

        emitter.emit(
            {
                "project_id": file_record.project_id,
                "step": "rag",
                "type": "rag_status",
                "file_id": str(file_record.id),
                "document_type": document_type,
                "status": "completed",
                "chunks": inserted,
            }
        )
        return payload
    except Exception as e:
        logger.error(f"RAG index failed file_id={file_id} error={str(e)}")
        payload["rag_indexed"] = False
        rag_db.rollback()

        if file_id:
            file_record = local_db.query(Files).filter(Files.id == file_id).first()
            if file_record:
                emitter.emit(
                    {
                        "project_id": file_record.project_id,
                        "step": "rag",
                        "type": "rag_status",
                        "file_id": str(file_record.id),
                        "document_type": (file_record.file_metadata or {}).get(
                            "primary_type",
                            "unknown",
                        ),
                        "status": "failed",
                        "error": str(e),
                    }
                )

        raise Exception(str(e))
    finally:
        local_db_gen.close()
        rag_db_gen.close()
