import logging
from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    Form,
)
from fastapi.responses import StreamingResponse
from io import BytesIO
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.file import Files
from app.models.folder import Folder
from app.models.session import Chat_Session

# Import Schema
from app.schemas.requirements_management_plan import (
    RMPGenerateResponse,
    GetRMPResponse,
    RMPListResponse,
    UpdateRMPResponse,
)
from app.schemas.folder import CreateFolderRequest
from app.core.config import settings
from app.utils.get_unique_name import get_unique_diagram_name
from app.utils.file_handling import (
    upload_to_supabase,
    update_file_from_supabase,
)
from app.utils.folder_utils import create_default_folder
from app.utils.call_ai_service import call_ai_service
from app.api.v1.file_upload import list_file

logger = logging.getLogger(__name__)
router = APIRouter()


def format_rmp_response(ai_response_data):
    if isinstance(ai_response_data, dict):
        return ai_response_data.get("content", "")
    return str(ai_response_data)


@router.post("/generate", response_model=RMPGenerateResponse)
async def generate_requirements_management_plan(
    project_id: int = Form(...),
    project_name: str = Form(...),
    description: Optional[str] = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"User {current_user.email} requested RMP generation for {project_name}"
    )

    new_folder = CreateFolderRequest(
        name="requirements_management_plan",
    )
    result = await create_default_folder(project_id, new_folder, current_user.id, db)

    if result.error:
        raise HTTPException(
            status_code=500, detail="Failed to create folder to storage"
        )

    folder = result.folder

    unique_title = get_unique_diagram_name(
        db, project_name, project_id, "requirements_management_plan"
    )

    logger.info(
        f"Original title: '{project_name}', Unique title chosen: '{unique_title}'"
    )

    ai_payload = {"message": description}
    generate_at = datetime.now(timezone.utc)

    ai_data = await call_ai_service(
        settings.ai_service_url_requirements_management_plan, ai_payload
    )

    markdown_content = format_rmp_response(ai_data["response"])

    file_name = f"/{folder.name}/{unique_title}.md"
    file_like = BytesIO(markdown_content.encode("utf-8"))
    upload_file = UploadFile(filename=file_name, file=file_like)
    path_in_bucket = await upload_to_supabase(upload_file)

    if path_in_bucket is None:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    try:
        new_file = Files(
            project_id=project_id,
            folder_id=folder.id,
            created_by=current_user.id,
            updated_by=current_user.id,
            name=unique_title,
            extension=".md",
            storage_path=path_in_bucket,
            content=markdown_content,
            file_category="ai gen",
            file_type="requirements_management_plan",
            metadata={
                "message": description,
                "ai_response": ai_data,
            },
        )
        db.add(new_file)
        db.flush()

        new_ai_session = Chat_Session(
            project_id=project_id,
            user_id=current_user.id,
            content_type="requirements_management_plan",
            content_id=new_file.id,
            role="ai",
            message=json.dumps(ai_data["response"]),
        )

        new_user_session = Chat_Session(
            project_id=project_id,
            user_id=current_user.id,
            content_type="requirements_management_plan",
            content_id=new_file.id,
            role="user",
            message=description,
        )

        db.add_all([new_ai_session, new_user_session])
        db.commit()
        db.refresh(new_file)

        return RMPGenerateResponse(
            document_id=str(new_file.id),
            user_id=str(current_user.id),
            generated_at=str(generate_at),
            input_description=description,
            document=markdown_content,
            status=new_file.status,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Database error during RMP generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/list/{project_id}", response_model=RMPListResponse)
async def list_requirements_management_plan(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_type = "requirements_management_plan"
    docs_list = (
        db.query(Files)
        .filter(
            Files.created_by == current_user.id,
            Files.project_id == project_id,
            Files.file_type == file_type,
        )
        .all()
    )

    result = []
    for doc in docs_list:
        result.append(
            GetRMPResponse(
                document_id=str(doc.id),
                project_name=doc.name,
                content=doc.content,
                status=doc.status,
                updated_at=doc.updated_at,
            )
        )

    return {"documents": result}


@router.get("/get/{project_id}/{document_id}", response_model=GetRMPResponse)
async def get_rmp_document(
    project_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_type = "requirements_management_plan"
    doc = (
        db.query(Files)
        .filter(
            Files.project_id == project_id,
            Files.id == document_id,
            Files.created_by == current_user.id,
            Files.file_type == file_type,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if current_user.id != doc.created_by:
        raise HTTPException(
            status_code=403, detail="You don't have permission to access this document."
        )

    return GetRMPResponse(
        document_id=str(doc.id),
        project_name=doc.name,
        content=doc.content,
        status=doc.status,
        updated_at=doc.updated_at,
    )


@router.get("/export/{project_id}/{document_id}", response_class=StreamingResponse)
async def export_markdown(
    project_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_type = "requirements_management_plan"
    doc = (
        db.query(Files)
        .filter(
            Files.project_id == project_id,
            Files.id == document_id,
            Files.created_by == current_user.id,
            Files.file_type == file_type,
        )
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if current_user.id != doc.created_by:
        raise HTTPException(
            status_code=403, detail="You don't have permission to access this document."
        )

    file_stream = BytesIO(doc.content.encode("utf-8"))
    filename = f"{doc.name.replace(' ', '_')}.md"

    return StreamingResponse(
        file_stream,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.put("/update/{project_id}/{document_id}", response_model=UpdateRMPResponse)
async def update_requirements_management_plan(
    project_id: str,
    document_id: str,
    content: str = Form(...),
    document_status: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    valid_document_status = [
        "generated",
        "draft",
        "published",
        "archived",
    ]
    if document_status not in valid_document_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document_status '{document_status}'. Must be one of {valid_document_status}.",
        )

    logger.info(f"User {current_user.email} requested update for RMP doc {document_id}")
    file_type = "requirements_management_plan"
    doc = (
        db.query(Files)
        .filter(
            Files.project_id == project_id,
            Files.id == document_id,
            Files.created_by == current_user.id,
            Files.file_type == file_type,
        )
        .first()
    )

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or you do not have permission to update it.",
        )

    if current_user.id != doc.created_by:
        raise HTTPException(
            status_code=403, detail="You don't have permission to access this document."
        )

    folder = (
        db.query(Folder)
        .filter(
            Folder.project_id == project_id,
            Folder.id == doc.folder_id,
        )
        .first()
    )

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder storage not found.",
        )

    doc.content = content
    doc.status = document_status
    doc.updated_by = current_user.id

    file_name = f"/{folder.name}/{doc.name}.md"
    file_like = BytesIO(doc.content.encode("utf-8"))
    upload_file = UploadFile(filename=file_name, file=file_like)
    path_in_bucket = await update_file_from_supabase(doc.storage_path, upload_file)

    if path_in_bucket is None:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    doc.storage_path = path_in_bucket

    db.commit()
    db.refresh(doc)

    return UpdateRMPResponse(
        document_id=str(doc.id),
        project_name=doc.name,
        content=content,
        status=document_status,
        updated_at=doc.updated_at,
    )


@router.patch(
    "/regenerate/{project_id}/{document_id}", response_model=RMPGenerateResponse
)
async def regenerate_requirements_management_plan(
    project_id: int,
    document_id: str,
    description: Optional[str] = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"User {current_user.email} requested RMP regeneration for {document_id}"
    )
    file_type = "requirements_management_plan"
    existing_doc = (
        db.query(Files)
        .filter(
            Files.id == document_id,
            Files.project_id == project_id,
            Files.file_type == file_type,
        )
        .first()
    )
    if not existing_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if current_user.id != existing_doc.created_by:
        raise HTTPException(
            status_code=403, detail="You don't have permission to access this document."
        )

    folder = (
        db.query(Folder)
        .filter(
            Folder.project_id == project_id,
            Folder.id == existing_doc.folder_id,
        )
        .first()
    )

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder storage not found.",
        )

    ai_payload = {"message": description, "content_id": document_id}

    ai_data = await call_ai_service(
        settings.ai_service_url_requirements_management_plan, ai_payload
    )
    markdown_content = format_rmp_response(ai_data["response"])

    file_name = f"/{folder.name}/{existing_doc.name}.md"
    file_like = BytesIO(markdown_content.encode("utf-8"))
    upload_file = UploadFile(filename=file_name, file=file_like)
    path_in_bucket = await update_file_from_supabase(
        existing_doc.storage_path, upload_file
    )

    if path_in_bucket is None:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    try:
        generate_at = datetime.now(timezone.utc)

        existing_doc.content = markdown_content
        existing_doc.file_metadata = {
            **existing_doc.file_metadata,
            "message": description,
            "ai_response": ai_data,
        }
        existing_doc.updated_by = current_user.id
        existing_doc.storage_path = path_in_bucket

        db.flush()

        new_ai_session = Chat_Session(
            content_id=existing_doc.id,
            project_id=project_id,
            user_id=current_user.id,
            content_type="requirements_management_plan",
            role="ai",
            message=json.dumps(ai_data["response"]),
        )

        new_user_session = Chat_Session(
            content_id=existing_doc.id,
            project_id=project_id,
            user_id=current_user.id,
            content_type="requirements_management_plan",
            role="user",
            message=description,
        )

        db.add_all([new_ai_session, new_user_session])
        db.commit()
        db.refresh(existing_doc)

        return RMPGenerateResponse(
            document_id=str(existing_doc.id),
            user_id=str(current_user.id),
            generated_at=str(generate_at),
            input_description=description,
            document=markdown_content,
            status=existing_doc.status,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
