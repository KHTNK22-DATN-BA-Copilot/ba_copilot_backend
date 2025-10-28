from pydantic import BaseModel


class OCRResponse(BaseModel):
    """Response schema for OCR endpoint"""
    filename: str
    extracted_text: str
    file_type: str
    status: str

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "document.pdf",
                "extracted_text": "This is the extracted text from the document...",
                "file_type": "pdf",
                "status": "success"
            }
        }
