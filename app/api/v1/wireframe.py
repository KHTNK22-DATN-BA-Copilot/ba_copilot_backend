import logging
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Query,
)
from fastapi.responses import StreamingResponse
from io import BytesIO
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import List
import json
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.wireframe import Wireframe
from app.models.user import User
from app.models.project_file import ProjectFile
from app.utils.supabase_client import supabase
from app.core.config import settings
from app.schemas.wireframe import WireframeGenerateResponse
from app.utils.srs_utils import (
    upload_to_supabase,
    call_ai_service,
    format_srs_to_markdown,
    extract_text_from_file,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate", response_model=WireframeGenerateResponse)
async def generate_srs(
    project_id: int = Form(...),
    device_type: str = Form(...),
    page_type: str = Form(...),
    fidelity: str = Form(...),
    wireframe_name: str = Form(...),
    description: str = Form(...),
    require_components: str = Form(...),
    color_schema:str=Form(...),
    style:str=Form(...),
    files: List[UploadFile] = File([]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"User {current_user.email} requested SRS generation for {wireframe_name}"
    )

    # Upload tất cả file lên Supabase
    file_urls: List[str] = []
    file_texts: List[str] = []

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

        text_content = await extract_text_from_file(file)
        file_texts.append(f"### File: {file.filename}\n{text_content}\n")

    db.commit()
    for file in (
        db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    ):
        db.refresh(file)

    combined_input = f"""
        Project Description:
        This project involves creating a {fidelity} {page_type} wireframe for a {device_type} device.
        The wireframe is named "{wireframe_name}" and follows the "{style}" design style with a {color_schema} color scheme.

        Key Requirements:
        - General Description: {description}
        - Required Components: {require_components}

        Attached Files Content:
        {''.join(file_texts)}
    """

    ai_payload = {
        "user_message": combined_input,
    }

    # Gọi AI service
    generate_at = datetime.now(timezone.utc)
    ai_data = await call_ai_service(settings.ai_service_url_wireframe, ai_payload)

    new_doc = Wireframe(
        project_id=project_id,
        user_id=current_user.id,
        project_name=wireframe_name,
        description = ai_data["response"]["description"],
        html_content = ai_data["response"]["figma_link"],
        template_type=page_type,
        document_metadata={
            "files": file_urls,
            "ai_response": ai_data,
        },
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    logger.info(f"SRS generated and saved for project '{wireframe_name}'")

    return WireframeGenerateResponse(
        wireframe_id=str(new_doc.wireframe_id),
        user_id=str(current_user.id),
        generated_at=str(generate_at),
        input_description=description,
        figma_link=new_doc.html_content,
        wireframe_description=new_doc.description,
    )
