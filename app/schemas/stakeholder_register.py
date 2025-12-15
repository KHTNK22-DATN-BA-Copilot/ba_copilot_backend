from pydantic import BaseModel, Field
from typing import Annotated, Dict, Any, Optional, List
from datetime import datetime


class StakeholderGenerateResponse(BaseModel):
    """Response schema for Stakeholder Register generation."""

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
        ..., description="Generated Stakeholder Register document in Markdown format"
    )
    status: str = Field(..., description="Generation status")


class GetStakeholderResponse(BaseModel):
    document_id: str
    project_name: str
    content: str
    status: str
    updated_at: datetime


class UpdateStakeholderResponse(BaseModel):
    document_id: str
    project_name: str
    content: str
    status: str
    updated_at: datetime


class StakeholderListResponse(BaseModel):
    documents: List[GetStakeholderResponse] = Field(
        ..., description="List of stakeholder register documents"
    )


class StakeholderDocument(BaseModel):
    """Stakeholder Register document model."""

    document_id: str
    project_name: str
    content: str
    metadata: Dict[str, Any]
