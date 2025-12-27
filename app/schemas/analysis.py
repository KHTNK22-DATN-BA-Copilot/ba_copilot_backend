from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AnalysisGenerateResponse(BaseModel):
    document_id: str
    user_id: Optional[str]
    generated_at: str
    input_description: str
    document: str
    doc_type: str
    status: str


class GetAnalysisResponse(BaseModel):
    document_id: str
    project_name: str
    content: str
    doc_type: str
    status: str
    updated_at: datetime


class UpdateAnalysisResponse(BaseModel):
    document_id: str
    project_name: str
    content: str
    status: str
    updated_at: datetime


class AnalysisListResponse(BaseModel):
    documents: List[GetAnalysisResponse]
