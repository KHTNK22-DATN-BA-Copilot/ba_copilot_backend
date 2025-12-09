from app.models.file import File
from app.schemas.file import GetFileResponse
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc
from app.schemas.project import (
    GetProjectChildResponse,
    GetProjectTreeResponse,
    ProjectCreate,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectUpdate,
    ProjectUpdateResponse,
    DeleteProjectResponse,
)
from app.schemas.folder import CreateFolderResponse, CreateFolderRequest, FolderNode
from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.folder import Folder
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
    project.team_size = body.team_size
    project.project_priority = body.project_priority
    project.settings = body.settings
    project.due_date = body.due_date
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


# Create new folder, support sub folders and root folder (parent_id is null)
@router.post("/{project_id}/folders", response_model=CreateFolderResponse)
async def create_folder(
    project_id: int,
    body: CreateFolderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if project exists
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

    if body.parent_id:
        # Check if parent folder exists
        parent_folder = (
            db.query(Folder)
            .filter(
                Folder.id == body.parent_id,
                Folder.project_id == project_id,
                Folder.is_deleted == False,
            )
            .first()
        )
        if not parent_folder:
            raise HTTPException(status_code=404, detail="Parent folder not found")

    # Check if folder name is already exists
    filters = [
        Folder.project_id == project_id,
        Folder.name == body.name,
        Folder.is_deleted == False,
    ]
    if body.parent_id is not None:
        filters.append(Folder.parent_id == body.parent_id)
    else:
        filters.append(Folder.parent_id.is_(None))
    folder = db.query(Folder).filter(*filters).first()
    if folder:
        raise HTTPException(
            status_code=400, detail=f"Folder name {body.name} already exists"
        )
    new_folder = Folder(
        project_id=project_id,
        name=body.name,
        parent_id=body.parent_id,
        created_by=current_user.id,
    )
    db.add(new_folder)
    db.commit()
    db.refresh(new_folder)
    return new_folder


# Get project direct child (folder + file)
@router.get("/{project_id}/contents", response_model=GetProjectChildResponse)
async def get_root_contents(
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

    # Get direct child folders (folder_id, name, parent_id)
    folders = (
        db.query(Folder)
        .filter(
            Folder.project_id == project_id,
            Folder.parent_id.is_(None),
            Folder.is_deleted == False,
        )
        .all()
    )
    # Get direct files
    files = (
        db.query(File)
        .filter(
            File.project_id == project_id,
            File.folder_id.is_(None),
            File.status != "deleted",
        )
        .all()
    )

    return {
        "folders": [
            {
                "id": folder.id,
                "name": folder.name,
                "project_id": folder.project_id,
                "parent_id": folder.parent_id,
                "created_by": folder.created_by,
                "created_at": folder.created_at,
                "updated_at": folder.updated_at,
            }
            for folder in folders
        ],
        "files": [
            {
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
                "file_metadata": file.file_metadata,
                "status": file.status,
                "created_at": file.created_at,
                "updated_at": file.updated_at,
            }
            for file in files
        ],
    }


# Get project full tree
@router.get("/{project_id}/tree", response_model=GetProjectTreeResponse)
async def get_project_tree(
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

    folders = (
        db.query(Folder)
        .filter(Folder.project_id == project_id, Folder.is_deleted == False)
        .all()
    )
    files = (
        db.query(File)
        .filter(File.project_id == project_id, File.status != "deleted")
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
            extension=file.extension,  # Note: mapped from DB column 'extend' to Pydantic 'extension'
            storage_path=file.storage_path,
            content=file.content,
            file_category=file.file_category,
            file_type=file.file_type,
            # Use 'metadata' from DB, default to {} if None
            file_metadata=file.file_metadata if file.file_metadata else {}, 
            status=file.status,
            created_at=file.created_at,
            updated_at=file.updated_at
        )
        if not file.folder_id: 
            root_files.append(file_node)
        if file.folder_id in folder_map:
            folder_map[file.folder_id].files.append(file_node)
        
    for folder in folders:
        current_node = folder_map[folder.id]
        if not folder.parent_id:
            root_folders.append(current_node)
        elif folder.parent_id in folder_map:
            folder_map[folder.parent_id].folders.append(current_node)
        else:
            pass
    return {
        "project_id": project_id,
        "tree": {"folders": root_folders, "files": root_files},
    }
