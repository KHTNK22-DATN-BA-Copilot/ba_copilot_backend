import os
import asyncio
import logging
import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
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
from app.schemas.srs import SRSGenerateResponse,GetSRSResponse,SRSListResponse
from app.utils.supabase_client import supabase
from app.core.config import settings
from app.utils.srs_utils import (
    upload_to_supabase,
    format_srs_to_markdown,
    extract_text_from_file,
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
        content_markdown=json.dumps(ai_data["response"]),
        status=ai_data.get("status", "generated"),
        document_metadata={
            "files": file_urls,
            "message":description,
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
        try:
            content_dict = json.loads(srs_doc.content_markdown)
            markdown_content = format_srs_to_markdown(content_dict)
        except Exception:
            markdown_content = srs_doc.content_markdown or ""

        result.append(
            GetSRSResponse(
                document_id=str(srs_doc.document_id),
                project_name=srs_doc.project_name,
                content=markdown_content,
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

    content_dict = json.loads(srs_doc.content_markdown)
    markdown_content = format_srs_to_markdown(content_dict)

    return GetSRSResponse(
        document_id=str(srs_doc.document_id),
        project_name=srs_doc.project_name,
        content=markdown_content,
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

    content_dict = json.loads(srs_doc.content_markdown)
    markdown_content = format_srs_to_markdown(content_dict)

    file_stream = BytesIO(markdown_content.encode("utf-8"))
    filename = f"{srs_doc.project_name.replace(' ', '_')}.md"

    return StreamingResponse(
        file_stream,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
