from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.core.rbac import Permission, ProjectAccessContext, require_permission
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User
from app.models.file import Files
from app.models.folder import Folder
from app.schemas.file import GetFileResponse
from app.schemas.folder import FolderNode
from app.schemas.project import (
    GetProjectChildResponse,
    GetProjectTreeResponse,
    ProjectCreate,
    ProjectUpdate,
)

router = APIRouter()


def serialize_project(project: Project, my_role: str | None = None):
    data = {
        "id": project.id,
        "user_id": project.user_id,
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "project_priority": project.project_priority,
        "team_size": project.team_size,
        "settings": project.settings,
        "due_date": project.due_date,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }
    if my_role is not None:
        data["my_role"] = my_role
    return data


def serialize_folder(folder: Folder):
    return {
        "id": folder.id,
        "name": folder.name,
        "project_id": folder.project_id,
        "parent_id": folder.parent_id,
        "created_by": folder.created_by,
        "created_at": folder.created_at,
        "updated_at": folder.updated_at,
    }


def serialize_file(file: Files):
    return {
        "id": file.id,
        "project_id": file.project_id,
        "folder_id": file.folder_id,
        "created_by": file.created_by,
        "updated_by": file.updated_by,
        "name": file.name,
        "extension": file.extension,
        "storage_path": file.storage_path,
        "content": file.content,
        "file_category": file.file_category,
        "file_type": file.file_type,
        "file_size": file.file_size,
        "file_metadata": file.file_metadata or {},
        "status": file.status,
        "created_at": file.created_at,
        "updated_at": file.updated_at,
    }


@router.post("/")
async def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    owner_role = db.query(Role).filter(Role.name == "Owner").first()
    if not owner_role:
        raise HTTPException(status_code=500, detail="Owner role is not configured")

    project = Project(
        user_id=current_user.id,
        name=body.name,
        description=body.description or "",
        status=body.status,
        team_size=body.team_size or 1,
        due_date=body.due_date,
        project_priority=body.project_priority,
        settings=getattr(body, "settings", {}) or {},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    try:
        db.add(project)
        db.flush()
        db.add(
            ProjectMember(
                project_id=project.id,
                user_id=current_user.id,
                role_id=owner_role.id,
            )
        )
        db.commit()
        db.refresh(project)
    except Exception:
        db.rollback()
        raise

    return serialize_project(project, my_role=owner_role.name)


@router.get("/")
async def list_projects(
    name: str | None = Query(None),
    sort_field: str = Query("created_at", pattern="^(name|created_at|updated_at)$"),
    sort: str = Query("DESC", pattern="^(ASC|DESC)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order_func = asc if sort.upper() == "ASC" else desc
    sort_map = {
        "name": Project.name,
        "created_at": Project.created_at,
        "updated_at": Project.updated_at,
    }

    query = (
        db.query(Project, Role.name.label("my_role"))
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .join(Role, Role.id == ProjectMember.role_id)
        .filter(
            ProjectMember.user_id == current_user.id,
            Project.status != "deleted",
        )
    )

    if name:
        query = query.filter(Project.name.ilike(f"%{name}%"))

    rows = query.order_by(order_func(sort_map[sort_field])).all()
    return {
        "projects": [
            serialize_project(project, my_role=my_role) for project, my_role in rows
        ]
    }


@router.get("/{project_id}")
async def get_project(
    project_id: int,
    access: ProjectAccessContext = Depends(require_permission(Permission.PROJECT_READ)),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.status != "deleted")
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return serialize_project(project, my_role=access.role.name)


@router.get("/{project_id}/contents", response_model=GetProjectChildResponse)
async def get_root_contents(
    project_id: int,
    access: ProjectAccessContext = Depends(require_permission(Permission.PROJECT_READ)),
    db: Session = Depends(get_db),
):
    folders = (
        db.query(Folder)
        .filter(
            Folder.project_id == project_id,
            Folder.parent_id.is_(None),
            Folder.is_deleted == False,
        )
        .all()
    )
    files = (
        db.query(Files)
        .filter(
            Files.project_id == project_id,
            Files.folder_id.is_(None),
            Files.status != "deleted",
        )
        .all()
    )

    return {
        "folders": [serialize_folder(folder) for folder in folders],
        "files": [serialize_file(file) for file in files],
    }


@router.get("/{project_id}/tree", response_model=GetProjectTreeResponse)
async def get_project_tree(
    project_id: int,
    access: ProjectAccessContext = Depends(require_permission(Permission.PROJECT_READ)),
    db: Session = Depends(get_db),
):
    folders = (
        db.query(Folder)
        .filter(Folder.project_id == project_id, Folder.is_deleted == False)
        .all()
    )
    files = (
        db.query(Files)
        .filter(Files.project_id == project_id, Files.status != "deleted")
        .all()
    )

    root_files = []
    root_folders = []
    folder_map = {}

    for folder in folders:
        folder_map[folder.id] = FolderNode(
            id=folder.id,
            name=folder.name,
            project_id=folder.project_id,
            parent_id=folder.parent_id,
            created_by=folder.created_by,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            folders=[],
            files=[],
        )

    for file in files:
        file_node = GetFileResponse(
            id=file.id,
            project_id=file.project_id,
            folder_id=file.folder_id,
            created_by=file.created_by,
            updated_by=file.updated_by,
            name=file.name,
            extension=file.extension,
            storage_path=file.storage_path,
            content=file.content,
            file_category=file.file_category,
            file_type=file.file_type,
            file_size=file.file_size,
            file_metadata=file.file_metadata or {},
            status=file.status,
            created_at=file.created_at,
            updated_at=file.updated_at,
        )
        if not file.folder_id:
            root_files.append(file_node)
        elif file.folder_id in folder_map:
            folder_map[file.folder_id].files.append(file_node)

    for folder in folders:
        current_node = folder_map[folder.id]
        if not folder.parent_id:
            root_folders.append(current_node)
        elif folder.parent_id in folder_map:
            folder_map[folder.parent_id].folders.append(current_node)

    return {
        "project_id": project_id,
        "tree": {"folders": root_folders, "files": root_files},
    }


@router.patch("/{project_id}")
async def update_project(
    project_id: int,
    body: ProjectUpdate,
    access: ProjectAccessContext = Depends(
        require_permission(Permission.PROJECT_WRITE)
    ),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.status != "deleted")
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.name = body.name
    project.description = body.description
    project.status = body.status
    project.team_size = body.team_size
    project.project_priority = body.project_priority
    project.settings = body.settings
    project.due_date = body.due_date
    project.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(project)
    return {"id": project.id, "message": "Project updated successfully"}


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    access: ProjectAccessContext = Depends(
        require_permission(Permission.PROJECT_DELETE)
    ),
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.status != "deleted")
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = "deleted"
    project.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Project deleted successfully"}
