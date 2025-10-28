import io
import logging
import tempfile
from fastapi import UploadFile
from PyPDF2 import PdfReader
import docx2txt
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)


async def extract_text_from_file(file: UploadFile) -> str:
    """
    Trích xuất text từ nhiều định dạng file:
    - Images (.jpg, .png, .jpeg) - sử dụng OCR
    - PDF (.pdf)
    - Word documents (.doc, .docx)
    - Markdown (.md)
    - Text files (.txt)
    """
    content = ""
    filename = file.filename.lower()

    try:
        # Đọc nội dung file bytes
        file_content = await file.read()
        await file.seek(0)  # Reset con trỏ file

        # Text files (.txt)
        if filename.endswith(".txt"):
            content = file_content.decode("utf-8", errors="ignore")
            logger.info(f"Extracted text from TXT file: {file.filename}")

        # Markdown files (.md)
        elif filename.endswith(".md"):
            content = file_content.decode("utf-8", errors="ignore")
            logger.info(f"Extracted text from Markdown file: {file.filename}")

        # PDF files (.pdf)
        elif filename.endswith(".pdf"):
            pdf_reader = PdfReader(io.BytesIO(file_content))
            content = "\n".join([page.extract_text() or "" for page in pdf_reader.pages])
            logger.info(f"Extracted text from PDF file: {file.filename} ({len(pdf_reader.pages)} pages)")

        # Word documents (.doc, .docx)
        elif filename.endswith((".doc", ".docx")):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                tmp.write(file_content)
                tmp.flush()
                content = docx2txt.process(tmp.name)
            logger.info(f"Extracted text from Word document: {file.filename}")

        # Image files (.jpg, .jpeg, .png) - using OCR
        elif filename.endswith((".jpg", ".jpeg", ".png")):
            image = Image.open(io.BytesIO(file_content))
            # Sử dụng pytesseract để OCR
            content = pytesseract.image_to_string(image, lang='eng+vie')  # Hỗ trợ tiếng Anh và tiếng Việt
            logger.info(f"Extracted text from image using OCR: {file.filename}")

        else:
            content = f"[Unsupported file type: {file.filename}]"
            logger.warning(f"Unsupported file type: {file.filename}")

    except Exception as e:
        logger.exception(f"Error extracting text from {file.filename}: {e}")
        raise Exception(f"Failed to extract text: {str(e)}")

    return content.strip()
