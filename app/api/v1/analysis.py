import logging
import json
from io import BytesIO
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.file import Files
from app.models.folder import Folder
from app.models.session import Chat_Session

# Import Analysis Schemas
from app.schemas.analysis import (
    AnalysisGenerateResponse,
    GetAnalysisResponse,
    AnalysisListResponse,
    UpdateAnalysisResponse,
)
from app.schemas.folder import CreateFolderRequest
from app.core.config import settings
from app.utils.get_unique_name import get_unique_diagram_name
from app.utils.file_handling import upload_to_supabase, update_file_from_supabase
from app.utils.folder_utils import create_default_folder
from app.utils.call_ai_service import call_ai_service
from app.utils.metadata_utils import create_ai_generated_metadata
from app.services.docs_constraint import validate_dependencies

logger = logging.getLogger(__name__)
router = APIRouter()

# Danh sách các loại tài liệu trong Analysis Step (dựa trên ảnh)
VALID_ANALYSIS_TYPES = [
    "feasibility-study",
    "cost-benefit-analysis",
    "risk-register",
    "compliance",
]


def get_ai_endpoint(doc_type: str) -> str:
    config_name = f"ai_service_url_{doc_type.replace('-', '_')}"
    try:
        return getattr(settings, config_name)
    except AttributeError:
        logger.error(f"Missing config for {config_name}")
        raise HTTPException(
            status_code=500, detail=f"Missing configuration for {doc_type}"
        )


def format_response(ai_data):
    if isinstance(ai_data, dict):
        return (
            ai_data.get("content")
            or ai_data.get("detail")
            or json.dumps(ai_data, indent=2)
        )
    return str(ai_data)


@router.post("/generate", response_model=AnalysisGenerateResponse)
async def generate_analysis_doc(
    project_id: int = Form(...),
    project_name: str = Form(...),
    doc_type: str = Form(..., description="Type of analysis document"),
    description: Optional[str] = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if doc_type not in VALID_ANALYSIS_TYPES:
        raise HTTPException(
            status_code=400, detail=f"Invalid doc_type. Must be: {VALID_ANALYSIS_TYPES}"
        )

    dependency_result = validate_dependencies(project_id, doc_type, db, current_user)
    if not dependency_result["can_proceed"]:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot generate {doc_type}. Missing required documents: {dependency_result['missing_required']}",
        )

    result = await create_default_folder(
        project_id, CreateFolderRequest(name=doc_type), current_user.id, db
    )
    if result.error:
        raise HTTPException(500, "Failed to create folder")
    folder = result.folder

    ai_data = await call_ai_service(get_ai_endpoint(doc_type), {"message": description})
    ai_inner = ai_data.get("response", {})
    content = format_response(ai_inner)

    unique_title = get_unique_diagram_name(db, project_name, project_id, doc_type)
    file_path = await upload_to_supabase(
        UploadFile(
            filename=f"{current_user.id}/{project_id}/{folder.name}/{unique_title}.md",
            file=BytesIO(content.encode("utf-8")),
        )
    )
    if not file_path:
        raise HTTPException(500, "Upload failed")

    try:
        # Create structured metadata for AI-generated file
        file_metadata = create_ai_generated_metadata(
            doc_type=doc_type,
            content=content,
            message=description,
            ai_response=ai_data,
            step="analysis",
        )

        new_file = Files(
            project_id=project_id,
            folder_id=folder.id,
            created_by=current_user.id,
            updated_by=current_user.id,
            name=unique_title,
            extension=".md",
            storage_path=file_path,
            content=content,
            file_category="ai gen",
            file_type=doc_type,
            file_metadata=file_metadata,
        )
        db.add(new_file)
        db.flush()
        db.add_all(
            [
                Chat_Session(
                    project_id=project_id,
                    user_id=current_user.id,
                    content_type=doc_type,
                    content_id=new_file.id,
                    role="ai",
                    message=json.dumps(ai_inner),
                ),
                Chat_Session(
                    project_id=project_id,
                    user_id=current_user.id,
                    content_type=doc_type,
                    content_id=new_file.id,
                    role="user",
                    message=description,
                ),
            ]
        )
        db.commit()
        db.refresh(new_file)
        return AnalysisGenerateResponse(
            document_id=str(new_file.id),
            user_id=str(current_user.id),
            generated_at=str(datetime.now(timezone.utc)),
            input_description=description,
            document=content,
            doc_type=doc_type,
            status=new_file.status,
            recommend_documents=dependency_result["missing_recommended"],
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@router.get("/list/{project_id}", response_model=AnalysisListResponse)
async def list_analysis_docs(
    project_id: str,
    doc_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Files).filter(
        Files.created_by == current_user.id, Files.project_id == project_id
    )
    if doc_type:
        query = query.filter(Files.file_type == doc_type)
    else:
        query = query.filter(Files.file_type.in_(VALID_ANALYSIS_TYPES))

    return {
        "documents": [
            GetAnalysisResponse(
                document_id=str(d.id),
                project_name=d.name,
                content=d.content,
                doc_type=d.file_type,
                status=d.status,
                updated_at=d.updated_at,
            )
            for d in query.all()
        ]
    }


@router.get("/get/{project_id}/{document_id}", response_model=GetAnalysisResponse)
async def get_analysis_doc(
    project_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = (
        db.query(Files)
        .filter(
            Files.id == document_id,
            Files.project_id == project_id,
            Files.created_by == current_user.id,
            Files.file_type.in_(VALID_ANALYSIS_TYPES),
        )
        .first()
    )
    if not doc:
        raise HTTPException(404, "Not found")
    return GetAnalysisResponse(
        document_id=str(doc.id),
        project_name=doc.name,
        content=doc.content,
        doc_type=doc.file_type,
        status=doc.status,
        updated_at=doc.updated_at,
    )


@router.put("/update/{project_id}/{document_id}", response_model=UpdateAnalysisResponse)
async def update_analysis_doc(
    project_id: str,
    document_id: str,
    content: str = Form(...),
    status: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = (
        db.query(Files)
        .filter(
            Files.id == document_id,
            Files.project_id == project_id,
            Files.created_by == current_user.id,
            Files.file_type.in_(VALID_ANALYSIS_TYPES),
        )
        .first()
    )
    if not doc:
        raise HTTPException(404, "Not found")

    folder = db.query(Folder).filter(Folder.id == doc.folder_id).first()
    path = await update_file_from_supabase(
        doc.storage_path,
        UploadFile(
            filename=f"{current_user.id}/{project_id}/{folder.name}/{doc.name}.md",
            file=BytesIO(content.encode("utf-8")),
        ),
    )

    doc.content = content
    doc.status = status
    doc.updated_by = current_user.id
    if path:
        doc.storage_path = path
    db.commit()
    db.refresh(doc)
    return UpdateAnalysisResponse(
        document_id=str(doc.id),
        project_name=doc.name,
        content=content,
        status=status,
        updated_at=doc.updated_at,
    )


@router.patch(
    "/regenerate/{project_id}/{document_id}", response_model=AnalysisGenerateResponse
)
async def regenerate_analysis_doc(
    project_id: int,
    document_id: str,
    description: Optional[str] = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = (
        db.query(Files)
        .filter(
            Files.id == document_id,
            Files.project_id == project_id,
            Files.file_type.in_(VALID_ANALYSIS_TYPES),
        )
        .first()
    )
    if not doc:
        raise HTTPException(404, "Not found")
    if doc.created_by != current_user.id:
        raise HTTPException(403, "Forbidden")

    ai_data = await call_ai_service(
        get_ai_endpoint(doc.file_type),
        {"message": description, "content_id": document_id},
    )
    ai_inner = ai_data.get("response", {})
    content = format_response(ai_inner)

    folder = db.query(Folder).filter(Folder.id == doc.folder_id).first()
    path = await update_file_from_supabase(
        doc.storage_path,
        UploadFile(
            filename=f"{current_user.id}/{project_id}/{folder.name}/{doc.name}.md",
            file=BytesIO(content.encode("utf-8")),
        ),
    )

    try:
        doc.content = content
        doc.updated_by = current_user.id
        doc.storage_path = path
        doc.file_metadata = {
            **doc.file_metadata,
            "message": description,
            "ai_response": ai_data,
        }
        db.flush()
        db.add_all(
            [
                Chat_Session(
                    project_id=project_id,
                    user_id=current_user.id,
                    content_type=doc.file_type,
                    content_id=doc.id,
                    role="ai",
                    message=json.dumps(ai_inner),
                ),
                Chat_Session(
                    project_id=project_id,
                    user_id=current_user.id,
                    content_type=doc.file_type,
                    content_id=doc.id,
                    role="user",
                    message=description,
                ),
            ]
        )
        db.commit()
        db.refresh(doc)
        return AnalysisGenerateResponse(
            document_id=str(doc.id),
            user_id=str(current_user.id),
            generated_at=str(datetime.now(timezone.utc)),
            input_description=description,
            document=content,
            doc_type=doc.file_type,
            status=doc.status,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))
