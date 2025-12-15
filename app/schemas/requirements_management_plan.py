from pydantic import BaseModel, Field
from typing import Annotated, Dict, Any, Optional, List
from datetime import datetime


class RMPGenerateResponse(BaseModel):
    """Response schema for Requirements Management Plan generation."""

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
    document: str = Field(
        ...,
        description="Generated Requirements Management Plan document in Markdown format",
    )
    status: str = Field(..., description="Generation status")


class GetRMPResponse(BaseModel):
    document_id: str
    project_name: str
    content: str
    status: str
    updated_at: datetime


class UpdateRMPResponse(BaseModel):
    document_id: str
    project_name: str
    content: str
    status: str
    updated_at: datetime


class RMPListResponse(BaseModel):
    documents: List[GetRMPResponse] = Field(..., description="List of RMP documents")


class RMPDocument(BaseModel):
    """Requirements Management Plan document model."""

    document_id: str
    project_name: str
    content: str
    metadata: Dict[str, Any]
