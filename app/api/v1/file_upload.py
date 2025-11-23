from typing import List
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
import tempfile
import os
from markitdown import MarkItDown
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.project_raw_file import ProjectRawFile
from app.models.project_md_file import ProjectMdFile
from app.models.user import User
from app.utils.file_handling import has_extension, upload_to_supabase

router = APIRouter()


@router.post("/upload", status_code=200)
async def upload(
    project_id: int = Form(...),
    files: List[UploadFile] = File([]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        for file in files:
            if not file.filename or not has_extension(file.filename):
                continue

            # ================================================================
            # 1) Tạo file tạm để convert → markdown
            # ================================================================
            suffix = os.path.splitext(file.filename)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name

            # ================================================================
            # 2) Upload bản RAW lên Supabase
            # ================================================================
            file.file.seek(0)
            raw_url = await upload_to_supabase(file)

            if not raw_url:
                raise Exception(f"Failed to upload raw file {file.filename}")

            raw_record = ProjectRawFile(
                file_path=raw_url,
                file_name=file.filename,
                project_id=project_id,
                user_id=current_user.id,
            )
            db.add(raw_record)
            db.flush()

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
            md_filename = file.filename + ".md"

            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".md") as md_tmp:
                md_tmp.write(markdown_text)
                md_tmp_path = md_tmp.name

            md_upload = UploadFile(filename=md_filename, file=open(md_tmp_path, "rb"))
            md_url = await upload_to_supabase(md_upload)
            os.remove(md_tmp_path)

            if not md_url:
                raise Exception(f"Failed to upload md file for {file.filename}")

            md_record = ProjectMdFile(
                raw_file_id=raw_record.id,
                project_id=project_id,
                user_id=current_user.id,
                file_name=md_filename,
                file_path=md_url,
            )
            db.add(md_record)

        db.commit()

        # Chỉ trả về status code 200, không trả về dữ liệu
        return {"status": "ok"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
