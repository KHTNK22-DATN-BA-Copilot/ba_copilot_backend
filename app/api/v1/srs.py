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
from app.schemas.srs import SRSGenerateResponse, SRSRequest
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
        if res.status_code not in (200, 201):
            logger.error(f"Failed to upload {file.filename}: {res}")
            return None

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
            await asyncio.sleep(2 * attempt)  # exponential backoff

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="AI service unavailable after multiple retries",
    )


@router.post("/generate", response_model=SRSGenerateResponse)
async def generate_srs(
    srsRequest: SRSRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload files lên Supabase, gọi AI service để tạo tài liệu SRS,
    sau đó lưu document vào DB.
    """
    logger.info(
        f"User {current_user.email} requested SRS generation for {srsRequest.project_name}"
    )

    # Upload tất cả file lên Supabase
    file_urls: List[str] = []
    for file in srsRequest.files:
        url = await upload_to_supabase(file)
        if not url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload file {file.filename}",
            )
        file_urls.append(url)

    # Chuẩn bị payload cho AI service
    ai_payload = {
        "project_input": srsRequest.description,
    }

    print(ai_payload)
    # Gọi AI service (retry + timeout)
    ai_data = await call_ai_service(ai_payload)

    # Parse & validate response
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
        project_id=srsRequest.project_id,
        project_name=srsRequest.project_name,
        content_markdown=json.dumps(ai_data["document"]),  # serialize dict -> string
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

    logger.info(f"SRS generated and saved for project '{srsRequest.project_name}'")

    # Trả về response cho client
    return SRSGenerateResponse(
        document_id=str(new_doc.document_id),
        user_id=str(current_user.id),
        generated_at=ai_data["generated_at"],
        input_description=srsRequest.description,
        document=ai_data["document"],
        status=new_doc.status,
    )
