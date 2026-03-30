from pydantic import BaseModel, Field
from typing import Annotated, Dict, Any, Optional, List
from datetime import datetime

from app.schemas.base_response import BaseResponseModel


class DesignGenerateResponse(BaseResponseModel):
    """Unified response schema for Design generation."""

    document_id: str = Field(
        ..., description="Unique identifier for the generated document"
    )
    user_id: Optional[str] = Field(
        None, description="User ID who generated the document"
    )
    generated_at: datetime = Field(..., description="Timestamp when document was generated")
    input_description: str = Field(
        ..., description="Original input used for generation"
    )
    document: str = Field(..., description="Generated content (Markdown/Mermaid) code")
    design_type: str = Field(..., description="Type of design (e.g., hld-arch, lld-db)")
    status: str = Field(..., description="Generation status")
    recommend_documents: Optional[List[str]] = None
    file_size_kb:float=Field(...,description="File size")


class GetDesignResponse(BaseResponseModel):
    document_id: str
    project_name: str
    content: str
    design_type: str
    status: str
    updated_at: datetime
    file_size_kb: float


class UpdateDesignResponse(BaseResponseModel):
    document_id: str
    project_name: str
    content: str
    updated_at: datetime
    file_size_kb: float

class DesignListResponse(BaseResponseModel):
    documents: List[GetDesignResponse] = Field(
        ..., description="List of design documents"
    )


class DesignDocument(BaseResponseModel):
    document_id: str
    project_name: str
    content: str
    metadata: Dict[str, Any]
