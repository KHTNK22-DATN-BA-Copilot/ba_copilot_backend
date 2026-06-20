from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class DeletionJob(Base):
    __tablename__ = "deletion_jobs"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(
        UUID(as_uuid=True).with_variant(String(36), "sqlite"),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    storage_path = Column(String(512), nullable=True)
    storage_md_path = Column(String(512), nullable=True)
    status = Column(String(32), nullable=False, default="pending")
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
