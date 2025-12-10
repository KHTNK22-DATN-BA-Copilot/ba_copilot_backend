from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.database import Base

class File(Base):
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    extension = Column(String(32), nullable=True)
    storage_path = Column(String(512), nullable=True)
    content = Column(Text, nullable=True)
    file_category = Column(String(50), nullable=False)
    file_type = Column(String(50), nullable=False)
    status = Column(String(32), nullable=False, default="active")
    file_metadata = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
