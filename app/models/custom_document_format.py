from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
    text,
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CustomDocumentFormat(Base):
    __tablename__ = "custom_document_formats"

    __table_args__ = (
        Index(
            "uq_custom_format_single_active",
            "project_id",
            "document_type",
            unique=True,
            postgresql_where=text("is_activated = true"),
        ),
        Index(
            "uq_custom_document_format_name",
            "project_id",
            "document_type",
            "format_name",
            unique=True,
        ),
    )

    id = Column(Integer, primary_key=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    format_name = Column(
        String(255),
        nullable=False,
    )

    document_type = Column(
        String(100),
        nullable=False,
    )

    content = Column(Text, nullable=False)

    extension = Column(String(20), nullable=False)

    is_activated = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    project = relationship(
        "Project",
        back_populates="custom_document_formats",
    )
