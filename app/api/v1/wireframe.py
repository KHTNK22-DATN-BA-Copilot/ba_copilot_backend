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
    Query,
)
from fastapi.responses import StreamingResponse
from io import BytesIO
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import List, Tuple
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
)
from app.utils.call_ai_service import call_ai_service

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
    page_type: str = Form(...),
    fidelity: str = Form(...),
    wireframe_name: str = Form(...),
    description: str = Form(...),
    require_components: str = Form(...),
    color_schema: str = Form(...),
    style: str = Form(...),
    files: List[UploadFile] = File([]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"User {current_user.email} requested wireframe generation for {wireframe_name}"
    )

    # Upload all files to Supabase
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
            user_id=current_user.id,
            belong_to="wireframe",
        )
        db.add(new_file)
        file_urls.append(url)

    db.commit()

    combined_input = f"""
        Project Description:
        This project involves creating a {fidelity} {page_type} wireframe for a {device_type} device.
        The wireframe is named "{wireframe_name}" and follows the "{style}" design style with a {color_schema} color scheme.

        Key Requirements:
        - General Description: {description}
        - Required Components: {require_components}
    """

    ai_payload = {
        "message": combined_input,
    }

    # Call AI service
    generate_at = datetime.now(timezone.utc)
    try:
        ai_data = await call_ai_service(
            settings.ai_service_url_wireframe, ai_payload, files
        )
    except Exception as e:
        logger.error(f"Error calling AI service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calling AI service: {e}",
        )

    ai_content = ai_data.get("response", {}).get("content", "")
    html_content, css_content = extract_html_css_from_content(ai_content)
    new_doc = Wireframe(
        project_id=project_id,
        user_id=current_user.id,
        title=wireframe_name,
        description=combined_input,
        html_content=html_content,
        css_content=css_content,
        template_type=page_type,
        wireframe_metadata={
            "files": file_urls,
            "ai_response": ai_data,
        },
    )
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    logger.info(
        f"User {current_user.id} generated and saved for project '{wireframe_name}'"
    )

    return WireframeGenerateResponse(
        wireframe_id=str(new_doc.wireframe_id),
        user_id=str(current_user.id),
        generated_at=str(generate_at),
        input_description=combined_input,
        html_content=new_doc.html_content,
        css_content=new_doc.css_content,
    )
