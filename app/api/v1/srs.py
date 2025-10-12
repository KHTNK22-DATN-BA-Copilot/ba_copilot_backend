import os
import asyncio
import logging
import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import json
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.srs import SRS
from app.models.user import User
from app.schemas.srs import SRSGenerateResponse
from app.utils.supabase_client import supabase

logger = logging.getLogger(__name__)
router = APIRouter()

AI_SERVICE_URL = "http://ai:8000/v1/srs/generate"
SUPABASE_BUCKET = "uploads"


async def upload_to_supabase(file: UploadFile) -> str | None:
    """Upload file lên Supabase và trả về public URL."""
    try:
        file_name = f"{uuid.uuid4()}_{file.filename}"
        file_data = await file.read()

        res = supabase.storage.from_(SUPABASE_BUCKET).upload(file_name, file_data)

        
        # Kiểm tra upload thành công
        if not res.path:
            logger.error(f"Failed to upload {file.filename}")
            return None
        # Lấy public URL
        public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(file_name)
        logger.info(f"Uploaded {file.filename} to Supabase → {public_url}")
        return public_url

    except Exception as e:
        logger.exception(f"Upload failed for {file.filename}: {e}")
        return None


async def call_ai_service(payload: dict, retries: int = 3, timeout: int = 120):
    """Gọi AI service với retry & timeout logic."""
    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(AI_SERVICE_URL, json=payload)

            if response.status_code == 200:
                return response.json()

            logger.warning(
                f"AI service returned {response.status_code} (attempt {attempt}/{retries})"
            )
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            logger.warning(f"AI request failed (attempt {attempt}/{retries}): {e}")
            await asyncio.sleep(2 * attempt)

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="AI service unavailable after multiple retries",
    )


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
