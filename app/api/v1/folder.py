from app.models.file import Files
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.folder import Folder
from app.schemas.folder import (
    DeleteFolderResponse,
    GetFolderChildrenReponse,
    UpdateFolderResponse,
    UpdateFolderRequest,
)
from sqlalchemy.orm import Session
from datetime import datetime, timezone

router = APIRouter()


# helper: cycle detection
def is_ancestor(db: Session, ancestor_id: int, target_id: int) -> bool:
    query = """
    WITH RECURSIVE ancestors AS (
        SELECT id, parent_id FROM folders WHERE id = :target_id
        UNION ALL
        SELECT f.id, f.parent_id 
        FROM folders f
        INNER JOIN ancestors a ON f.id = a.parent_id
    )
    SELECT 1 FROM ancestors WHERE id = :ancestor_id LIMIT 1;
    """
    result = db.execute(
        text(query), {"ancestor_id": ancestor_id, "target_id": target_id}
    )
    return result.scalar() is not None


# change folder name, or move folder to another folder
@router.patch("/{folder_id}", response_model=UpdateFolderResponse)
async def update_folder(
    folder_id: int,
    body: UpdateFolderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if folder exists
    folder = (
        db.query(Folder)
        .filter(Folder.id == folder_id, Folder.is_deleted == False)
        .first()
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Moving folder to another folder
    if body.parent_id:
        # Check if new parent folder exists
        parent_folder = (
            db.query(Folder)
            .filter(
                Folder.id == body.parent_id,
                Folder.project_id == folder.project_id,
                Folder.is_deleted == False,
            )
            .first()
        )
        if not parent_folder:
            raise HTTPException(status_code=404, detail="Parent folder not found")
        # Check if moving to itself or ancestor
        if is_ancestor(db, folder_id, body.parent_id):
            raise HTTPException(
                status_code=400, detail="Cannot move to itself or ancestor"
            )

    # Update folder name
    target_parent_id = body.parent_id if body.parent_id else folder.parent_id
    target_folder_name = body.name if body.name else folder.name

    duplicated_folder = (
        db.query(Folder)
        .filter(
            Folder.project_id == folder.project_id,
            Folder.name == target_folder_name,
            Folder.parent_id == target_parent_id,
            Folder.is_deleted == False,
            Folder.id != folder_id,
        )
        .first()
    )
    if duplicated_folder:
        raise HTTPException(
            status_code=400, detail=f"Folder name {target_folder_name} already exists"
        )
    folder.name = target_folder_name
    folder.parent_id = target_parent_id
    folder.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(folder)
    return folder


# Soft delete folder
@router.delete("/{folder_id}", response_model=DeleteFolderResponse)
async def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    folder = (
        db.query(Folder)
        .filter(Folder.id == folder_id, Folder.is_deleted == False)
        .first()
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    folder.is_deleted = True
    folder.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(folder)
    return folder


# Get folder's DIRECT children, include sub folders and files
@router.get("/{folder_id}/contents", response_model=GetFolderChildrenReponse)
async def get_folder_children(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    folder = (
        db.query(Folder)
        .filter(Folder.id == folder_id, Folder.is_deleted == False)
        .first()
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    folders = (
        db.query(Folder)
        .filter(Folder.parent_id == folder_id, Folder.is_deleted == False)
        .all()
    )

    files = (
        db.query(Files)
        .filter(Files.folder_id == folder_id, Files.status != "deleted")
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
