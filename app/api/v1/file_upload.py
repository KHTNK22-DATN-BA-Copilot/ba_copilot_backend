from io import BytesIO
from typing import List
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
import tempfile
import os
import logging
from fastapi.responses import StreamingResponse
from markitdown import MarkItDown
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.config import settings
from app.models.file import Files
from app.models.user import User
from app.utils.file_handling import has_extension, upload_to_supabase
from app.schemas.folder import CreateFolderRequest
from app.utils.folder_utils import create_default_folder
from app.utils.get_unique_name import get_unique_diagram_name
from app.utils.call_ai_service import call_ai_service
from app.utils.metadata_utils import create_user_upload_metadata

router = APIRouter()
logger = logging.getLogger(__name__)


async def list_file(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_list = (
        db.query(Files)
        .filter(
            Files.project_id == project_id,
            Files.created_by == current_user.id,
        )
        .order_by(Files.created_at.asc())
        .all()
    )

    return [
        (
            file.storage_md_path
            if file.file_category == "user upload"
            else file.storage_path
        )
        for file in file_list
    ]


@router.post("/upload/{project_id}/{folder_id}", status_code=200)
async def upload(
    project_id: int,
    folder_id:int,
    path: str=Form(),
    files: List[UploadFile] = File([]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    try:
        for file in files:
            if not file.filename or not has_extension(file.filename):
                continue

            suffix = os.path.splitext(file.filename)[1]
            file_name = os.path.splitext(file.filename)[0]
            unique_title = get_unique_diagram_name(db, file_name, project_id, suffix)

            # ================================================================
            # 1) Tạo file tạm để convert → markdown
            # ================================================================
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name

            # ================================================================
            # 2) Upload bản RAW lên Supabase
            # ================================================================
            file.file.seek(0)
            raw_filename = f"/{current_user.id}/{project_id}/user/{path}/{unique_title}.{suffix}"
            raw_url = await upload_to_supabase(file,raw_filename)

            if not raw_url:
                raise Exception(f"Failed to upload raw file {file.filename}")

            # ================================================================
            # 3) Convert RAW → Markdown
            # ================================================================
            try:
                md = MarkItDown(enable_plugins=False)
                result = md.convert(tmp_path)
                markdown_text = result.text_content
            except Exception as e:
                raise HTTPException(500, f"Markdown convert failed: {str(e)}")
            finally:
                os.remove(tmp_path)

            # ================================================================
            # 4) Upload file .md lên Supabase
            # ================================================================
            md_filename = f"/{current_user.id}/{project_id}/user/{path}/{unique_title}.md"

            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".md") as md_tmp:
                md_tmp.write(markdown_text)
                md_tmp_path = md_tmp.name

            md_upload = UploadFile(filename=md_filename, file=open(md_tmp_path, "rb"))
            md_url = await upload_to_supabase(md_upload)
            os.remove(md_tmp_path)

            if not md_url:
                raise Exception(f"Failed to upload md file for {file.filename}")

            # ================================================================
            # 5) Call AI service to extract metadata from markdown
            # ================================================================
            file_metadata = {}
            try:
                # Generate a temporary ID for the document (will be replaced by actual UUID)
                temp_doc_id = f"temp-{unique_title}"

                metadata_payload = {
                    "document_id": temp_doc_id,
                    "content": markdown_text,
                    "filename": file.filename
                }

                metadata_response = await call_ai_service(
                    ai_service_url=settings.ai_service_url_metadata_extraction,
                    payload=metadata_payload,
                    retries=2,  # Fewer retries for metadata extraction
                    read_timeout=120  # 2 minutes timeout
                )

                # Parse metadata response using utility function
                if metadata_response and "response" in metadata_response:
                    file_metadata = create_user_upload_metadata(
                        metadata_response=metadata_response,
                        content=markdown_text,
                        filename=file.filename
                    )
                    logger.info(f"Metadata extracted for {file.filename}")
            except Exception as me:
                # Log error but don't fail the upload
                logger.warning(f"Metadata extraction failed for {file.filename}: {str(me)}")
                file_metadata = {
                    "extraction_status": "failed",
                    "error": str(me)
                }

            raw_record = Files(
                project_id=project_id,
                folder_id=folder_id,
                created_by=current_user.id,
                updated_by=current_user.id,
                name=file.filename,
                storage_path=raw_url,
                storage_md_path=md_url,
                file_category="user upload",
                file_type=suffix,
                file_metadata=file_metadata,
            )
            db.add(raw_record)
            db.commit()

        # Chỉ trả về status code 200, không trả về dữ liệu
        return {"status": "ok"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{document_id}", response_class=StreamingResponse)
async def export_markdown(
   
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    doc = (
        db.query(Files)
        .filter(
            Files.id == document_id,
            Files.created_by == current_user.id,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")

    if current_user.id != doc.created_by:
        raise HTTPException(
            status_code=403, detail="You don't have permission to access this document."
        )

    file_stream = BytesIO(doc.content.encode("utf-8"))
    filename = f"{doc.name.replace(' ', '_')}.md"

    return StreamingResponse(
        file_stream,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
