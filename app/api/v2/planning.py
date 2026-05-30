from typing import Optional

from fastapi import APIRouter, Depends, Form, Query
from sqlalchemy.orm import Session

from app.api.v1.planning import VALID_PLANNING_TYPES, format_response, get_ai_endpoint
from app.services.document_generation import (
    generate_document,
    get_document,
    list_documents,
    regenerate_document,
    update_document,
)
from app.core.database import get_db
from app.core.rbac import Permission, ProjectAccessContext, require_permission
from app.schemas.planning import (
    GetPlanningResponse,
    PlanningGenerateResponse,
    PlanningListResponse,
    UpdatePlanningResponse,
)

router = APIRouter()


@router.post("/{project_id}/planning/generate", response_model=PlanningGenerateResponse)
async def generate_planning_doc(
    project_id: int,
    project_name: str = Form(...),
    doc_type: str = Form(..., description="Type of planning document"),
    description: Optional[str] = Form(""),
    access: ProjectAccessContext = Depends(
        require_permission(Permission.FILE_WRITE)
    ),
    db: Session = Depends(get_db),
):
    return await generate_document(
        project_id=project_id,
        project_name=project_name,
        document_type=doc_type,
        description=description,
        valid_types=VALID_PLANNING_TYPES,
        step="planning",
        type_field="doc_type",
        response_cls=PlanningGenerateResponse,
        get_ai_endpoint=get_ai_endpoint,
        format_response=format_response,
        access=access,
        db=db,
    )


@router.get("/{project_id}/planning", response_model=PlanningListResponse)
async def list_planning_docs(
    project_id: int,
    doc_type: Optional[str] = Query(None),
    access: ProjectAccessContext = Depends(
        require_permission(Permission.FILE_READ)
    ),
    db: Session = Depends(get_db),
):
    return list_documents(
        project_id=project_id,
        document_type=doc_type,
        valid_types=VALID_PLANNING_TYPES,
        response_cls=PlanningListResponse,
        item_response_cls=GetPlanningResponse,
        type_field="doc_type",
        db=db,
    )


@router.get("/{project_id}/planning/{document_id}", response_model=GetPlanningResponse)
async def get_planning_doc(
    project_id: int,
    document_id: str,
    access: ProjectAccessContext = Depends(
        require_permission(Permission.FILE_READ)
    ),
    db: Session = Depends(get_db),
):
    return get_document(
        project_id=project_id,
        document_id=document_id,
        valid_types=VALID_PLANNING_TYPES,
        response_cls=GetPlanningResponse,
        type_field="doc_type",
        db=db,
    )


@router.put(
    "/{project_id}/planning/{document_id}", response_model=UpdatePlanningResponse
)
async def update_planning_doc(
    project_id: int,
    document_id: str,
    content: str = Form(...),
    access: ProjectAccessContext = Depends(
        require_permission(Permission.FILE_WRITE)
    ),
    db: Session = Depends(get_db),
):
    return await update_document(
        project_id=project_id,
        document_id=document_id,
        content=content,
        valid_types=VALID_PLANNING_TYPES,
        response_cls=UpdatePlanningResponse,
        access=access,
        db=db,
    )


@router.post(
    "/{project_id}/planning/{document_id}/regenerate",
    response_model=PlanningGenerateResponse,
)
async def regenerate_planning_doc(
    project_id: int,
    document_id: str,
    description: Optional[str] = Form(""),
    access: ProjectAccessContext = Depends(
        require_permission(Permission.FILE_WRITE)
    ),
    db: Session = Depends(get_db),
):
    return await regenerate_document(
        project_id=project_id,
        document_id=document_id,
        description=description,
        valid_types=VALID_PLANNING_TYPES,
        type_field="doc_type",
        response_cls=PlanningGenerateResponse,
        get_ai_endpoint=get_ai_endpoint,
        format_response=format_response,
        access=access,
        db=db,
    )
