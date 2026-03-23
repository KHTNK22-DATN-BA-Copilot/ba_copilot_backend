from sqlalchemy import Column, Integer, String, Text, Index, DateTime, JSON
from sqlalchemy.dialects.postgresql import TSVECTOR
import datetime
from app.core.database import Base

class GlobalSearchIndex(Base):
    __tablename__ = 'global_search_index'
    
    id = Column(Integer, primary_key=True)
    entity_id = Column(String, nullable=False)
    entity_type = Column(String(20))           
    project_id = Column(Integer, nullable=False)
    title = Column(Text)                       
    search_vector = Column(TSVECTOR)
    
    metadata = Column(JSON) 
    updated_at = Column(DateTime, default=datetime.utcnow)

Index('idx_search_vector', GlobalSearchIndex.search_vector, postgresql_using='gin')