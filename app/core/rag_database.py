from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


rag_database_url = settings.rag_database_url or settings.database_url
rag_engine = create_engine(rag_database_url)
RagSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=rag_engine)


def get_rag_db():
    db = RagSessionLocal()
    try:
        yield db
    finally:
        db.close()