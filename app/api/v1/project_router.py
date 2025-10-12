from fastapi import APIRouter, Depends, HTTPException
from app.schemas.project import (
    ProjectCreate,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectUpdate,
    ProjectUpdateResponse,
    DeleteProjectResponse,
)
from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.project import Project
from sqlalchemy.orm import Session
from datetime import datetime, timezone

router = APIRouter()


@router.post("/", response_model=ProjectDetailResponse)
async def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_project = Project(
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        status=body.status if hasattr(body, "status") else "active",
        settings=body.settings if hasattr(body, "settings") else {},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


@router.get("/", response_model=ProjectListResponse)
async def get_projects(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    projects = (
        db.query(Project)
        .filter(Project.user_id == current_user.id, Project.status != "deleted")
        .all()
    )
    return {
        "projects": projects,
    }


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id,
            Project.status != "deleted",
        )
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectUpdateResponse)
async def update_project(
    project_id: int,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.name = body.name
    project.description = body.description
    project.status = body.status
    project.settings = body.settings
    project.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)
    return {"id": project.id, "message": "Project updated successfully"}


# Soft delete project
@router.delete("/{project_id}", response_model=DeleteProjectResponse)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.user_id == current_user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = "deleted"
    project.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)
    return {"message": "Project deleted successfully"}
