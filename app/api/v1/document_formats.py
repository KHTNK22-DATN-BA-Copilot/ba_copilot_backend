# routers/document_format.py
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Query

from sqlalchemy.orm import Session

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
    get_project_document_formats,
)


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
async def get_formats(
    project_id: int,
    document_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    access: ProjectAccessContext = Depends(require_permission(Permission.FORMAT_READ)),
    db: Session = Depends(get_db),
):
    result = get_project_document_formats(
        db=db,
        project_id=project_id,
        document_type=document_type,
        page=page,
        size=size,
    )

    return {
        "pages": result["pages"],
        "formats": [
            ProjectDocumentFormatResponse(
                id=item.id,
                format_name=item.format_name,
                document_type=item.document_type,
                extension=item.extension,
                content=item.content,
                source="custom",
                is_activated=item.is_activated,
            )
            for item in result["formats"]
        ],
    }


@router.get(
    "/projects/{project_id}/document-formats/active/{document_type}",
    response_model=DocumentFormatContentResponse,
)
async def get_active_format(
    project_id: int,
    document_type: str,
    access: ProjectAccessContext = Depends(require_permission(Permission.FORMAT_READ)),
    db: Session = Depends(get_db),
):
    result = await resolve_active_format(
        db=db,
        project_id=project_id,
        document_type=document_type,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document type '{document_type}' not found in system defaults.",
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
    access: ProjectAccessContext = Depends(require_permission(Permission.FORMAT_WRITE)),
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
    access: ProjectAccessContext = Depends(require_permission(Permission.FORMAT_WRITE)),
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
    access: ProjectAccessContext = Depends(require_permission(Permission.FORMAT_WRITE)),
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
    access: ProjectAccessContext = Depends(require_permission(Permission.FORMAT_WRITE)),
    db: Session = Depends(get_db),
):
    require_owner(access)

    await delete_custom_format(
        db=db,
        project_id=project_id,
        format_id=format_id,
    )

    db.commit()

    return {"message": "Custom format deleted successfully"}
