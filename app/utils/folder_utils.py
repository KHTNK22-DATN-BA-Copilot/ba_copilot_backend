from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.folder import (
    CreateFolderRequest,
    CreateFolderResult,
    CreateFolderResponse,
)
from app.models.project import Project
from app.models.folder import Folder


async def create_default_folder(
    project_id: int,
    body: CreateFolderRequest,
    user_id: int,
    db: Session,
) -> CreateFolderResult:
    try:
        project = (
            db.query(Project)
            .filter(
                Project.id == project_id,
                Project.user_id == user_id,
                Project.status != "deleted",
            )
            .first()
        )

        if not project:
            return CreateFolderResult(error="Project not found")

        filters = [
            Folder.project_id == project_id,
            Folder.name == body.name,
            Folder.is_deleted == False,
        ]

        if body.parent_id is not None:
            filters.append(Folder.parent_id == body.parent_id)
        else:
            filters.append(Folder.parent_id.is_(None))

        existing = db.query(Folder).filter(*filters).first()


        if existing:
            return CreateFolderResult(
                folder=CreateFolderResponse.model_validate(existing)
            )

        new_folder = Folder(
            project_id=project_id,
            name=body.name,
            parent_id=body.parent_id,
            created_by=user_id,
        )

        db.add(new_folder)
        db.commit()
        db.refresh(new_folder)

        return CreateFolderResult(
            folder=CreateFolderResponse.model_validate(new_folder)
        )

    except SQLAlchemyError as e:
        db.rollback()
        return CreateFolderResult(
            error="Database error",
            detail=str(e),
        )

    except Exception as e:
        db.rollback()
        return CreateFolderResult(
            error="Unknown error",
            detail=str(e),
        )
