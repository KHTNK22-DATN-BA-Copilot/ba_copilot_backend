from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey, text
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
    project_priority = Column(String(32), default="low", nullable=False)
    team_size = Column(Integer, default=1)
    settings = Column(JSON, default={}, nullable=False)
    due_date = Column(
        DateTime(timezone=True), server_default=text("(now() + interval '30 days')")
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

   
