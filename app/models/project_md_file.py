from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ProjectMdFile(Base):
    __tablename__ = "project_md_files"

    id = Column(Integer, primary_key=True, index=True)
    raw_file_id=Column(Integer,ForeignKey("project_raw_files.id"))
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_name=Column(String,nullable=True)
    file_path = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
