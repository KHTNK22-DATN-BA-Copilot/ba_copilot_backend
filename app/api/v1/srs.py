import os
import asyncio
import logging
import uuid
import httpx
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Query,
    Response,
)
from fastapi.responses import StreamingResponse
from io import BytesIO
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import List
import json
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.srs import SRS
from app.models.user import User
from app.models.project_file import ProjectFile
from app.schemas.srs import SRSGenerateResponse,GetSRSResponse,SRSListResponse, UpdateSRSResponse
from app.utils.supabase_client import supabase
from app.core.config import settings
from app.utils.srs_utils import (
    upload_to_supabase,
    format_srs_to_markdown,
)
from app.utils.call_ai_service import call_ai_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate", response_model=SRSGenerateResponse)
async def generate_srs(
    project_id: int = Form(...),
    project_name: str = Form(...),
    description: str = Form(...),
    files: List[UploadFile] = File([]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload file lên Supabase, gọi AI service để tạo SRS,
    sau đó lưu document vào DB.
    """
    logger.info(
        f"User {current_user.email} requested SRS generation for {project_name}"
    )

    # Upload tất cả file lên Supabase
    file_urls: List[str] = []

    for file in files:
        url = await upload_to_supabase(file)
        if not url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file {file.filename}",
            )

        new_file = ProjectFile(
            file_path=url,
            project_id=project_id,
            user_id=current_user.id
        )
        db.add(new_file)
        file_urls.append(url)

    db.commit()
    for file in db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all():
        db.refresh(file)

    ai_payload = {
        "message": description,
    }

    # Gọi AI service
    generate_at = datetime.now(timezone.utc)
    ai_data = await call_ai_service(settings.ai_service_url_srs,ai_payload,files)

    markdown_content = format_srs_to_markdown(ai_data["response"])

    new_doc = SRS(
        project_id=project_id,
        user_id=current_user.id,
        project_name=project_name,
        content_markdown=markdown_content,
        status=ai_data.get("status", "generated"),
        document_metadata={
            "files": file_urls,
            "message": description,
            "ai_response": ai_data,
        },
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    logger.info(f"SRS generated and saved for project '{project_name}'")

    return SRSGenerateResponse(
        document_id=str(new_doc.document_id),
        user_id=str(current_user.id),
        generated_at=str(generate_at),
        input_description=description,
        document=markdown_content,
        status=new_doc.status,
    )


@router.get("/list/{project_id}", response_model=SRSListResponse)
async def list_SRS(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    srs_list = (
        db.query(SRS)
        .filter(SRS.user_id == current_user.id, SRS.project_id == project_id)
        .all()
    )

    result = []
    for srs_doc in srs_list:

        result.append(
            GetSRSResponse(
                document_id=str(srs_doc.document_id),
                project_name=srs_doc.project_name,
                content=srs_doc.content_markdown,
                status=srs_doc.status,
                updated_at=srs_doc.updated_at,
            )
        )

    return {"SRSs": result}


@router.get("/get/{project_id}/{document_id}", response_model=GetSRSResponse)
async def get_srs_document(
    project_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    srs_doc = (
        db.query(SRS)
        .filter(SRS.project_id == project_id, SRS.document_id == document_id, SRS.user_id==current_user.id)
        .first()
    )
    if not srs_doc:
        raise HTTPException(status_code=404, detail="Document not found")


    return GetSRSResponse(
        document_id=str(srs_doc.document_id),
        project_name=srs_doc.project_name,
        content=srs_doc.content_markdown,
        status=srs_doc.status,
        updated_at=srs_doc.updated_at,
    )


@router.get("/export/{project_id}/{document_id}", response_class=StreamingResponse)
async def export_markdown(
    project_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    srs_doc = (
        db.query(SRS)
        .filter(
            SRS.project_id == project_id,
            SRS.document_id == document_id,
            SRS.user_id == current_user.id,
        )
        .first()
    )
    if not srs_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_stream = BytesIO(srs_doc.content_markdown.encode("utf-8"))
    filename = f"{srs_doc.project_name.replace(' ', '_')}.md"

    return StreamingResponse(
        file_stream,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.put("/update/{project_id}/{document_id}", response_model=UpdateSRSResponse)
async def update_usecase_diagram(
    project_id: str,
    document_id: str,
    content: str = Form(...),
    document_status:str=Form(...),
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

    logger.info(f"User {current_user.email} requested update for diagram {document_id}")
    srs_doc = (
        db.query(SRS)
        .filter(
            SRS.project_id == project_id,
            SRS.document_id == document_id,
            SRS.user_id == current_user.id,
        )
        .first()
    )

    if not srs_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SRS document not found or you do not have permission to update it.",
        )

    srs_doc.status = document_status

    db.commit()
    db.refresh(srs_doc)

    return UpdateSRSResponse(
        document_id=str(srs_doc.document_id),
        project_name=srs_doc.project_name,
        content=content,
        status=document_status,
        updated_at=srs_doc.updated_at,
    )


@router.post("/re-generate", response_model=SRSGenerateResponse)
async def generate_srs(
    project_id: int = Form(...),
    project_name: str = Form(...),
    description: str = Form(...),
    files: List[UploadFile] = File([]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    logger.info(
        f"User {current_user.email} requested SRS generation for {project_name}"
    )

    # Upload tất cả file lên Supabase
    file_urls: List[str] = []

    for file in files:
        url = await upload_to_supabase(file)
        if not url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file {file.filename}",
            )

        new_file = ProjectFile(
            file_path=url, project_id=project_id, user_id=current_user.id
        )
        db.add(new_file)
        file_urls.append(url)

    db.commit()
    for file in (
        db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    ):
        db.refresh(file)

    ai_payload = {
        "message": description,
    }

    # Gọi AI service
    generate_at = datetime.now(timezone.utc)
    ai_data = await call_ai_service(settings.ai_service_url_srs, ai_payload, files)

    markdown_content = format_srs_to_markdown(ai_data["response"])

    new_doc = SRS(
        project_id=project_id,
        user_id=current_user.id,
        project_name=project_name,
        content_markdown=markdown_content,
        status=ai_data.get("status", "generated"),
        document_metadata={
            "files": file_urls,
            "message": description,
            "ai_response": ai_data,
        },
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    logger.info(f"SRS generated and saved for project '{project_name}'")

    return SRSGenerateResponse(
        document_id=str(new_doc.document_id),
        user_id=str(current_user.id),
        generated_at=str(generate_at),
        input_description=description,
        document=markdown_content,
        status=new_doc.status,
    )
