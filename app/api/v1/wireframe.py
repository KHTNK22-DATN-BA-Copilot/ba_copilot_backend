from io import BytesIO
import logging
import json as json_lib
import re
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
import json
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.document import Documents
from app.models.user import User
from app.models.session import Chat_Session
from app.core.config import settings
from app.schemas.wireframe import WireframeGenerateResponse, WireframeListResponse
from app.schemas.wireframe import GetWireframeResponse
from app.utils.call_ai_service import call_ai_service
from app.utils.file_handling import update_file_from_supabase, upload_to_supabase
from app.utils.get_unique_name import get_unique_diagram_name

logger = logging.getLogger(__name__)
router = APIRouter()


def extract_html_css_from_content(content: str) -> Tuple[str, str]:
    """Extract HTML and CSS from content"""
    html_content = ""
    css_content = None
    try:
        json_match = re.search(r"```(?:json)?\s*\n({.*?})\n```", content, re.DOTALL)
        html_match = re.search(r"```(?:html)?\s*\n(.*?)\n```", content, re.DOTALL)

        if json_match:
            json_str = json_match.group(1)
            try:
                parsed_json = json_lib.loads(json_str)
                html_content = parsed_json.get("html", "")
                css_content = parsed_json.get("css", "")

                if not css_content and html_content:
                    # Try to extract <style> tags
                    style_match = re.search(
                        r"<style[^>]*>(.*?)</style>", html_content, re.DOTALL
                    )
                    if style_match:
                        css_content = style_match.group(1)
                        # Remove style tags from HTML
                        html_content = re.sub(
                            r"<style[^>]*>.*?</style>",
                            "",
                            html_content,
                            flags=re.DOTALL,
                        )
            except json_lib.JSONDecodeError:
                # If JSON parsing fails, treat as plain HTML
                html_content = content
        elif html_match:
            # Content is HTML in markdown block
            html_content = html_match.group(1)
        else:
            # Plain content, assume it's HTML/CSS mixed
            html_content = content

        html_content = html_content.strip()
        if not html_content:
            html_content = content  # Fallback to original content

    except Exception as e:
        logger.warning(
            f"Error parsing AI response content: {str(e)}, using raw content"
        )
        html_content = content

    return html_content, css_content


"""
Generate wireframe with HTML and CSS
"""


@router.post("/generate", response_model=WireframeGenerateResponse)
async def generate_wireframe(
    project_id: int = Form(...),
    device_type: str = Form(...),
    wireframe_name: str = Form(...),
    description: Optional[str] = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
  
    combined_input = f"""
        Project Description:
        This project involves creating a wireframe for a {device_type} device.
        The wireframe is named "{wireframe_name}".

        Key Requirements:
        - General Description: {description}
    """

    unique_title = get_unique_diagram_name(db, wireframe_name, project_id, "wireframe")

    logger.info(
        f"Original title: '{wireframe_name}', Unique title chosen: '{unique_title}'"
    )

    ai_payload = {
        "message": combined_input,
    }

    # Call AI service
    generate_at = datetime.now(timezone.utc)
    try:
        ai_data = await call_ai_service(settings.ai_service_url_wireframe, ai_payload)
    except HTTPException as http_exc:
        # Re-raise if it’s already an HTTPException from the AI service
        raise http_exc
    except Exception as e:
        logger.error(f"Error calling AI service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calling AI service: {e}",
        )

    ai_content = ai_data.get("response", {}).get("content", "")
    file_name = f"/wireframe/{unique_title}.md"
    file_like = BytesIO(ai_content.encode("utf-8"))
    upload_file = UploadFile(filename=file_name, file=file_like)
    path_in_bucket = await upload_to_supabase(upload_file)
    if path_in_bucket is None:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    html_content, css_content = extract_html_css_from_content(ai_content)
    try:
        new_doc = Documents(
            project_id=project_id,
            user_id=current_user.id,
            document_name=unique_title,
            document_type="wireframe",
            content=ai_content,
            file_name=unique_title,
            file_path=path_in_bucket,
            document_metadata={
                "message": description,
                "ai_response": ai_data,
            },
        )
        db.add(new_doc)
        db.flush()  # get generated diagram_id + version without commit

        # Create chat sessions

        new_user_session = Chat_Session(
            session_id=new_doc.version,
            content_id=new_doc.document_id,
            project_id=project_id,
            user_id=current_user.id,
            content_type="wireframe",
            role="user",
            message=combined_input,
        )

        new_ai_session = Chat_Session(
            session_id=new_doc.version,
            content_id=new_doc.document_id,
            project_id=project_id,
            user_id=current_user.id,
            content_type="wireframe",
            role="ai",
            message=json.dumps(ai_data["response"]),
        )

        db.add_all([new_ai_session, new_user_session])
        db.commit()
        db.refresh(new_doc)
    except Exception as e:
        db.rollback()
        logger.error(f"Transaction failed: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to save wireframe and session data.",
        )

    logger.info(
        f"User {current_user.id} generated and saved for project '{unique_title}'"
    )

    return WireframeGenerateResponse(
        wireframe_id=str(new_doc.document_id),
        user_id=str(current_user.id),
        generated_at=str(generate_at),
        input_description=combined_input,
        html_content=html_content,
        css_content=css_content,
    )


@router.get("/list/{project_id}", response_model=WireframeListResponse)
async def list_wireframes(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document_type = "wireframe"
    wireframes = (
        db.query(Documents)
        .filter(
            Documents.project_id == project_id,
            Documents.user_id == current_user.id,
            Documents.document_type == document_type,
        )
        .all()
    )
    result = []
    for wireframe in wireframes:
        html_content, css_content = extract_html_css_from_content(wireframe.content)
        result.append(
            GetWireframeResponse(
                wireframe_id=str(wireframe.document_id),
                project_id=wireframe.project_id,
                user_id=wireframe.user_id,
                title=wireframe.document_name,
                html_content=html_content,
                css_content=css_content,
                created_at=wireframe.created_at,
                updated_at=wireframe.updated_at,
            )
        )
    return {"wireframes": result}


@router.get("/get/{project_id}/{wireframe_id}", response_model=GetWireframeResponse)
async def get_wireframe(
    wireframe_id: str,
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document_type = "wireframe"
    wireframe = (
        db.query(Documents)
        .filter(
            Documents.document_id == wireframe_id,
            Documents.project_id == project_id,
            Documents.user_id == current_user.id,
            Documents.document_type == document_type,
        )
        .first()
    )
    if not wireframe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wireframe not found",
        )

    html_content, css_content = extract_html_css_from_content(wireframe.content)
    return GetWireframeResponse(
        wireframe_id=str(wireframe.document_id),
        project_id=wireframe.project_id,
        user_id=wireframe.user_id,
        title=wireframe.document_name,
        html_content=html_content,
        css_content=css_content,
        created_at=wireframe.created_at,
        updated_at=wireframe.updated_at,
    )


@router.patch(
    "/regenerate/{project_id}/{wireframe_id}", response_model=GetWireframeResponse
)
async def regenerate_srs(
    project_id: int,
    wireframe_id: str,
    description: Optional[str] = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"User {current_user.email} requested SRS regeneration for {wireframe_id}"
    )

    document_type = "wireframe"
    existing_wireframe = (
        db.query(Documents)
        .filter(
            Documents.document_id == wireframe_id,
            Documents.project_id == project_id,
            Documents.user_id==current_user.id,
            Documents.document_type == document_type,
        )
        .first()
    )
    if not existing_wireframe:
        raise HTTPException(status_code=404, detail="Wireframe not found")

    if current_user.id != existing_wireframe.user_id:
        raise HTTPException(
            status_code=403, detail="You don't have permission to access this document."
        )

    ai_payload = {"message": description, "content_id": wireframe_id}

    try:
        ai_data = await call_ai_service(settings.ai_service_url_wireframe, ai_payload)
    except HTTPException as http_exc:
        # Re-raise if it’s already an HTTPException from the AI service
        raise http_exc
    except Exception as e:
        logger.error(f"Error calling AI service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calling AI service: {e}",
        )

    ai_content = ai_data.get("response", {}).get("content", "")
    html_content, css_content = extract_html_css_from_content(ai_content)
    existing_wireframe.content = ai_content
    existing_wireframe.version += 1

    file_name = f"/wireframe/{existing_wireframe.document_name}.md"
    file_like = BytesIO(existing_wireframe.content.encode("utf-8"))
    upload_file = UploadFile(filename=file_name, file=file_like)
    path_in_bucket = await update_file_from_supabase(
        existing_wireframe.file_path, upload_file
    )

    if path_in_bucket is None:
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    existing_wireframe.file_path = path_in_bucket

    try:

        generate_at = datetime.now(timezone.utc)

        new_user_session = Chat_Session(
            session_id=existing_wireframe.version,
            content_id=existing_wireframe.document_id,
            project_id=project_id,
            user_id=current_user.id,
            content_type="wireframe",
            role="user",
            message=description,
        )

        new_ai_session = Chat_Session(
            session_id=existing_wireframe.version,
            content_id=existing_wireframe.document_id,
            project_id=project_id,
            user_id=current_user.id,
            content_type="wireframe",
            role="ai",
            message=json.dumps(ai_data["response"]),
        )

        db.add_all([new_ai_session, new_user_session])
        db.commit()
        db.refresh(existing_wireframe)

        return GetWireframeResponse(
            wireframe_id=str(existing_wireframe.document_id),
            project_id=existing_wireframe.project_id,
            user_id=existing_wireframe.user_id,
            title=existing_wireframe.document_name,
            html_content=html_content,
            css_content=css_content,
            created_at=existing_wireframe.created_at,
            updated_at=existing_wireframe.updated_at,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
