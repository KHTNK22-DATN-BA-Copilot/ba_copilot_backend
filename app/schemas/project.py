from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from datetime import datetime, timedelta,timezone
class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

class ProjectPriority(str,Enum):
    LOW="low"
    MEDIUM="medium"
    HIGH="high"
    CRITICAL = "critical"
class ProjectCreate(BaseModel):
    name: str = Field(..., description="The name of the project")
    description: Optional[str] = Field(None, description="Project description")
    status: Optional[ProjectStatus] = Field(ProjectStatus.ACTIVE, description="Project status")
    team_size: Optional[int]=Field(1,description="Project team size")
    due_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30),
                               description="Due date (default: 30 days from now)")
    project_priority:Optional[ProjectPriority]=Field(ProjectPriority.LOW,description="Project priority")

class ProjectUpdate(BaseModel):
    name: str = Field(..., description="Updated project name")
    description: str = Field(..., description="Updated description")
    status: ProjectStatus = Field(..., description="Updated project status")
    due_date:datetime=Field(...,description="Project due date")
    project_priority:ProjectPriority=Field(...,description="Project priority")
    team_size: int=Field(...,description="Project team size")
    settings: dict = Field(..., description="Project settings")

class ProjectResponse(BaseModel):
    id: int = Field(..., description="Project unique ID")
    user_id: int = Field(..., description="ID of the user owning the project")
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    status: ProjectStatus = Field(..., description="Project status")
    due_date: datetime = Field(..., description="Project due date")
    project_priority: ProjectPriority = Field(..., description="Project priority")
    team_size: int = Field(..., description="Project team size")
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
