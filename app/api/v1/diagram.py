from io import BytesIO
import json
import logging
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    Form,
)

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.file import Files
from app.models.user import User
from app.models.project import Project
from app.models.session import Chat_Session
from app.core.config import settings
from app.schemas.diagram import (
    DiagramGenerateResponse,
    DiagramResponse,
    DiagramListResponse,
    DiagramUpdateResponse,
)
from app.utils.mock_data.diagram_mock_data import get_mock_data

from app.utils.file_handling import (
    update_file_from_supabase,
    upload_to_supabase,
)
from app.utils.folder_utils import create_default_folder
from app.utils.call_ai_service import call_ai_service
from app.utils.get_unique_name import get_unique_diagram_name
from app.schemas.folder import CreateFolderRequest

logger = logging.getLogger(__name__)
router = APIRouter()


# generate usecase-diagram
@router.post("/generate", response_model=DiagramGenerateResponse)
async def generate_usecase_diagram(
    project_id: int = Form(...),
    diagram_type: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"User {current_user.email} requested generation for {diagram_type} diagram"
    )

    valid_diagram_types = [
        "sequence",
        "architecture",
        "usecase",
        "flowchart",
        "class",
        "activity",
    ]
    if diagram_type not in valid_diagram_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid diagram_type '{diagram_type}'. Must be one of {valid_diagram_types}.",
        )

    new_folder = CreateFolderRequest(
        name=diagram_type,
    )
    result = await create_default_folder(project_id, new_folder, current_user.id, db)

    if result.error:
        raise HTTPException(
            status_code=500, detail="Failed to create folder to storage"
        )

    folder = result.folder

    unique_title = get_unique_diagram_name(db, title, project_id, diagram_type)

    logger.info(f"Original title: '{title}', Unique title chosen: '{unique_title}'")

    combined_input = f"""
        Project Description:
        This project involves creating a  {diagram_type} diagram.

        Key Requirements:
        - General Description: {description}
    """

    ai_payload = {
        "message": combined_input,
    }

    if diagram_type == "usecase":
        ai_service_url = settings.ai_service_url_diagram_usecase
    elif diagram_type == "class":
        ai_service_url = settings.ai_service_url_diagram_class
    elif diagram_type == "activity":
        ai_service_url = settings.ai_service_url_diagram_activity

    # Gọi AI service
    generate_at = datetime.now(timezone.utc)
    try:
        ai_data = await call_ai_service(ai_service_url, ai_payload)
        ai_response = ai_data.get("response") if ai_data else None

        if not ai_response or "detail" not in ai_response:
            raise ValueError("Invalid AI response format")

    except Exception as e:
        logger.error(f"AI service failed, using mock data. Error: {e}")
        ai_data = {"response": get_mock_data(diagram_type)}
        ai_response = ai_data["response"]

    file_name = f"/{diagram_type}/{unique_title}.md"
    file_like = BytesIO(ai_data["response"]["detail"].encode("utf-8"))
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
            content=ai_data["response"]["detail"],
            file_category="ai gen",
            file_type=diagram_type,
            metadata={
                "message": description,
                "ai_response": ai_data,
            },
        )
        db.add(new_file)
        db.flush()  # get generated diagram_id + version without commit

        # Create chat sessions
        new_ai_session = Chat_Session(
            
            content_id=new_file.id,
            project_id=project_id,
            user_id=current_user.id,
            content_type="diagram",
            role="ai",
            message=json.dumps(ai_data["response"]),
        )

        new_user_session = Chat_Session(
            content_id=new_file.id,
            project_id=project_id,
            user_id=current_user.id,
            content_type="diagram",
            role="user",
            message=description,
        )

        db.add_all([new_ai_session, new_user_session])
        db.commit()
        db.refresh(new_file)

    except Exception as e:
        db.rollback()
        logger.error(f"Transaction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to save diagram and session data.",
        )

    logger.info(
        f"SRS generated and saved for project {diagram_type} diagram belong to project {project_id}"
    )

    return DiagramGenerateResponse(
        diagram_id=str(new_file.id),
        title=unique_title,
        diagram_type=diagram_type,
        user_id=str(current_user.id),
        generated_at=str(generate_at),
        input_description=combined_input,
        content_md=new_file.content,
    )


@router.put("/update/{project_id}/{diagram_id}", response_model=DiagramUpdateResponse)
async def update_usecase_diagram(
    project_id: str,
    diagram_id: str,
    diagram_type: str,
    content_md: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"User {current_user.email} requested update for diagram {diagram_id}")
    diagram = (
        db.query(Files)
        .filter(
            Files.project_id == project_id,
            Files.id == diagram_id,
            Files.created_by == current_user.id,
            Files.file_type == diagram_type,
        )
        .first()
    )

    if not diagram:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagram not found or you do not have permission to update it.",
        )


    diagram.content = content_md

    file_name = f"/{diagram.file_type}/{diagram.name}.md"
    file_like = BytesIO(diagram.content.encode("utf-8"))
    upload_file = UploadFile(filename=file_name, file=file_like)
    path_in_bucket = await update_file_from_supabase(diagram.storage_path, upload_file)

    if path_in_bucket is None:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    diagram.storage_path = path_in_bucket
    diagram.updated_by=current_user.id

    db.commit()
    db.refresh(diagram)

    return DiagramUpdateResponse(
        diagram_id=str(diagram.id),
        title=diagram.name,
        diagram_type=diagram.file_type,
        update_at=str(diagram.updated_at),
        content_md=diagram.content,
    )


@router.get("/get/{project_id}/{diagram_id}", response_model=DiagramResponse)
async def get_diagram(
    project_id: str,
    diagram_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.user_id == current_user.id)
            .first()
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project",
            )

        valid_diagram_types = {"class", "usecase", "activity"}

        diagram = (
            db.query(Files)
            .filter(
                Files.project_id == project_id,
                Files.id == diagram_id,
                Files.created_by == current_user.id,
                Files.file_type.in_(valid_diagram_types),
            )
            .first()
        )
        if not diagram:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagram with id {diagram_id} not found",
            )

        return DiagramResponse(
            diagram_id=str(diagram.id),
            title=diagram.name,
            diagram_type=diagram.file_type,
            update_at=str(diagram.updated_at),
            content_md=diagram.content,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching diagram detail")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get("/list/{project_id}", response_model=DiagramListResponse)
async def list_diagram(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        valid_diagram_types = {"class", "usecase", "activity"}

        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.user_id == current_user.id)
            .first()
        )
        if not project:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project",
            )

        diagram_list = (
            db.query(Files)
            .filter(
                Files.created_by == current_user.id,
                Files.project_id == project_id,
                Files.file_type.in_(valid_diagram_types),
            )
            .order_by(Files.updated_at.desc())
            .all()
        )

        if not diagram_list:
            return {"diagrams": []}

        result = []
        for diagram in diagram_list:
            result.append(
                DiagramResponse(
                    diagram_id=str(diagram.id),
                    title=diagram.name,
                    diagram_type=diagram.file_type,
                    update_at=str(diagram.updated_at),
                    content_md=diagram.content,
                )
            )

        return {"diagrams": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching diagram list")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.patch("/regenerate/{project_id}/{diagram_id}", response_model=DiagramResponse)
async def regenerate_srs(
    project_id: int,
    diagram_id: str,
    description: Optional[str] = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"User {current_user.email} requested SRS regeneration for {diagram_id}"
    )
    valid_diagram_types = {"class", "usecase", "activity"}
    existing_diagram = (
        db.query(Files)
        .filter(
            Files.id == diagram_id,
            Files.project_id == project_id,
            Files.created_by == current_user.id,
            Files.file_type.in_(valid_diagram_types),
        )
        .first()
    )
    if not existing_diagram:
        raise HTTPException(status_code=404, detail="Diagram not found")

    if current_user.id != existing_diagram.user_id:
        raise HTTPException(
            status_code=403, detail="You don't have permission to access this document."
        )

    if existing_diagram.file_type == "usecase":
        ai_service_url = settings.ai_service_url_diagram_usecase
    elif existing_diagram.file_type == "class":
        ai_service_url = settings.ai_service_url_diagram_class
    elif existing_diagram.file_type == "activity":
        ai_service_url = settings.ai_service_url_diagram_activity

    ai_payload = {"message": description, "content_id": diagram_id}
    ai_data = await call_ai_service(ai_service_url, ai_payload)

    existing_diagram.content = ai_data["response"]["detail"]

    file_name = f"/{existing_diagram.file_type}/{existing_diagram.name}.md"
    file_like = BytesIO(existing_diagram.content.encode("utf-8"))
    upload_file = UploadFile(filename=file_name, file=file_like)
    path_in_bucket = await update_file_from_supabase(
        existing_diagram.storage_path, upload_file
    )

    if path_in_bucket is None:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    existing_diagram.storage_path = path_in_bucket
    existing_diagram.updated_by=current_user.id

    try:

        generate_at = datetime.now(timezone.utc)

        new_ai_session = Chat_Session(
            content_id=existing_diagram.id,
            project_id=project_id,
            user_id=current_user.id,
            content_type="diagram",
            role="ai",
            message=json.dumps(ai_data["response"]),
        )

        new_user_session = Chat_Session(
            content_id=existing_diagram.id,
            project_id=project_id,
            user_id=current_user.id,
            content_type="diagram",
            role="user",
            message=description,
        )

        db.add_all([new_ai_session, new_user_session])
        db.commit()
        db.refresh(existing_diagram)

        return DiagramResponse(
            diagram_id=str(existing_diagram.id),
            title=existing_diagram.name,
            diagram_type=existing_diagram.file_type,
            update_at=str(existing_diagram.updated_at),
            content_md=existing_diagram.content,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
