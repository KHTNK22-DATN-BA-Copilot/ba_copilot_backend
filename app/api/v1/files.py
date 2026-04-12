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
from app.utils.file_handling import has_extension, upload_to_supabase, delete_file_from_supabase,extract_text_from_binary
from app.schemas.file import UploadedFileResponse, UploadResponse
from app.utils.folder_utils import create_default_folder
from app.utils.get_unique_name import get_unique_diagram_name
from app.tasks.file_tasks import process_markdown_and_metadata

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


ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".pdf",
    ".docx",
    ".doc",
    ".pptx",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
}


@router.post(
    "/upload/{project_id}/{folder_id}",
    response_model=UploadResponse,
)
async def upload(
    project_id: int,
    folder_id: int,
    path: str = Form(),
    files: List[UploadFile] = File([]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    upload_files = []
    logger.info(f"Files {files}")

    try:
        for file in files:
            if not file.filename or not has_extension(file.filename):
                continue

            suffix = os.path.splitext(file.filename)[1].lower()
            if suffix not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type '{suffix}'. Allowed formats: txt, md, csv, pdf, docx, pptx, png, jpg, jpeg and gif.",
                )

            file_name = os.path.splitext(file.filename)[0]
            logger.info(f"file name {file_name}")
            unique_title = get_unique_diagram_name(db, file_name, project_id, suffix)
            logger.info(f"unique name {unique_title}")

            binary_content = await file.read()
            file_size_bytes = len(binary_content)
            file_size_kb = round(file_size_bytes / 1024, 2)

            try:
                raw_text = extract_text_from_binary(binary_content, suffix)
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to extract raw text from {file.filename}: {str(e)}",
                )

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(binary_content)
                tmp_path = tmp.name

            try:

                file.file.seek(0)
                raw_filename = f"/{current_user.id}/{project_id}/user/{path}/{unique_title}{suffix}"
                raw_url = await upload_to_supabase(file, raw_filename)

                if not raw_url:
                    raise Exception(f"Failed to upload raw file {file.filename}")

                # if suffix == ".md":

                #     markdown_text = raw_text
                #     md_url = raw_url
                # else:

                #     md = MarkItDown(enable_plugins=False)
                #     result = md.convert(tmp_path)
                #     markdown_text = result.text_content

                #     md_filename = f"/{current_user.id}/{project_id}/user/{path}/{unique_title}_convert.md"

                #     with tempfile.NamedTemporaryFile(
                #         "w", delete=False, suffix=".md", encoding="utf-8"
                #     ) as md_tmp:
                #         md_content = (
                #             markdown_text
                #             if markdown_text.strip()
                #             else f"![{file_name}]({raw_url})"
                #         )
                #         md_tmp.write(md_content)
                #         md_tmp_path = md_tmp.name

                #     try:
                #         md_upload = UploadFile(
                #             filename=md_filename, file=open(md_tmp_path, "rb")
                #         )
                #         md_url = await upload_to_supabase(md_upload)
                #         if not md_url:
                #             raise Exception(
                #                 f"Failed to upload md file for {file.filename}"
                #             )
                #     finally:
                #         if os.path.exists(md_tmp_path):
                #             os.remove(md_tmp_path)

            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing Upload/MarkItDown for {file.filename}: {str(e)}",
                )
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            # file_metadata = {}
            # try:
            #     temp_doc_id = f"temp-{unique_title}"
            #     metadata_payload = {
            #         "document_id": temp_doc_id,
            #         "content": markdown_text,
            #         "filename": file.filename,
            #     }

            #     metadata_response = await call_ai_service(
            #         ai_service_url=settings.ai_service_url_metadata_extraction,
            #         payload=metadata_payload,
            #         retries=2,
            #         read_timeout=120,
            #     )

            #     if metadata_response and "response" in metadata_response:
            #         file_metadata = create_user_upload_metadata(
            #             metadata_response=metadata_response,
            #             content=markdown_text,
            #             filename=file.filename,
            #         )
            #         logger.info(f"Metadata extracted for {file.filename}")
            # except Exception as me:
            #     logger.warning(
            #         f"Metadata extraction failed cho {file.filename}: {str(me)}"
            #     )
            #     file_metadata = {"extraction_status": "failed", "error": str(me)}

            raw_record = Files(
                project_id=project_id,
                folder_id=folder_id,
                created_by=current_user.id,
                updated_by=current_user.id,
                name=unique_title,
                content=raw_text,
                extension=suffix,
                storage_path=raw_url,
                # storage_md_path=md_url,
                file_category="user upload",
                file_size=file_size_kb,
                file_type=suffix,
                status="pending",
                # file_metadata=file_metadata,
            )
            db.add(raw_record)
            db.commit()
            db.refresh(raw_record)

            temp_path = os.path.join("temp_storage", f"{raw_record.id}{suffix}")
            os.makedirs("temp_storage", exist_ok=True)
            with open(temp_path, "wb") as f:
                f.write(binary_content)

            process_markdown_and_metadata.delay(str(raw_record.id), temp_path, path)

            upload_files.append(
                UploadedFileResponse(
                    id=str(raw_record.id),
                    name=raw_record.name,
                    size_kb=file_size_kb,
                    type=raw_record.extension,
                    content=raw_text,
                    created_at=raw_record.created_at,
                    status=raw_record.status,
                )
            )

        return UploadResponse(status="ok", files=upload_files)

    except HTTPException as he:
        db.rollback()
        raise he
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
    filename = f"{doc.name.replace(' ', '_')}.{doc.extension}"

    return StreamingResponse(
        file_stream,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.delete("/{file_id}", status_code=200)
async def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:

        file = (
            db.query(Files)
            .filter(Files.id == file_id, Files.created_by == current_user.id)
            .first()
        )

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        if file.storage_path:
            await delete_file_from_supabase(file.storage_path)

        if file.storage_md_path:
            await delete_file_from_supabase(file.storage_md_path)

        db.delete(file)
        db.commit()

        return {"status": "deleted", "file_id": file_id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
