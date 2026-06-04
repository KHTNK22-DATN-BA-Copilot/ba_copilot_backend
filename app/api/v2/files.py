import logging
import mimetypes
import os
import tempfile
from typing import List, Optional
from urllib.parse import quote

from celery import chain
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import Permission, ProjectAccessContext, require_permission
from app.models.file import Files
from app.models.folder import Folder
from app.schemas.file import UploadedFileResponse, UploadResponse
from app.tasks.file_tasks import extract_metadata_task, process_markdown_task, index_rag_task
from app.utils.file_handling import (
    delete_file_from_supabase,
    download_file_from_supabase,
    extract_text_from_binary,
    has_extension,
    upload_to_supabase,
)
from app.utils.get_unique_name import get_unique_diagram_name
from app.core.rag_database import get_rag_db
from app.utils.rag_indexer import delete_rag_chunks_for_file

router = APIRouter()
logger = logging.getLogger(__name__)

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


@router.post("/{project_id}/files/upload", response_model=UploadResponse)
async def upload_files(
    project_id: int,
    folder_id: Optional[int] = Form(None),
    path: str = Form(""),
    files: List[UploadFile] = File([]),
    access: ProjectAccessContext = Depends(require_permission(Permission.FILE_WRITE)),
    db: Session = Depends(get_db),
):
    if folder_id is not None:
        folder = (
            db.query(Folder)
            .filter(
                Folder.id == folder_id,
                Folder.project_id == project_id,
                Folder.is_deleted == False,
            )
            .first()
        )
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

    uploaded_files = []
    storage_folder = path.strip("/") or "root"

    try:
        for file in files:
            if not file.filename or not has_extension(file.filename):
                continue

            suffix = os.path.splitext(file.filename)[1].lower()
            if suffix not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Unsupported file type '{suffix}'. Allowed formats: "
                        "txt, md, csv, pdf, docx, pptx, png, jpg, jpeg and gif."
                    ),
                )

            file_name = os.path.splitext(file.filename)[0]
            unique_title = get_unique_diagram_name(db, file_name, project_id, suffix)

            binary_content = await file.read()
            file_size_kb = round(len(binary_content) / 1024, 2)

            try:
                raw_text = extract_text_from_binary(binary_content, suffix)
            except Exception as exc:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"Failed to extract raw text from {file.filename}: {str(exc)}"
                    ),
                )

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(binary_content)
                tmp_path = tmp.name

            try:
                file.file.seek(0)
                raw_filename = (
                    f"/{access.user.id}/{project_id}/user/"
                    f"{storage_folder}/{unique_title}{suffix}"
                )
                raw_url = await upload_to_supabase(file, raw_filename)
                if not raw_url:
                    raise Exception(f"Failed to upload raw file {file.filename}")
            except Exception as exc:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"Error processing Upload/MarkItDown for "
                        f"{file.filename}: {str(exc)}"
                    ),
                )
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

            raw_record = Files(
                project_id=project_id,
                folder_id=folder_id,
                created_by=access.user.id,
                updated_by=access.user.id,
                name=unique_title,
                content=raw_text,
                extension=suffix,
                storage_path=raw_url,
                file_category="user upload",
                file_size=file_size_kb,
                file_type=suffix,
                status="pending",
            )
            db.add(raw_record)
            db.commit()
            db.refresh(raw_record)

            temp_path = os.path.join("temp_storage", f"{raw_record.id}{suffix}")
            os.makedirs("temp_storage", exist_ok=True)
            with open(temp_path, "wb") as output:
                output.write(binary_content)

            chain(
                process_markdown_task.s(str(raw_record.id), temp_path, storage_folder),
                extract_metadata_task.s(),
                index_rag_task.s(),
            ).apply_async()

            uploaded_files.append(
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

        return UploadResponse(status="ok", files=uploaded_files)

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{project_id}/files/{file_id}/export")
async def export_file(
    project_id: int,
    file_id: str,
    access: ProjectAccessContext = Depends(require_permission(Permission.FILE_READ)),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Files)
        .filter(
            Files.id == file_id,
            Files.project_id == project_id,
            Files.status != "deleted",
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_stream = await download_file_from_supabase(doc.storage_path)
        filename = f"{doc.name}{doc.extension or ''}"
        media_type, _ = mimetypes.guess_type(filename)
        if not media_type:
            media_type = "application/octet-stream"

        return StreamingResponse(
            file_stream,
            media_type=media_type,
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"; '
                    f"filename*=UTF-8''{quote(filename)}"
                )
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Error when exporting file '{file_id}': {exc}")
        raise HTTPException(status_code=500, detail="Failed to export file")


@router.delete("/{project_id}/files/{file_id}")
async def delete_file(
    project_id: int,
    file_id: str,
    access: ProjectAccessContext = Depends(require_permission(Permission.FILE_DELETE)),
    db: Session = Depends(get_db),
):
    rag_db_gen = get_rag_db()
    rag_db = next(rag_db_gen)

    file = ( 
        db.query(Files)
        .filter(
            Files.id == file_id,
            Files.project_id == project_id,
            Files.status != "deleted",
        )
        .first()
    )
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    delete_rag_chunks_for_file(rag_db, file_id=str(file_id))
    rag_db.commit()


    try:
        if file.storage_path:
            await delete_file_from_supabase(file.storage_path)
        if file.storage_md_path:
            await delete_file_from_supabase(file.storage_md_path)

        db.delete(file)
        db.commit()
        return {"status": "deleted", "file_id": file_id}
    except HTTPException:
        db.rollback()
        rag_db.rollback()
        raise

    except Exception as e:
        db.rollback()
        rag_db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        rag_db_gen.close()
