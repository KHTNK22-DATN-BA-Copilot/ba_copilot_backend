import logging
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)

from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.diagram import Diagram
from app.models.user import User
from app.models.project import Project
from app.models.project_raw_file import ProjectRawFile
from app.core.config import settings
from app.schemas.diagram import (
    DiagramGenerateResponse,
    DiagramResponse,
    DiagramListResponse,
    DiagramUpdateResponse
)
from app.utils.mock_data.diagram_mock_data import get_mock_data

from app.utils.file_handling import (
    upload_to_supabase,
    has_extension
)
from app.utils.call_ai_service import call_ai_service

logger = logging.getLogger(__name__)
router = APIRouter()

# generate usecase-diagram
@router.post("/generate", response_model=DiagramGenerateResponse)
async def generate_usecase_diagram(
    project_id: int = Form(...),
    diagram_type: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    files: List[UploadFile] = File([]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"User {current_user.email} requested generation for {diagram_type} diagram"
    )

    valid_diagram_types = ["sequence", "architecture", "usecase", "flowchart", "class", "activity"]
    if diagram_type not in valid_diagram_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid diagram_type '{diagram_type}'. Must be one of {valid_diagram_types}.",
        )

    # file_urls: List[str] = []

    # for file in files:
    #     if not file.filename or not has_extension(file.filename):
    #         continue
    #     url = await upload_to_supabase(file)
    #     if not url:
    #         raise HTTPException(
    #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #             detail=f"Failed to upload file {file.filename}",
    #         )

    #     new_file = ProjectFile(
    #         file_path=url, project_id=project_id, user_id=current_user.id
    #     )
    #     db.add(new_file)
    #     file_urls.append(url)

    # db.commit()
    # for file in (
    #     db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
    # ):
    #     db.refresh(file)

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
        ai_data = await call_ai_service(ai_service_url, ai_payload, files)
        ai_response = ai_data.get("response") if ai_data else None

        if not ai_response or "detail" not in ai_response:
            raise ValueError("Invalid AI response format")

    except Exception as e:
        logger.error(f"AI service failed, using mock data. Error: {e}")
        ai_data = {"response": get_mock_data(diagram_type)}
        ai_response = ai_data["response"]

    new_diagram = Diagram(
        project_id=project_id,
        user_id=current_user.id,
        diagram_type=diagram_type,
        title=title,
        content_md=ai_data["response"]["detail"],
    )
    db.add(new_diagram)
    db.commit()
    db.refresh(new_diagram)

    logger.info(
        f"SRS generated and saved for project {diagram_type} diagram belong to project {project_id}"
    )

    return DiagramGenerateResponse(
        diagram_id=str(new_diagram.diagram_id),
        title=title,
        diagram_type=diagram_type,
        user_id=str(current_user.id),
        generated_at=str(generate_at),
        input_description=combined_input,
        content_md=new_diagram.content_md,
    )


@router.put("/update/{project_id}/{diagram_id}", response_model=DiagramUpdateResponse)
async def update_usecase_diagram(
    project_id: str,
    diagram_id: str,
    content_md: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"User {current_user.email} requested update for diagram {diagram_id}"
    )
    diagram = (
        db.query(Diagram)
        .filter(
            Diagram.project_id == project_id,
            Diagram.diagram_id == diagram_id,
            Diagram.user_id == current_user.id,
        )
        .first()
    )

    if not diagram:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Diagram not found or you do not have permission to update it.",
        )

    diagram.content_md = content_md

    db.commit()
    db.refresh(diagram)

    return DiagramUpdateResponse(
        diagram_id=str(diagram.diagram_id),
        title=diagram.title,
        diagram_type=diagram.diagram_type,
        update_at=str(diagram.updated_at),
        content_md=diagram.content_md,
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

        diagram = (
            db.query(Diagram)
            .filter(
                Diagram.project_id == project_id,
                Diagram.diagram_id == diagram_id,
                Diagram.user_id == current_user.id,
            )
            .first()
        )
        if not diagram:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Diagram with id {diagram_id} not found",
            )

        return DiagramResponse(
            diagram_id=str(diagram.diagram_id),
            title=diagram.title,
            diagram_type=diagram.diagram_type,
            update_at=str(diagram.updated_at),
            content_md=diagram.content_md,
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
            db.query(Diagram)
            .filter(
                Diagram.user_id == current_user.id,
                Diagram.project_id == project_id,
            )
            .order_by(Diagram.updated_at.desc())
            .all()
        )

        if not diagram_list:
            return {"diagrams": []}


        result = []
        for diagram in diagram_list:
            result.append(
                DiagramResponse(
                    diagram_id=str(diagram.diagram_id),
                    title=diagram.title,
                    diagram_type=diagram.diagram_type,
                    update_at=str(diagram.updated_at),
                    content_md=diagram.content_md,
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
