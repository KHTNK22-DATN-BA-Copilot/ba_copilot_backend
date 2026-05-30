# routers/document_format.py

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.core.rbac import (
    Permission,
    ProjectAccessContext,
    require_permission,
)

from app.schemas.document_format import (
    ProjectDocumentFormatResponse,
    ProjectDocumentFormatListResponse,
    UploadCustomDocumentFormatResponse,
    UpdateDocumentFormatContentRequest,
    DocumentFormatContentResponse,
)

from app.services.document_format_service import (
    resolve_active_format,
    upload_custom_document_format,
    update_custom_format_content,
    delete_custom_format,
    activate_custom_format,
)

from app.models.custom_document_format import CustomDocumentFormat

router = APIRouter()


def require_owner(access: ProjectAccessContext):
    if access.role.name != "Owner":
        raise HTTPException(
            status_code=403,
            detail="Only project owner can manage document formats",
        )


@router.get(
    "/projects/{project_id}/document-formats",
    response_model=ProjectDocumentFormatListResponse,
)
async def get_all_formats(
    project_id: int,
    access: ProjectAccessContext = Depends(
        require_permission(Permission.FORMAT_READ)
    ),
    db: Session = Depends(get_db),
):
    formats = (
        db.query(CustomDocumentFormat)
        .filter(CustomDocumentFormat.project_id == project_id)
        .order_by(CustomDocumentFormat.created_at.desc())
        .all()
    )

    result = []

    for item in formats:
        result.append(
            ProjectDocumentFormatResponse(
                id=item.id,
                name=item.name,
                document_type=item.document_type,
                extension=item.extension,
                content=item.content,
                source="custom",
                is_activated=item.is_activated,
            )
        )

    return {"formats": result}


@router.get(
    "/projects/{project_id}/document-formats/types/{document_type}",
    response_model=ProjectDocumentFormatListResponse,
)
async def get_formats_by_type(
    project_id: int,
    document_type: str,
    access: ProjectAccessContext = Depends(
        require_permission(Permission.FORMAT_READ)
    ),
    db: Session = Depends(get_db),
):
    formats = (
        db.query(CustomDocumentFormat)
        .filter(
            CustomDocumentFormat.project_id == project_id,
            CustomDocumentFormat.document_type == document_type,
        )
        .order_by(CustomDocumentFormat.created_at.desc())
        .all()
    )

    result = []

    for item in formats:
        result.append(
            ProjectDocumentFormatResponse(
                id=item.id,
                name=item.name,
                document_type=item.document_type,
                extension=item.extension,
                content=item.content,
                source="custom",
                is_activated=item.is_activated,
            )
        )

    return {"formats": result}


@router.get(
    "/projects/{project_id}/document-formats/active/{document_type}",
    response_model=DocumentFormatContentResponse,
)
async def get_active_format(
    project_id: int,
    document_type: str,
    access: ProjectAccessContext = Depends(
        require_permission(Permission.FORMAT_READ)
    ),
    db: AsyncSession = Depends(get_db),
):
    result = await resolve_active_format(
        db=db,
        project_id=project_id,
        document_type=document_type,
    )

    return result


@router.post(
    "/projects/{project_id}/document-formats/upload",
    response_model=UploadCustomDocumentFormatResponse,
)
async def upload_format(
    project_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    access: ProjectAccessContext = Depends(
        require_permission(Permission.FORMAT_WRITE)
    ),
    db: Session = Depends(get_db),
):
    require_owner(access)

    new_format = await upload_custom_document_format(
        db=db,
        project_id=project_id,
        document_type=document_type,
        file=file,
    )

    db.commit()
    db.refresh(new_format)

    return new_format


@router.put(
    "/projects/{project_id}/document-formats/{format_id}",
    response_model=UploadCustomDocumentFormatResponse,
)
async def update_format(
    project_id: int,
    format_id: int,
    req: UpdateDocumentFormatContentRequest,
    access: ProjectAccessContext = Depends(
        require_permission(Permission.FORMAT_WRITE)
    ),
    db: Session = Depends(get_db),
):
    require_owner(access)

    updated_format = await update_custom_format_content(
        db=db,
        project_id=project_id,
        format_id=format_id,
        content=req.content,
    )

    db.commit()
    db.refresh(updated_format)

    return updated_format


@router.patch("/projects/{project_id}/document-formats/{format_id}/activate")
async def activate_format(
    project_id: int,
    format_id: int,
    access: ProjectAccessContext = Depends(
        require_permission(Permission.FORMAT_WRITE)
    ),
    db: Session = Depends(get_db),
):
    require_owner(access)

    activated_format = await activate_custom_format(
        db=db,
        project_id=project_id,
        format_id=format_id,
    )

    db.commit()
    db.refresh(activated_format)

    return {
        "message": "Format activated successfully",
        "id": activated_format.id,
    }


@router.delete("/projects/{project_id}/document-formats/{format_id}")
async def remove_format(
    project_id: int,
    format_id: int,
    access: ProjectAccessContext = Depends(
        require_permission(Permission.FORMAT_WRITE)
    ),
    db: Session = Depends(get_db),
):
    require_owner(access)

    await delete_custom_format(
        db=db,
        project_id=project_id,
        format_id=format_id,
    )

    db.commit()

    return {
        "message": "Custom format deleted successfully"
    }

