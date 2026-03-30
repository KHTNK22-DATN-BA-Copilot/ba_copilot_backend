from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.schemas.base_response import BaseResponseModel


class PlanningGenerateResponse(BaseResponseModel):
    document_id: str
    user_id: Optional[str]
    generated_at: datetime
    input_description: str
    document: str
    doc_type: str
    status: str
    recommend_documents: Optional[List[str]] = None
    file_size_kb: float = Field(..., description="File size")


class GetPlanningResponse(BaseResponseModel):
    document_id: str
    project_name: str
    content: str
    doc_type: str
    status: str
    updated_at: datetime
    file_size_kb: float


class UpdatePlanningResponse(BaseResponseModel):
    document_id: str
    project_name: str
    content: str
    updated_at: datetime
    file_size_kb: float


class PlanningListResponse(BaseResponseModel):
    documents: List[GetPlanningResponse]
