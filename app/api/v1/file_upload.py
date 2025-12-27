from typing import List
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
import tempfile
import os
from markitdown import MarkItDown
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.file import Files
from app.models.user import User
from app.utils.file_handling import has_extension, upload_to_supabase
from app.schemas.folder import CreateFolderRequest
from app.utils.folder_utils import create_default_folder
from app.utils.get_unique_name import get_unique_diagram_name

router = APIRouter()


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
            )
            db.add(raw_record)
            db.commit()

        # Chỉ trả về status code 200, không trả về dữ liệu
        return {"status": "ok"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
