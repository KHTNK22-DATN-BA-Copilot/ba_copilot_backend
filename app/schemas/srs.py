from pydantic import BaseModel, Field
from typing import Annotated, Dict, Any, Optional, List


class SRSRequest(BaseModel):
    project_id: int
    project_name: str
    description: str = Field(..., description="Project description or context")
    files: Optional[List[str]] = Field(
        None,
        description="List of base64-encoded file contents or text extracted from uploaded documents",
    )


class SRSGenerateResponse(BaseModel):
    """Response schema for SRS generation."""

    document_id: str = Field(
        ..., description="Unique identifier for the generated document"
    )
    user_id: Optional[str] = Field(
        None, description="User ID who generated the document"
    )
    generated_at: str = Field(..., description="Timestamp when document was generated")
    input_description: str = Field(
        ..., description="Original input used for generation"
    )
    document: Dict[str, Any] = Field(
        ..., description="Generated SRS document in JSON format"
    )
    status: str = Field(..., description="Generation status")


class SRSDocument(BaseModel):
    """SRS document model."""

    document_id: str
    project_name: str
    content: str
    metadata: Dict[str, Any]


class SRSExportResponse(BaseModel):
    """SRS export response model."""

    download_url: str
    expires_at: str
    file_size_bytes: int
    format: str
