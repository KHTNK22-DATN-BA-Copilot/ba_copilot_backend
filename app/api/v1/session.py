import logging
from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.srs import SRS
from app.models.session import Session
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
    document = db.query(SRS).filter(SRS.document_id == content_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    srs_session_list = (
        db.query(Session)
        .filter(Session.content_id == content_id)
        .order_by(Session.created_at.asc())
        .all()
    )

    result = []
    for srs_session in srs_session_list:

        result.append(
            GetSessionResponse(
                role=srs_session.role,
                message=srs_session.message,
                create_at=srs_session.created_at,
            )
        )

    return {"Sessions": result}
