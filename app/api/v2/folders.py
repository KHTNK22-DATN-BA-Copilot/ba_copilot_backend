from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import Permission, ProjectAccessContext, require_permission
from app.models.file import Files
from app.models.folder import Folder
from app.schemas.folder import CreateFolderRequest, UpdateFolderRequest

router = APIRouter()


def serialize_folder(folder: Folder):
    return {
        "id": folder.id,
        "project_id": folder.project_id,
        "parent_id": folder.parent_id,
        "name": folder.name,
        "is_deleted": folder.is_deleted,
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


@router.post("/{project_id}/folders")
async def create_folder(
    project_id: int,
    body: CreateFolderRequest,
    access: ProjectAccessContext = Depends(require_permission(Permission.FOLDER_WRITE)),
    db: Session = Depends(get_db),
):
    if body.parent_id:
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

    duplicate_query = db.query(Folder).filter(
        Folder.project_id == project_id,
        Folder.name == body.name,
        Folder.is_deleted == False,
    )

    if body.parent_id is None:
        duplicate_query = duplicate_query.filter(Folder.parent_id.is_(None))
    else:
        duplicate_query = duplicate_query.filter(Folder.parent_id == body.parent_id)

    if duplicate_query.first():
        raise HTTPException(status_code=400, detail="Folder name already exists")

    folder = Folder(
        project_id=project_id,
        name=body.name,
        parent_id=body.parent_id,
        created_by=access.user.id,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)

    return serialize_folder(folder)


@router.get("/{project_id}/folders/{folder_id}/contents")
async def get_folder_contents(
    project_id: int,
    folder_id: int,
    access: ProjectAccessContext = Depends(require_permission(Permission.FOLDER_READ)),
    db: Session = Depends(get_db),
):
    folder = (
        db.query(Folder)
        .filter(
            Folder.id == folder_id,
            Folder.project_id == project_id,
            Folder.is_deleted == False,
        )
        .first()
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    folders = (
        db.query(Folder)
        .filter(
            Folder.parent_id == folder_id,
            Folder.project_id == project_id,
            Folder.is_deleted == False,
        )
        .all()
    )

    files = (
        db.query(Files)
        .filter(
            Files.folder_id == folder_id,
            Files.project_id == project_id,
            Files.status != "deleted",
        )
        .all()
    )

    return {
        "folders": [serialize_folder(child) for child in folders],
        "files": [serialize_file(file) for file in files],
    }


@router.patch("/{project_id}/folders/{folder_id}")
async def update_folder(
    project_id: int,
    folder_id: int,
    body: UpdateFolderRequest,
    access: ProjectAccessContext = Depends(require_permission(Permission.FOLDER_WRITE)),
    db: Session = Depends(get_db),
):
    folder = (
        db.query(Folder)
        .filter(
            Folder.id == folder_id,
            Folder.project_id == project_id,
            Folder.is_deleted == False,
        )
        .first()
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    target_parent_id = (
        body.parent_id if body.parent_id is not None else folder.parent_id
    )
    target_name = body.name if body.name else folder.name

    if target_parent_id:
        parent_folder = (
            db.query(Folder)
            .filter(
                Folder.id == target_parent_id,
                Folder.project_id == project_id,
                Folder.is_deleted == False,
            )
            .first()
        )
        if not parent_folder:
            raise HTTPException(status_code=404, detail="Parent folder not found")
        if target_parent_id == folder_id or is_ancestor(
            db, folder_id, target_parent_id
        ):
            raise HTTPException(
                status_code=400,
                detail="Cannot move folder into itself or descendant",
            )

    duplicate = (
        db.query(Folder)
        .filter(
            Folder.project_id == project_id,
            Folder.parent_id == target_parent_id,
            Folder.name == target_name,
            Folder.is_deleted == False,
            Folder.id != folder_id,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="Folder name already exists")

    folder.name = target_name
    folder.parent_id = target_parent_id
    folder.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(folder)

    return serialize_folder(folder)


@router.delete("/{project_id}/folders/{folder_id}")
async def delete_folder(
    project_id: int,
    folder_id: int,
    access: ProjectAccessContext = Depends(
        require_permission(Permission.FOLDER_DELETE)
    ),
    db: Session = Depends(get_db),
):
    folder = (
        db.query(Folder)
        .filter(
            Folder.id == folder_id,
            Folder.project_id == project_id,
            Folder.is_deleted == False,
        )
        .first()
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    folder.is_deleted = True
    folder.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(folder)

    return serialize_folder(folder)
