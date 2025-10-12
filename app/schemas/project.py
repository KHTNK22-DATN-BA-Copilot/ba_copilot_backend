from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime
class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

class ProjectCreate(BaseModel):
    name: str = Field(..., description="The name of the project")
    description: Optional[str] = Field(None, description="Project description")
    status: Optional[ProjectStatus] = Field(ProjectStatus.ACTIVE, description="Project status")

class ProjectUpdate(BaseModel):
    name: str = Field(..., description="Updated project name")
    description: str = Field(..., description="Updated description")
    status: ProjectStatus = Field(..., description="Updated project status")
    settings: dict = Field(..., description="Project settings")

class ProjectResponse(BaseModel):
    id: int = Field(..., description="Project unique ID")
    user_id: int = Field(..., description="ID of the user owning the project")
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    status: ProjectStatus = Field(..., description="Project status")
    settings: Optional[dict] = Field(None, description="Project settings")

class ProjectUpdateResponse(BaseModel):
    id: int = Field(..., description="Project unique ID")
    message: str = Field(..., description="Status message confirming update")

class ProjectDetailResponse(ProjectResponse):
    created_at: Optional[datetime] = Field(None, description="Timestamp when the project was created")
    updated_at: Optional[datetime] = Field(None, description="Timestamp when the project was last updated")

class ProjectListResponse(BaseModel):
    projects: List[ProjectDetailResponse] = Field(..., description="List of user's projects")

class DeleteProjectResponse(BaseModel):
    message: str = Field(..., description="Status message confirming deletion")
