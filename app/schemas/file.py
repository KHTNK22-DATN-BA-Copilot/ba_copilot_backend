from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class GetFileResponse(BaseModel):
    id: UUID = Field(..., description="Unique identifier of the file")
    project_id: int = Field(..., description="ID of the associated project")
    folder_id: Optional[int] = Field(..., description="ID of the folder containing the file")
    created_by: int = Field(..., description="ID of the user who created the file")
    updated_by: int = Field(..., description="ID of the user who last updated the file")
    name: str = Field(..., description="Display name or filename")
    extension: Optional[str] = Field(None, description="File extension, e.g., .md, .pdf")
    storage_path: Optional[str] = Field(None, description="Path in S3/Storage backend")
    content: Optional[str] = Field(None, description="Content of the file, if text or markdown")
    file_category: str = Field(..., description="Categorizing the file source (ai gen, user upload, etc.)")
    file_type: str = Field(..., description="Technical file type (srs, pdf, wireframe, markdown)")
    file_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="File metadata (AI params, file metadata, etc.)")
    status: str = Field(..., description="File status (active, etc.)")
    created_at: datetime = Field(..., description="Timestamp when the file was created")
    updated_at: datetime = Field(..., description="Timestamp when the file was last updated")
    

