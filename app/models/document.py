import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    JSON,
    DateTime,
    Integer,
    ForeignKey,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Documents(Base):
    __tablename__ = "documents"

    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_name = Column(String(255), nullable=False)
    document_type = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(32), default="generated", nullable=False)
    file_name=Column(String,nullable=True)
    file_path = Column(String(100), nullable=False)
    document_metadata = Column(JSON, default={})
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('generated', 'draft', 'published', 'archived')",
            name="documents_status_check"
        ),
        CheckConstraint(
            "document_type IN ('srs','wireframe','sequence','architecture','usecase','flowchart','class','activity','entity_relationship')",
            name="documents_type_check"
        ),
    )