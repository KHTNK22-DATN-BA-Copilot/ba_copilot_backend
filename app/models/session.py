import uuid
from sqlalchemy import (
    CheckConstraint,
    Column,
    PrimaryKeyConstraint,
    String,
    Text,
    DateTime,
    Integer,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base


class Chat_Session(Base):
    __tablename__ = "sessions"

    # Sửa server_default thành default=uuid.uuid4 và thêm with_variant cho SQLite
    session_id = Column(
        UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        primary_key=True,
        default=uuid.uuid4,
    )

    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content_type = Column(String(32), nullable=False)

    # Thêm with_variant cho khóa ngoại trỏ tới bảng files
    content_id = Column(
        UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
    )

    role = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (CheckConstraint("role IN ('user','ai')", name="role_check"),)
