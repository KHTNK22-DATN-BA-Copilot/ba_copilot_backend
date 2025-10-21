import os
import asyncio
import logging
import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy.orm import Session
from typing import List
import json
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.srs import SRS
from app.models.user import User
from app.schemas.srs import SRSGenerateResponse, SRSDocument, SRSExportResponse
from app.utils.supabase_client import supabase
from app.utils.srs_utils import (
    upload_to_supabase,
    call_ai_service,
    format_srs_to_markdown,
)

logger = logging.getLogger(__name__)
router = APIRouter()

AI_SERVICE_URL = "http://ai:8000/v1/srs/generate"
SUPABASE_BUCKET = "uploads"


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
        file_urls.append(url)

    ai_payload = {
        "project_input": description,
        "file_urls": file_urls,  
    }

    # Gọi AI service
    ai_data = await call_ai_service(ai_payload)

    # Validate response
    required_fields = ["document", "generated_at", "status"]
    for field in required_fields:
        if field not in ai_data:
            logger.error(f"Invalid AI response, missing field: {field}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"AI service returned invalid response: missing {field}",
            )

    # Lưu document vào DB
    markdown_content = format_srs_to_markdown(ai_data["document"])

    new_doc = SRS(
        project_id=project_id,
        project_name=project_name,
        content_markdown=json.dumps(ai_data["document"]),
        status=ai_data.get("status", "generated"),
        document_metadata={
            "generated_at": ai_data["generated_at"],
            "files": file_urls,
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
        generated_at=ai_data["generated_at"],
        input_description=description,
        document=ai_data["document"],
        status=new_doc.status,
    )

@router.get("/export/{document_id}", response_class=StreamingResponse)
async def export_markdown(document_id: str, db: Session = Depends(get_db)):
    print(document_id)
    srs_doc = db.query(SRS).filter(SRS.document_id == document_id).first()
    if not srs_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    content_dict = json.loads(srs_doc.content_markdown)

    markdown_content = format_srs_to_markdown(content_dict)

    print(markdown_content)
    file_stream = BytesIO(markdown_content.encode("utf-8"))
    filename = f"{srs_doc.project_name.replace(' ', '_')}.md"

    
    return StreamingResponse(
        file_stream,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
