import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Form, Query
from sqlalchemy.orm import Session

from app.api.v1.design import (
    VALID_DESIGN_TYPES,
    format_design_response,
    get_ai_endpoint,
)
from app.services.document_generation import (
    generate_document,
    get_document,
    list_documents,
    regenerate_document,
    update_document,
)
from app.core.database import get_db
from app.core.rbac import Permission, ProjectAccessContext, require_permission
from app.schemas.design import (
    DesignGenerateResponse,
    DesignListResponse,
    GetDesignResponse,
    UpdateDesignResponse,
)
from app.utils.file_handling import extract_html_css_from_content, merge_html_css

router = APIRouter()
logger = logging.getLogger(__name__)


def transform_design_generate_response(ai_inner_response):
    ai_inner_content = ai_inner_response.get("content", {})
    html_content, css_content = extract_html_css_from_content(
        json.dumps(ai_inner_content)
    )
    if html_content:
        return merge_html_css(html_content, css_content or "")
    return ai_inner_content


@router.post("/{project_id}/design/generate", response_model=DesignGenerateResponse)
async def generate_design_doc(
    project_id: int,
    project_name: str = Form(...),
    design_type: str = Form(
        ..., description="Type of design document (e.g., hld-arch, lld-db)"
    ),
    description: Optional[str] = Form(""),
    access: ProjectAccessContext = Depends(require_permission(Permission.FILE_WRITE)),
    db: Session = Depends(get_db),
):
    return await generate_document(
        project_id=project_id,
        project_name=project_name,
        document_type=design_type,
        description=description,
        valid_types=VALID_DESIGN_TYPES,
        step="design",
        type_field="design_type",
        response_cls=DesignGenerateResponse,
        get_ai_endpoint=get_ai_endpoint,
        format_response=format_design_response,
        access=access,
        db=db,
        content_transform=transform_design_generate_response,
    )


@router.get("/{project_id}/design", response_model=DesignListResponse)
async def list_design_docs(
    project_id: int,
    design_type: Optional[str] = Query(None),
    access: ProjectAccessContext = Depends(require_permission(Permission.FILE_READ)),
    db: Session = Depends(get_db),
):
    return list_documents(
        project_id=project_id,
        document_type=design_type,
        valid_types=VALID_DESIGN_TYPES,
        response_cls=DesignListResponse,
        item_response_cls=GetDesignResponse,
        type_field="design_type",
        db=db,
    )


@router.get("/{project_id}/design/{document_id}", response_model=GetDesignResponse)
async def get_design_doc(
    project_id: int,
    document_id: str,
    access: ProjectAccessContext = Depends(require_permission(Permission.FILE_READ)),
    db: Session = Depends(get_db),
):
    return get_document(
        project_id=project_id,
        document_id=document_id,
        valid_types=VALID_DESIGN_TYPES,
        response_cls=GetDesignResponse,
        type_field="design_type",
        db=db,
    )


@router.put("/{project_id}/design/{document_id}", response_model=UpdateDesignResponse)
async def update_design_doc(
    project_id: int,
    document_id: str,
    content: str = Form(...),
    access: ProjectAccessContext = Depends(require_permission(Permission.FILE_WRITE)),
    db: Session = Depends(get_db),
):
    return await update_document(
        project_id=project_id,
        document_id=document_id,
        content=content,
        valid_types=VALID_DESIGN_TYPES,
        response_cls=UpdateDesignResponse,
        access=access,
        db=db,
    )


@router.post(
    "/{project_id}/design/{document_id}/regenerate",
    response_model=DesignGenerateResponse,
)
async def regenerate_design_doc(
    project_id: int,
    document_id: str,
    description: Optional[str] = Form(""),
    access: ProjectAccessContext = Depends(require_permission(Permission.FILE_WRITE)),
    db: Session = Depends(get_db),
):
    logger.info(f"description: {description}")
    return await regenerate_document(
        project_id=project_id,
        document_id=document_id,
        description=description,
        valid_types=VALID_DESIGN_TYPES,
        type_field="design_type",
        response_cls=DesignGenerateResponse,
        get_ai_endpoint=get_ai_endpoint,
        format_response=transform_design_generate_response,
        access=access,
        db=db,
    )
