import uuid
from sqlalchemy import CheckConstraint, Column, PrimaryKeyConstraint, String, Text, JSON, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class SRSSession(Base):
    __tablename__ = "document_session"

    session_id = Column(Integer, nullable=False)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        PrimaryKeyConstraint("session_id", "document_id", "role"),
        CheckConstraint("role IN ('user','ai')", name="role_check"),
    )

