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


@celery_app.task(name="process_markdown_and_metadata", bind=True)
def process_markdown_and_metadata(
    self, file_id: str, temp_path: str, supabase_folder: str
):
    db_gen = get_db()
    db = next(db_gen)

    try:
        logger.info(f"[START] Processing file_id={file_id}")

        file_record = db.query(Files).filter(Files.id == file_id).first()

        logger.info(f"File_record: {file_record}, file_id: {file_id}")
        if not file_record:
            raise Exception(f"File {file_id} not found")

        file_record.status = "processing"
        db.commit()

 
        if file_record.extension == ".md":
            markdown_text = file_record.content
            md_url = file_record.storage_path

        else:
            md_engine = MarkItDown(enable_plugins=False)

            if not os.path.exists(temp_path):
                raise Exception(f"Temp file not found: {temp_path}")

            result = md_engine.convert(temp_path)
            markdown_text = result.text_content

            if not markdown_text:
                raise Exception("Markdown conversion returned empty content")

            md_filename = f"/{file_record.created_by}/{file_record.project_id}/user/{supabase_folder}/{file_record.name}_convert.md"

            md_file_obj = UploadFile(
                filename=f"{file_record.name}.md",
                file=io.BytesIO(markdown_text.encode("utf-8")),
            )

            md_url = asyncio.run(upload_to_supabase(md_file_obj, md_filename))

            if not md_url:
                raise Exception("Upload to Supabase failed")

        logger.info(f"[MARKDOWN DONE] length={len(markdown_text)}")

    
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
            raise Exception("AI service returned empty response")

        file_metadata = create_user_upload_metadata(
                metadata_response=metadata_response,
                content=markdown_text,
                filename=file_record.name,
            )
        

        if not file_metadata:
            raise Exception("Metadata creation failed")

        logger.info(f"[METADATA DONE]")

    
        file_record.storage_md_path = md_url
        file_record.file_metadata = file_metadata
        file_record.status = "completed"

        db.commit()

        logger.info(f"[SUCCESS] file_id={file_id}")

        return {"status": "completed", "file_id": file_id}

    except Exception as e:
        logger.error(f"[FAILED] file_id={file_id} error={str(e)}")

        db.rollback()

   
        try:
            file_record = db.query(Files).filter(Files.id == file_id).first()
            if file_record:
                file_record.status = "failed"
                db.commit()
        except Exception as inner_e:
            logger.error(f"Failed to update status=failed: {str(inner_e)}")


        raise e

    finally:
        db_gen.close()

   
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as cleanup_err:
            logger.warning(f"Failed to cleanup temp file: {str(cleanup_err)}")
