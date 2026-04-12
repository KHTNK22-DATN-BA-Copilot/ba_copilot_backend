from sqlalchemy import Column, Integer, String, Text, Index, DateTime, JSON
from sqlalchemy.dialects.postgresql import TSVECTOR
from app.core.database import Base
from sqlalchemy.sql import func

class GlobalSearchIndex(Base):
    __tablename__ = 'global_search_index'

    id = Column(Integer, primary_key=True)
    entity_id = Column(String, nullable=False)
    entity_type = Column(String(20))           
    project_id = Column(Integer, nullable=False)
    title = Column(Text)                       
    search_vector = Column(TSVECTOR)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

Index('idx_search_vector', GlobalSearchIndex.search_vector, postgresql_using='gin')
