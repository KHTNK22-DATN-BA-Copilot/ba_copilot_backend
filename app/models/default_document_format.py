from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
)

from sqlalchemy.sql import func

from app.core.database import Base


class DefaultDocumentFormat(Base):
    __tablename__ = "default_document_formats"

    id = Column(Integer, primary_key=True)

    document_type = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    content = Column(Text, nullable=False)

    extension = Column(String(20), nullable=False)

    description = Column(Text)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
