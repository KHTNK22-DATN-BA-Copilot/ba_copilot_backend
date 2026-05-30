# schemas/document_format.py

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class DefaultDocumentFormatResponse(BaseModel):
    id: int
    document_type: str
    extension: str
    content: str
    description: Optional[str]


class ProjectDocumentFormatResponse(BaseModel):
    id: int
    name: str
    document_type: str
    extension: str
    content: str
    source: str
    is_activated: bool


class ProjectDocumentFormatListResponse(BaseModel):
    formats: List[ProjectDocumentFormatResponse]


class DocumentFormatContentResponse(BaseModel):
    document_type: str
    extension: str
    source: str
    content: str


class UploadCustomDocumentFormatResponse(BaseModel):
    id: int
    project_id: int
    document_type: str
    extension: str
    content: str
    is_activated: bool
    created_at: datetime


class UpdateDocumentFormatContentRequest(BaseModel):
    content: str
