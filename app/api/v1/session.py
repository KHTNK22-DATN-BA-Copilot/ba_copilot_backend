import json
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.session import Chat_Session
from app.schemas.session import (
    ListSessionResponse,
    GetSessionResponse,
)
from app.utils.file_handling import (
    extract_html_css_from_content,
    merge_html_css,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def build_session_response(session_list):
    result = []

    for session in session_list:
        message = ""
        summary = ""

        if session.role == "ai":
            try:
                parsed = json.loads(session.message)
                content = parsed.get("content")

                if isinstance(content, dict):
                    html_content, css_content = extract_html_css_from_content(content)
                    message = merge_html_css(html_content, css_content or "")
                elif isinstance(content, str):
                    message = content
                else:
                    message = ""

                summary = parsed.get("summary") or ""

            except Exception:
                message = session.message or ""
        else:
            message = session.message or ""

        result.append(
            GetSessionResponse(
                role=session.role,
                message=message,
                summary=summary,
                create_at=session.created_at,
            )
        )

    return result


@router.get("/list/{content_id}", response_model=ListSessionResponse)
async def list_session(
    content_id: str,
    db: Session = Depends(get_db),
):
    session_list = (
        db.query(Chat_Session)
        .filter(Chat_Session.content_id == content_id)
        .order_by(Chat_Session.created_at.asc())
        .all()
    )

    return {"Sessions": build_session_response(session_list)}


@router.get("/list-ai/{content_id}", response_model=ListSessionResponse)
async def list_session_ai(
    content_id: str,
    db: Session = Depends(get_db),
):
    session_list = (
        db.query(Chat_Session)
        .filter(Chat_Session.content_id == content_id)
        .order_by(Chat_Session.created_at.desc())
        .all()
    )

    return {"Sessions": build_session_response(session_list)}
