from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc
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
from datetime import datetime, timezone, timedelta

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
        team_size=body.team_size if hasattr(body, "team_size") else 1,
        due_date=(
            body.due_date
            if hasattr(body, "due_date")
            else datetime.now(timezone.utc) + timedelta(days=30)
        ),
        project_priority=(
            body.project_priority if hasattr(body, "project_priority") else "low"
        ),
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
    name: str | None = Query(None),
    created_at: str | None = Query(None),
    updated_at: str | None = Query(None),
    sort_field: str = Query("created_at", regex="^(name|created_at|updated_at)$"),
    sort: str = Query("DESC", regex="^(ASC|DESC)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    order_func = asc if sort.upper() == "ASC" else desc


    query = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.status != "deleted",
    )


    if name:
        query = query.filter(Project.name.ilike(f"%{name}%"))
    if created_at:
        query = query.filter(Project.created_at == created_at)
    if updated_at:
        query = query.filter(Project.updated_at == updated_at)

    sort_map = {
        "name": Project.name,
        "created_at": Project.created_at,
        "updated_at": Project.updated_at,
    }

    query = query.order_by(order_func(sort_map[sort_field]))

    return {"projects": query.all()}


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
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id,
            Project.status != "deleted",
        )
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.name = body.name
    project.description = body.description
    project.status = body.status
    project.team_size=body.team_size
    project.project_priority=body.project_priority
    project.settings = body.settings
    project.due_date=body.due_date
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
        .filter(
            Project.id == project_id,
            Project.user_id == current_user.id,
            Project.status != "deleted",
        )
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = "deleted"
    project.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)
    return {"message": "Project deleted successfully"}
