from pydantic import BaseModel, Field
from typing import Annotated, Dict, Any, Optional, List
from datetime import datetime


class HLRGenerateResponse(BaseModel):
    """Response schema for High-Level Requirements generation."""

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
        ..., description="Generated High-Level Requirements document in Markdown format"
    )
    status: str = Field(..., description="Generation status")


class GetHLRResponse(BaseModel):
    document_id: str
    project_name: str
    content: str
    status: str
    updated_at: datetime


class UpdateHLRResponse(BaseModel):
    document_id: str
    project_name: str
    content: str
    status: str
    updated_at: datetime


class HLRListResponse(BaseModel):
    documents: List[GetHLRResponse] = Field(..., description="List of HLR documents")


class HLRDocument(BaseModel):
    """High-Level Requirements document model."""

    document_id: str
    project_name: str
    content: str
    metadata: Dict[str, Any]
