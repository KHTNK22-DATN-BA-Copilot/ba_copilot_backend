import logging
import json
from io import BytesIO
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    Form,
    Query,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.file import Files
from app.models.folder import Folder
from app.models.session import Chat_Session

from app.schemas.design import (
    DesignGenerateResponse,
    GetDesignResponse,
    DesignListResponse,
    UpdateDesignResponse,
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

# Danh sách các design_type hợp lệ
VALID_DESIGN_TYPES = [
    "hld-arch",
    "hld-cloud",
    "hld-tech",
    "lld-arch",
    "lld-db",
    "lld-api",
    "lld-pseudo",
    "uiux-wireframe",
    "uiux-mockup",
    "uiux-prototype",
]


def get_ai_endpoint(design_type: str) -> str:
    config_name = f"ai_service_url_{design_type.replace('-', '_')}"

    try:
        url = getattr(settings, config_name)
        return url
    except AttributeError:
        logger.error(f"Missing configuration for {config_name} in settings")
        raise HTTPException(
            status_code=500,
            detail=f"Server configuration error: Missing URL for {design_type}",
        )


def format_design_response(ai_response_data):
    """
    Extracts content based on AI response structure.
    """
    if isinstance(ai_response_data, dict):
        if "detail" in ai_response_data:
            return ai_response_data["detail"]
        if "content" in ai_response_data:
            return ai_response_data["content"]
        return json.dumps(ai_response_data, indent=2)
    return str(ai_response_data)


@router.post("/generate", response_model=DesignGenerateResponse)
async def generate_design(
    project_id: int = Form(...),
    project_name: str = Form(...),
    design_type: str = Form(
        ..., description="Type of design document (e.g., hld-arch, lld-db)"
    ),
    description: Optional[str] = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if design_type not in VALID_DESIGN_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid design_type. Must be one of: {', '.join(VALID_DESIGN_TYPES)}",
        )

    logger.info(
        f"User {current_user.email} requested {design_type} generation for {project_name}"
    )

    new_folder = CreateFolderRequest(name=design_type)
    result = await create_default_folder(project_id, new_folder, current_user.id, db)

    if result.error:
        raise HTTPException(status_code=500, detail="Failed to create folder storage")
    folder = result.folder

    unique_title = get_unique_diagram_name(db, project_name, project_id, design_type)

    file_urls = await list_file(project_id, db, current_user)
    ai_payload = {"message": description, "storage_paths": file_urls}

    ai_url = get_ai_endpoint(design_type)
    generate_at = datetime.now(timezone.utc)

    ai_data = await call_ai_service(ai_url, ai_payload)

    ai_inner_response = ai_data.get("response", {})
    markdown_content = format_design_response(ai_inner_response)

    # 5. Upload lên Supabase
    file_name = f"{current_user.id}/{project_id}/{folder.name}/{unique_title}.md"
    file_like = BytesIO(markdown_content.encode("utf-8"))
    upload_file = UploadFile(filename=file_name, file=file_like)
    path_in_bucket = await upload_to_supabase(upload_file)

    if path_in_bucket is None:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    # 6. Transaction DB
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
            file_type=design_type,
            metadata={
                "message": description,
                "ai_response": ai_data,
                "design_category": design_type.split("-")[0],
            },
        )
        db.add(new_file)
        db.flush()

        new_ai_session = Chat_Session(
            project_id=project_id,
            user_id=current_user.id,
            content_type=design_type,
            content_id=new_file.id,
            role="ai",
            message=json.dumps(ai_inner_response),
        )

        new_user_session = Chat_Session(
            project_id=project_id,
            user_id=current_user.id,
            content_type=design_type,
            content_id=new_file.id,
            role="user",
            message=description,
        )

        db.add_all([new_ai_session, new_user_session])
        db.commit()
        db.refresh(new_file)

        return DesignGenerateResponse(
            document_id=str(new_file.id),
            user_id=str(current_user.id),
            generated_at=str(generate_at),
            input_description=description,
            document=markdown_content,
            design_type=design_type,
            status=new_file.status,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Database error during {design_type} generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/list/{project_id}", response_model=DesignListResponse)
async def list_designs(
    project_id: str,
    design_type: Optional[str] = Query(
        None, description="Filter by specific design type"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Files).filter(
        Files.created_by == current_user.id,
        Files.project_id == project_id,
    )

    if design_type:
        query = query.filter(Files.file_type == design_type)
    else:
        query = query.filter(Files.file_type.in_(VALID_DESIGN_TYPES))

    docs_list = query.all()

    result = []
    for doc in docs_list:
        result.append(
            GetDesignResponse(
                document_id=str(doc.id),
                project_name=doc.name,
                content=doc.content,
                design_type=doc.file_type,
                status=doc.status,
                updated_at=doc.updated_at,
            )
        )

    return {"documents": result}


@router.get("/get/{project_id}/{document_id}", response_model=GetDesignResponse)
async def get_design_document(
    project_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = (
        db.query(Files)
        .filter(
            Files.project_id == project_id,
            Files.id == document_id,
            Files.created_by == current_user.id,
            Files.file_type.in_(VALID_DESIGN_TYPES),
        )
        .first()
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return GetDesignResponse(
        document_id=str(doc.id),
        project_name=doc.name,
        content=doc.content,
        design_type=doc.file_type,
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
    doc = (
        db.query(Files)
        .filter(
            Files.project_id == project_id,
            Files.id == document_id,
            Files.created_by == current_user.id,
            Files.file_type.in_(VALID_DESIGN_TYPES),
        )
        .first()
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_stream = BytesIO(doc.content.encode("utf-8"))
    filename = f"{doc.name.replace(' ', '_')}.md"

    return StreamingResponse(
        file_stream,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.put("/update/{project_id}/{document_id}", response_model=UpdateDesignResponse)
async def update_design_document(
    project_id: str,
    document_id: str,
    content: str = Form(...),
    document_status: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    valid_status = ["generated", "draft", "published", "archived"]
    if document_status not in valid_status:
        raise HTTPException(status_code=400, detail="Invalid status")

    doc = (
        db.query(Files)
        .filter(
            Files.project_id == project_id,
            Files.id == document_id,
            Files.created_by == current_user.id,
            Files.file_type.in_(VALID_DESIGN_TYPES),
        )
        .first()
    )

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    folder = db.query(Folder).filter(Folder.id == doc.folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    doc.content = content
    doc.status = document_status
    doc.updated_by = current_user.id

    file_name = f"{current_user.id}/{project_id}/{folder.name}/{doc.name}.md"
    file_like = BytesIO(doc.content.encode("utf-8"))
    upload_file = UploadFile(filename=file_name, file=file_like)

    path_in_bucket = await update_file_from_supabase(doc.storage_path, upload_file)
    if path_in_bucket:
        doc.storage_path = path_in_bucket

    db.commit()
    db.refresh(doc)

    return UpdateDesignResponse(
        document_id=str(doc.id),
        project_name=doc.name,
        content=content,
        status=document_status,
        updated_at=doc.updated_at,
    )


@router.patch(
    "/regenerate/{project_id}/{document_id}", response_model=DesignGenerateResponse
)
async def regenerate_design(
    project_id: int,
    document_id: str,
    description: Optional[str] = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing_doc = (
        db.query(Files)
        .filter(
            Files.id == document_id,
            Files.project_id == project_id,
            Files.file_type.in_(VALID_DESIGN_TYPES),
        )
        .first()
    )

    if not existing_doc:
        raise HTTPException(status_code=404, detail="Design document not found")

    if current_user.id != existing_doc.created_by:
        raise HTTPException(status_code=403, detail="Permission denied")

    design_type = existing_doc.file_type

    folder = db.query(Folder).filter(Folder.id == existing_doc.folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Lấy URL động từ settings
    ai_url = get_ai_endpoint(design_type)
    file_urls = await list_file(project_id, db, current_user)
    ai_payload = {
        "message": description,
        "content_id": document_id,
        "storage_paths": file_urls,
    }

    ai_data = await call_ai_service(ai_url, ai_payload)
    ai_inner_response = ai_data.get("response", {})
    markdown_content = format_design_response(ai_inner_response)

    file_name = f"{current_user.id}/{project_id}/{folder.name}/{existing_doc.name}.md"
    file_like = BytesIO(markdown_content.encode("utf-8"))
    upload_file = UploadFile(filename=file_name, file=file_like)
    path_in_bucket = await update_file_from_supabase(
        existing_doc.storage_path, upload_file
    )

    if not path_in_bucket:
        raise HTTPException(status_code=500, detail="Failed to upload file")

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
            content_type=design_type,
            role="ai",
            message=json.dumps(ai_inner_response),
        )

        new_user_session = Chat_Session(
            content_id=existing_doc.id,
            project_id=project_id,
            user_id=current_user.id,
            content_type=design_type,
            role="user",
            message=description,
        )

        db.add_all([new_ai_session, new_user_session])
        db.commit()
        db.refresh(existing_doc)

        return DesignGenerateResponse(
            document_id=str(existing_doc.id),
            user_id=str(current_user.id),
            generated_at=str(generate_at),
            input_description=description,
            document=markdown_content,
            design_type=design_type,
            status=existing_doc.status,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
