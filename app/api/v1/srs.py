import logging
from uuid import UUID
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
from app.models.srs_attachment import Document_Attachments
from app.models.srs_session import SRSSession
from app.schemas.srs import (
    SRSGenerateResponse,
    GetSRSResponse,
    SRSListResponse,
    UpdateSRSResponse,
    ListSRSSessionResponse,
    GetSRSSessionResponse,
)
from app.core.config import settings
from app.utils.srs_utils import (
    upload_to_supabase,
    format_srs_to_markdown,
    get_file_from_supabase,
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

    logger.info(
        f"User {current_user.email} requested SRS generation for {project_name}"
    )

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
            "message": description,
            "ai_response": ai_data,
        },
    )

    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    try:
        file_urls = []
        if files:
            for file in files:
                url = await upload_to_supabase(file)
                if not url:
                    raise Exception(f"Failed to upload file {file.filename}")
                new_file = Document_Attachments(
                    file_path=url, document_id=new_doc.document_id
                )
                db.add(new_file)
                file_urls.append(url)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    logger.info(f"SRS generated and saved for project '{project_name}'")

    new_ai_session = SRSSession(
        session_id=new_doc.version,
        document_id=new_doc.document_id,
        user_id=current_user.id,
        role="ai",
        message=json.dumps(ai_data["response"]),
    )

    new_user_session = SRSSession(
        session_id=new_doc.version,
        document_id=new_doc.document_id,
        user_id=current_user.id,
        role="user",
        message=description,
    )

    db.add_all([new_ai_session, new_user_session])
    db.commit()

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
        .filter(
            SRS.project_id == project_id,
            SRS.document_id == document_id,
            SRS.user_id == current_user.id,
        )
        .first()
    )
    if not srs_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if current_user.id != srs_doc.user_id:
        raise HTTPException(
            status_code=403, detail="You don't have permission to access this document."
        )

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

    if current_user.id != srs_doc.user_id:
        raise HTTPException(
            status_code=403, detail="You don't have permission to access this document."
        )
    
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

    if current_user.id != srs_doc.user_id:
        raise HTTPException(
            status_code=403, detail="You don't have permission to access this document."
        )
    
    srs_doc.content_markdown=content
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


@router.patch(
    "/regenerate/{project_id}/{document_id}", response_model=SRSGenerateResponse
)
async def regenerate_srs(
    project_id: int,
    document_id: str,
    description: str = Form(...),
    files: List[UploadFile] = File([]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"User {current_user.email} requested SRS regeneration for {document_id}"
    )

    existing_doc = (
        db.query(SRS)
        .filter(SRS.document_id == document_id, SRS.project_id == project_id)
        .first()
    )
    if not existing_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if current_user.id!=existing_doc.user_id:
        raise HTTPException(
            status_code=403, detail="You don't have permission to access this document."
        )

    existing_files_db = (
        db.query(Document_Attachments)
        .filter(Document_Attachments.document_id == document_id)
        .all()
    )

    existing_files_uploadfile = await get_file_from_supabase(existing_files_db)

    ai_files = files + existing_files_uploadfile

    ai_payload = {"message": description, "document_id": document_id}
    ai_data = await call_ai_service(settings.ai_service_url_srs, ai_payload, ai_files)
    markdown_content = format_srs_to_markdown(ai_data["response"])

    existing_doc.content_markdown = markdown_content
    existing_doc.version += 1

    existing_doc.document_metadata = {
        **existing_doc.document_metadata,
        "message": description,
        "ai_response": ai_data,
    }

    try:
        file_urls = []
        if files:
            for file in files:
                url = await upload_to_supabase(file)
                if not url:
                    raise Exception(f"Failed to upload file {file.filename}")
                new_file = Document_Attachments(
                    file_path=url, document_id=existing_doc.document_id
                )
                db.add(new_file)
                file_urls.append(url)

        generate_at = datetime.now(timezone.utc)
        new_ai_session = SRSSession(
            session_id=existing_doc.version,
            document_id=existing_doc.document_id,
            user_id=current_user.id,
            role="ai",
            message=json.dumps(ai_data["response"]),
        )

        new_user_session = SRSSession(
            session_id=existing_doc.version,
            document_id=existing_doc.document_id,
            user_id=current_user.id,
            role="user",
            message=description,
        )
        db.add_all([new_ai_session, new_user_session])
        db.commit()
        db.refresh(existing_doc)

        return SRSGenerateResponse(
            document_id=str(existing_doc.document_id),
            user_id=str(current_user.id),
            generated_at=str(generate_at),
            input_description=description,
            document=markdown_content,
            status=existing_doc.status,
            version=existing_doc.version,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{document_id}", response_model=ListSRSSessionResponse)
async def list_SRS_Session(
    document_id: str,
    db: Session = Depends(get_db),
):
    document = db.query(SRS).filter(SRS.document_id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    srs_session_list = (
        db.query(SRSSession)
        .filter(SRSSession.document_id == document_id)
        .order_by(SRSSession.created_at.asc())
        .all()
    )

    result = []
    for srs_session in srs_session_list:

        result.append(
            GetSRSSessionResponse(
                role=srs_session.role,
                message=srs_session.message,
                create_at=srs_session.created_at,
            )
        )

    return {"SRSSessions": result}
