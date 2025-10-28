import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.schemas.ocr import OCRResponse
from app.utils.ocr_utils import extract_text_from_file

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=OCRResponse)
async def ocr_extract_text(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Endpoint OCR để trích xuất text từ các file:
    - Images: .jpg, .png, .jpeg
    - Documents: .pdf, .docx, .doc
    - Markdown: .md
    - Text: .txt
    """
    logger.info(f"User {current_user.email} requested OCR for file: {file.filename}")

    # Kiểm tra định dạng file
    allowed_extensions = [
        ".jpg", ".jpeg", ".png",  # Images
        ".pdf",                    # PDF
        ".doc", ".docx",          # Word documents
        ".md",                     # Markdown
        ".txt"                     # Text files
    ]

    file_ext = None
    for ext in allowed_extensions:
        if file.filename.lower().endswith(ext):
            file_ext = ext
            break

    if not file_ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Allowed formats: {', '.join(allowed_extensions)}"
        )

    try:
        # Trích xuất text từ file
        extracted_text = await extract_text_from_file(file)

        if not extracted_text or extracted_text.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract text from the file. The file may be empty or corrupted."
            )

        logger.info(f"Successfully extracted {len(extracted_text)} characters from {file.filename}")

        return OCRResponse(
            filename=file.filename,
            extracted_text=extracted_text,
            file_type=file_ext.lstrip('.'),
            status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"OCR extraction failed for {file.filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text from file: {str(e)}"
        )
