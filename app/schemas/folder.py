from __future__ import annotations
from app.schemas.file import GetFileResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class CreateFolderRequest(BaseModel):
    name: str = Field(..., description="The name of the folder")
    parent_id: Optional[int] = Field(None, description="The parent folder id")

class CreateFolderResponse(BaseModel):
    id: int = Field(..., description="The id of the folder")
    project_id: int = Field(..., description="The project id")
    parent_id: Optional[int] = Field(None, description="The parent folder id")
    name: str = Field(..., description="The name of the folder")
    is_deleted: bool = Field(..., description="Whether the folder is deleted")
    created_by: int = Field(..., description="The user id who created the folder")
    created_at: datetime = Field(..., description="The creation time of the folder")
    updated_at: datetime = Field(..., description="The update time of the folder")
    model_config = {"from_attributes": True}


class CreateFolderResult(BaseModel):
    folder: Optional[CreateFolderResponse] = None
    error: Optional[str] = None
    detail: Optional[str] = None


class UpdateFolderRequest(BaseModel):
    name: Optional[str] = Field(None, description="The name of the folder")
    parent_id: Optional[int] = Field(None, description="The parent folder id")

class UpdateFolderResponse(BaseModel):
    id: int = Field(..., description="The id of the folder")
    project_id: int = Field(..., description="The project id")
    parent_id: Optional[int] = Field(None, description="The parent folder id")
    name: str = Field(..., description="The name of the folder")
    is_deleted: bool = Field(..., description="Whether the folder is deleted")
    created_by: int = Field(..., description="The user id who created the folder")
    created_at: datetime = Field(..., description="The creation time of the folder")
    updated_at: datetime = Field(..., description="The update time of the folder")

class DeleteFolderResponse(BaseModel): 
    id: int = Field(..., description="The id of the folder")
    project_id: int = Field(..., description="The project id")
    parent_id: Optional[int] = Field(None, description="The parent folder id")
    name: str = Field(..., description="The name of the folder")
    is_deleted: bool = Field(..., description="Whether the folder is deleted")
    created_by: int = Field(..., description="The user id who created the folder")
    created_at: datetime = Field(..., description="The creation time of the folder")
    updated_at: datetime = Field(..., description="The update time of the folder")

class GetFolderResponse(BaseModel):
    id: int = Field(..., description="The id of the folder")
    name: str = Field(..., description="The name of the folder")
    project_id: int = Field(..., description="The project id")
    parent_id: Optional[int] = Field(None, description="The parent folder id")
    created_by: int = Field(..., description="The user id who created the folder")
    created_at: datetime = Field(..., description="The creation time of the folder")
    updated_at: datetime = Field(..., description="The update time of the folder")

class GetFolderChildrenReponse(BaseModel): 
    folders: List[GetFolderResponse]
    files: List[GetFileResponse]

class FolderNode(GetFolderResponse): 
    folders: List[FolderNode] = []
    files: List[GetFileResponse] = []
