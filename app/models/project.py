from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), default="active", nullable=False)
    settings = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="projects")
    documents = relationship(
        "SRS", back_populates="project", cascade="all, delete-orphan"
    )
    wireframes = relationship(
        "Wireframe", back_populates="project", cascade="all, delete-orphan"
    )
    diagrams = relationship(
        "Diagram", back_populates="project", cascade="all, delete-orphan"
    )
    conversations = relationship(
        "Conversation", back_populates="project", cascade="all, delete-orphan"
    )
    files = relationship(
        "ProjectFile", back_populates="project", cascade="all, delete-orphan"
    )
