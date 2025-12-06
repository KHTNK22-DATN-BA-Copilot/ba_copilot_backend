import logging
import os
from typing import List
import uuid
from fastapi import UploadFile
from app.utils.supabase_client import supabase
from PyPDF2 import PdfReader
import docx2txt
import io
import tempfile
import unicodedata
import re

logger = logging.getLogger(__name__)

SUPABASE_BUCKET = "uploads"


def sanitize_filename(filename: str) -> str:
    name, ext = os.path.splitext(filename)

    name = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")

    name = re.sub(r"\s+", "_", name)

    name = re.sub(r"[^a-zA-Z0-9._/-]", "", name)

    return f"{name}{ext}"


async def upload_to_supabase(file: UploadFile,new_name:str|None=None) -> str | None:
    """Upload file lên Supabase và trả về public URL."""
    try:
        filename_to_use = new_name if new_name else file.filename
        new_file_name = sanitize_filename(filename_to_use)
        file_data = await file.read()

        res = supabase.storage.from_(SUPABASE_BUCKET).upload(new_file_name, file_data)

        if not res.path:
            logger.error(f"Failed to upload {file.filename}")
            return None

        logger.info(f"Uploaded {file.filename} to Supabase → {res.path}")
        return res.path

    except Exception as e:
        logger.exception(f"Upload failed for {file.filename}: {e}")
        return None


async def list_file_from_supabase(existing_files_db: List):
    existing_files_uploadfile = []
    for file in existing_files_db:
        try:
            file_bytes = supabase.storage.from_(SUPABASE_BUCKET).download(
                file.file_path
            )
            existing_files_uploadfile.append(
                UploadFile(
                    filename=file.file_path.split("/")[-1], file=io.BytesIO(file_bytes)
                )
            )
        except Exception as e:
            logger.exception(f"Error when getting file '{file}': {e}")
    return existing_files_uploadfile


async def update_file_from_supabase(file_path: str,file: UploadFile) -> str | None:

    file_data = await file.read()
    try:
        res = supabase.storage.from_(SUPABASE_BUCKET).update(file_path,file_data)
        return res.path

    except Exception as e:
        logger.exception(f"Error when getting file '{file_path}': {e}")
        return None


async def extract_text_from_file(file: UploadFile) -> str:
    """Trích xuất nội dung text từ file upload."""
    content = ""

    # Đọc nội dung file bytes
    file_content = await file.read()
    file.file.seek(0)  # Reset con trỏ nếu cần upload lại sau

    if file.filename.endswith(".txt"):
        content = file_content.decode("utf-8", errors="ignore")
    elif file.filename.endswith(".pdf"):
        pdf_reader = PdfReader(io.BytesIO(file_content))
        content = "\n".join([page.extract_text() or "" for page in pdf_reader.pages])
    elif file.filename.endswith((".doc", ".docx")):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(file_content)
            tmp.flush()
            content = docx2txt.process(tmp.name)
    else:
        content = f"[Unsupported file type: {file.filename}]"

    return content


def has_extension(filename: str) -> bool:
    return "." in filename and not filename.startswith(".")
