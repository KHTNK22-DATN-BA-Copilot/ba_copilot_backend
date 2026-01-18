from pydantic import BaseModel, Field
from typing import Annotated, Dict, Any, Optional, List
from datetime import datetime


class DesignGenerateResponse(BaseModel):
    """Unified response schema for Design generation."""

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
    document: str = Field(..., description="Generated content (Markdown/Mermaid) code")
    design_type: str = Field(..., description="Type of design (e.g., hld-arch, lld-db)")
    status: str = Field(..., description="Generation status")
    recommend_documents: Optional[List[str]] = None


class GetDesignResponse(BaseModel):
    document_id: str
    project_name: str
    content: str
    design_type: str
    status: str
    updated_at: datetime


class UpdateDesignResponse(BaseModel):
    document_id: str
    project_name: str
    content: str
    status: str
    updated_at: datetime


class DesignListResponse(BaseModel):
    documents: List[GetDesignResponse] = Field(
        ..., description="List of design documents"
    )


class DesignDocument(BaseModel):
    document_id: str
    project_name: str
    content: str
    metadata: Dict[str, Any]
