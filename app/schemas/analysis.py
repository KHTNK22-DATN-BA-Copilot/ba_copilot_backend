
from typing import Optional, List
from datetime import datetime
from app.schemas.base_response import BaseResponseModel


class AnalysisGenerateResponse(BaseResponseModel):
    document_id: str
    user_id: Optional[str]
    generated_at: datetime
    input_description: str
    document: str
    doc_type: str
    status: str
    recommend_documents: Optional[List[str]] = None
    file_size_kb:float


class GetAnalysisResponse(BaseResponseModel):
    document_id: str
    project_name: str
    content: str
    doc_type: str
    status: str
    updated_at: datetime
    file_size_kb:float


class UpdateAnalysisResponse(BaseResponseModel):
    document_id: str
    project_name: str
    content: str
    updated_at: datetime
    file_size_kb: float


class AnalysisListResponse(BaseResponseModel):
    documents: List[GetAnalysisResponse]
