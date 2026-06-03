from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.role import Role
from app.models.user import User

router = APIRouter()


@router.get("/")
async def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roles = db.query(Role).order_by(Role.id.asc()).all()
    return {
        "roles": [
            {
                "id": role.id,
                "name": role.name,
                "permissions": role.permissions or {},
            }
            for role in roles
        ]
    }
