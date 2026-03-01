from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class PlanningGenerateResponse(BaseModel):
    document_id: str
    user_id: Optional[str]
    generated_at: str
    input_description: str
    document: str
    doc_type: str
    status: str
    recommend_documents: Optional[List[str]] = None
    file_size_kb: float = Field(..., description="File size")


class GetPlanningResponse(BaseModel):
    document_id: str
    project_name: str
    content: str
    doc_type: str
    status: str
    updated_at: datetime
    file_size_kb: float


class UpdatePlanningResponse(BaseModel):
    document_id: str
    project_name: str
    content: str
    status: str
    updated_at: datetime
    file_size_kb: float


class PlanningListResponse(BaseModel):
    documents: List[GetPlanningResponse]
