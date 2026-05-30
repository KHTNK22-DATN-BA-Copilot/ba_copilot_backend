from dataclasses import dataclass
from enum import Enum

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.project_member import ProjectMember
from app.models.role import Role
from app.models.user import User


class Permission(Enum):
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_DELETE = "project:delete"
    
    MANAGE_MEMBERS = "project:manage_members"

    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    FILE_DELETE = "file:delete"

    FOLDER_READ = "folder:read"
    FOLDER_WRITE = "folder:write"
    FOLDER_DELETE = "folder:delete"

    FORMAT_READ = "format:read"
    FORMAT_WRITE = "format:write"
    FORMAT_DELETE = "format:delete"

@dataclass
class ProjectAccessContext:
    user: User
    member: ProjectMember
    role: Role
    permissions: dict


def require_permission(permission: Permission):
    def dependency(
        project_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> ProjectAccessContext:
        row = (
            db.query(ProjectMember, Role)
            .join(Role, Role.id == ProjectMember.role_id)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user.id,
            )
            .first()
        )

        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

        member, role = row
        role_permissions = role.permissions or {}
        resource, action = permission.value.split(":")

        if action not in role_permissions.get(resource, []):
            raise HTTPException(
                status_code=403,
                detail=f"Role {role.name} does not have {permission.value} permission",
            )

        return ProjectAccessContext(
            user=current_user,
            member=member,
            role=role,
            permissions=role_permissions,
        )

    return dependency
