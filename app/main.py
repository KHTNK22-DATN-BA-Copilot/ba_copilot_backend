from fastapi import FastAPI, HTTPException
from app.api.v1 import auth
from app.core.database import engine, Base
import logging
import time
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BaCopilot Authentication API", version="1.0.0")

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Wait for database to be ready and create tables
    max_retries = 30
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Try to create tables
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
            break
        except Exception as e:
            retry_count += 1
            logger.warning(f"Database connection attempt {retry_count} failed: {str(e)}")
            if retry_count >= max_retries:
                logger.error("Max retries reached. Could not connect to database.")
                raise e
            time.sleep(2)


@app.get("/")
def read_root():
    return {"message": "BaCopilot Authentication API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    try:
        # Check database connection
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")