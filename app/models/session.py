import uuid
from sqlalchemy import (
    CheckConstraint,
    Column,
    PrimaryKeyConstraint,
    String,
    Text,
    JSON,
    DateTime,
    Integer,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


from sqlalchemy import (
    CheckConstraint,
    Column,
    String,
    Text,
    DateTime,
    Integer,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Chat_Session(Base):
    __tablename__ = "sessions"

    session_id = Column(Integer)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content_type = Column(String(32), nullable=False)
    content_id = Column(
        UUID(as_uuid=True),
        nullable=False,
    )
    role = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint("session_id", "content_id", "role"),
        CheckConstraint("role IN ('user','ai')", name="role_check"),
        CheckConstraint(
            "content_type IN ('srs', 'wireframe', 'diagram', 'conversation')",
            name="content_type_check",
        ),
    )
