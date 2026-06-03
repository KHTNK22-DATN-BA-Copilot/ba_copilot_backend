from typing import Optional

from fastapi import APIRouter, Depends, Form, Query
from sqlalchemy.orm import Session

from app.api.v1.analysis import VALID_ANALYSIS_TYPES, format_response, get_ai_endpoint
from app.services.document_generation import (
    generate_document,
    get_document,
    list_documents,
    regenerate_document,
    update_document,
)
from app.core.database import get_db
from app.core.rbac import Permission, ProjectAccessContext, require_permission
from app.schemas.analysis import (
    AnalysisGenerateResponse,
    AnalysisListResponse,
    GetAnalysisResponse,
    UpdateAnalysisResponse,
)

router = APIRouter()


@router.post("/{project_id}/analysis/generate", response_model=AnalysisGenerateResponse)
async def generate_analysis_doc(
    project_id: int,
    project_name: str = Form(...),
    doc_type: str = Form(..., description="Type of analysis document"),
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
        valid_types=VALID_ANALYSIS_TYPES,
        step="analysis",
        type_field="doc_type",
        response_cls=AnalysisGenerateResponse,
        get_ai_endpoint=get_ai_endpoint,
        format_response=format_response,
        access=access,
        db=db,
    )


@router.get("/{project_id}/analysis", response_model=AnalysisListResponse)
async def list_analysis_docs(
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
        valid_types=VALID_ANALYSIS_TYPES,
        response_cls=AnalysisListResponse,
        item_response_cls=GetAnalysisResponse,
        type_field="doc_type",
        db=db,
    )


@router.get("/{project_id}/analysis/{document_id}", response_model=GetAnalysisResponse)
async def get_analysis_doc(
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
        valid_types=VALID_ANALYSIS_TYPES,
        response_cls=GetAnalysisResponse,
        type_field="doc_type",
        db=db,
    )


@router.put(
    "/{project_id}/analysis/{document_id}", response_model=UpdateAnalysisResponse
)
async def update_analysis_doc(
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
        valid_types=VALID_ANALYSIS_TYPES,
        response_cls=UpdateAnalysisResponse,
        access=access,
        db=db,
    )


@router.post(
    "/{project_id}/analysis/{document_id}/regenerate",
    response_model=AnalysisGenerateResponse,
)
async def regenerate_analysis_doc(
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
        valid_types=VALID_ANALYSIS_TYPES,
        type_field="doc_type",
        response_cls=AnalysisGenerateResponse,
        get_ai_endpoint=get_ai_endpoint,
        format_response=format_response,
        access=access,
        db=db,
    )
