import os
import io
import logging
import asyncio
from fastapi import UploadFile
from markitdown import MarkItDown

from app.core.celery_app import celery_app
from app.core.database import get_db
from app.models.file import Files
from app.core.config import settings
from app.utils.file_handling import upload_to_supabase
from app.utils.call_ai_service import call_ai_service
from app.utils.metadata_utils import create_user_upload_metadata

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

        if file_record.extension == ".md":
            markdown_text = file_record.content
            md_url = file_record.storage_path
        else:
            if not os.path.exists(temp_path):
                raise Exception(f"Temp file not found: {temp_path}")

            md_engine = MarkItDown(enable_plugins=False)
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

            raise e

    finally:
        db_gen.close()
        if os.path.exists(temp_path):
            os.remove(temp_path)


@celery_app.task(name="extract_metadata_task", bind=True)
def extract_metadata_task(self, payload: dict):
    db_gen = get_db()
    db = next(db_gen)

    try:
        file_id = payload["file_id"]
        markdown_text = payload["md_text"]

        logger.info(f"[START] Metadata task file_id={file_id}")

        file_record = db.query(Files).filter(Files.id == file_id).first()

        metadata_payload = {
            "document_id": f"task-{file_id}",
            "content": markdown_text,
            "filename": file_record.name,
        }

        metadata_response = asyncio.run(
            call_ai_service(
                ai_service_url=settings.ai_service_url_metadata_extraction,
                payload=metadata_payload,
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

        file_record.file_metadata = file_metadata
        file_record.status = "completed"
        db.commit()

        logger.info(f"[SUCCESS] Metadata done file_id={file_id}")

        return {"status": "completed", "file_id": file_id}

    except Exception as e:
        logger.error(
            f"[FAILED] Metadata max retries exceeded file_id={payload['file_id']}"
        )

        db.rollback()
        file_record = db.query(Files).filter(Files.id == payload["file_id"]).first()
        if file_record:
            file_record.status = "failed"
            db.commit()

        raise e

    finally:
        db_gen.close()
