import logging
from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.session import Chat_Session
from app.schemas.session import (
    ListSessionResponse,
    GetSessionResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/list/{content_id}", response_model=ListSessionResponse)
async def list_Session(
    content_id: str,
    db: Session = Depends(get_db),
):

    session_list = (
        db.query(Chat_Session)
        .filter(Chat_Session.content_id == content_id)
        .order_by(Chat_Session.created_at.asc())
        .all()
    )

    result = []
    for session in session_list:

        result.append(
            GetSessionResponse(
                role=session.role,
                message=session.message,
                create_at=session.created_at,
            )
        )

    return {"Sessions": result}
