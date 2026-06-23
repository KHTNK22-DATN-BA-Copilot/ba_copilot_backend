from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rbac import Permission, ProjectAccessContext, require_permission
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User

router = APIRouter()


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: str


class UpdateMemberRoleRequest(BaseModel):
    role: str


def count_project_owners(db: Session, project_id: int) -> int:
    return (
        db.query(ProjectMember)
        .join(Role, Role.id == ProjectMember.role_id)
        .filter(ProjectMember.project_id == project_id, Role.name == "Owner")
        .count()
    )


def serialize_member(user: User, role: Role, joined_at: datetime):
    return {
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "role": role.name,
        "joined_at": joined_at,
    }


@router.get("/{project_id}/members")
async def list_project_members(
    project_id: int,
    access: ProjectAccessContext = Depends(require_permission(Permission.PROJECT_READ)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(ProjectMember, User, Role)
        .join(User, User.id == ProjectMember.user_id)
        .join(Role, Role.id == ProjectMember.role_id)
        .filter(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.created_at.asc())
        .all()
    )
    return {
        "members": [
            serialize_member(user, role, member.created_at)
            for member, user, role in rows
        ]
    }


@router.get("/{project_id}/members/me")
async def get_my_project_membership(
    project_id: int,
    access: ProjectAccessContext = Depends(require_permission(Permission.PROJECT_READ)),
):
    return {
        "project_id": project_id,
        "user_id": access.user.id,
        "role": access.role.name,
        "permissions": access.permissions,
    }


@router.post("/{project_id}/members/invite", status_code=201)
async def invite_project_member(
    project_id: int,
    body: InviteMemberRequest,
    access: ProjectAccessContext = Depends(
        require_permission(Permission.MANAGE_MEMBERS)
    ),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role = db.query(Role).filter(Role.name == body.role).first()
    if not role:
        raise HTTPException(status_code=400, detail="Role not found")

    existing = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="User is already a member")

    member = ProjectMember(project_id=project_id, user_id=user.id, role_id=role.id)
    db.add(member)
    db.commit()

    return {
        "project_id": project_id,
        "user_id": user.id,
        "email": user.email,
        "role": role.name,
        "message": "Member added to project",
    }


@router.patch("/{project_id}/members/{user_id}/role")
async def update_project_member_role(
    project_id: int,
    user_id: int,
    body: UpdateMemberRoleRequest,
    access: ProjectAccessContext = Depends(
        require_permission(Permission.MANAGE_MEMBERS)
    ),
    db: Session = Depends(get_db),
):
    target_member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        .first()
    )
    if not target_member:
        raise HTTPException(status_code=404, detail="Member not found")

    current_role = db.query(Role).filter(Role.id == target_member.role_id).first()
    new_role = db.query(Role).filter(Role.name == body.role).first()
    if not new_role:
        raise HTTPException(status_code=400, detail="Role not found")

    if current_role and current_role.name == "Owner" and new_role.name != "Owner":
        if count_project_owners(db, project_id) <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot downgrade the last project owner",
            )

    target_member.role_id = new_role.id
    db.commit()

    return {
        "project_id": project_id,
        "user_id": user_id,
        "role": new_role.name,
        "message": "Member role updated",
    }


@router.delete("/{project_id}/members/{user_id}")
async def remove_project_member(
    project_id: int,
    user_id: int,
    access: ProjectAccessContext = Depends(
        require_permission(Permission.MANAGE_MEMBERS)
    ),
    db: Session = Depends(get_db),
):
    target_member = (
        db.query(ProjectMember)
        .filter(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        .first()
    )
    if not target_member:
        raise HTTPException(status_code=404, detail="Member not found")

    role = db.query(Role).filter(Role.id == target_member.role_id).first()
    if role and role.name == "Owner" and count_project_owners(db, project_id) <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove the last project owner",
        )

    db.delete(target_member)
    db.commit()

    return {"message": "Member removed from project"}
