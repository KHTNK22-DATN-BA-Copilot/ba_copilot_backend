
import logging
import uuid
from fastapi import HTTPException, status, UploadFile
from app.utils.supabase_client import supabase
from PyPDF2 import PdfReader
import docx2txt
import io
import tempfile
import re


logger = logging.getLogger(__name__)

SUPABASE_BUCKET = "uploads"


async def upload_to_supabase(file: UploadFile) -> str | None:
    """Upload file lên Supabase và trả về public URL."""
    try:
        file_name = f"{uuid.uuid4()}_{file.filename}"
        file_data = await file.read()

        res = supabase.storage.from_(SUPABASE_BUCKET).upload(file_name, file_data)

        if not res.path:
            logger.error(f"Failed to upload {file.filename}")
            return None

        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(file_name)
        logger.info(f"Uploaded {file.filename} to Supabase → {public_url}")
        return public_url

    except Exception as e:
        logger.exception(f"Upload failed for {file.filename}: {e}")
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




def format_srs_to_markdown(document: dict) -> str:
    lines = []

    # Tiêu đề chính
    title = document.get("title", "Untitled Document").strip()
    lines.append(f"# {title}\n")

    # Mô tả chi tiết
    detail = document.get("detail", "").strip()
    if detail:
        lines.append("## Detailed Description\n")
        lines.append(detail)
        lines.append("")  # dòng trống

    # --- Hàm phụ để tách "1. ..." "2. ..." ---
    def split_requirements(text: str):
        text = text.strip()
        # Nếu có \n thì tách theo dòng
        if "\n" in text:
            items = [t.strip() for t in text.splitlines() if t.strip()]
        else:
            # Nếu không có \n thì tách theo số thứ tự (giữ nguyên phần số)
            items = re.findall(r"\d+\.[^0-9]+(?=\d+\.|$)", text)
            items = [t.strip() for t in items if t.strip()]
        return items

    # --- Functional Requirements ---
    func_req = document.get("functional_requirements", "").strip()
    if func_req:
        lines.append("## Functional Requirements\n")
        for line in split_requirements(func_req):
            lines.append(f"- {line}")
        lines.append("")

    # --- Non-Functional Requirements ---
    non_func_req = document.get("non_functional_requirements", "").strip()
    if non_func_req:
        lines.append("## Non-Functional Requirements\n")
        for line in split_requirements(non_func_req):
            lines.append(f"- {line}")
        lines.append("")

    markdown_output = "\n".join(lines).strip()
    return markdown_output
