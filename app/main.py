from fastapi import FastAPI, HTTPException
from app.api.v1 import (
    auth,
    user,
    wireframe,
    srs,
    project_router,
    diagram,
    session,
    file_upload,
    one_click,
    folder,
    design,
    planning,
    analysis,
)

from app.api.v1.ws import planning_ws,design_ws,analysis_ws
from app.core.database import engine, Base
import logging
import time
from fastapi.middleware.cors import CORSMiddleware


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BaCopilot Authentication API", version="1.0.0")

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(user.router, prefix="/api/v1/user", tags=["user"])
app.include_router(srs.router, prefix="/api/v1/srs", tags=["srs_generator"])
app.include_router(
    wireframe.router, prefix="/api/v1/wireframe", tags=["wireframe_generator"]
)
app.include_router(diagram.router, prefix="/api/v1/diagram", tags=["diagram_generator"])
app.include_router(project_router.router, prefix="/api/v1/projects", tags=["project"])
app.include_router(file_upload.router, prefix="/api/v1/files", tags=["file"])
app.include_router(session.router, prefix="/api/v1/sessions", tags=["chat history"])
app.include_router(folder.router, prefix="/api/v1/folders", tags=["folders"])

app.include_router(design.router,prefix="/api/v1/design",tags=["design step"])
app.include_router(planning.router,prefix="/api/v1/planning",tags=["planning step"])
app.include_router(analysis.router,prefix="/api/v1/analysis",tags=["analysis"])

app.include_router(planning_ws.router,prefix="/api/v1",tags=["planning step websocket"])
app.include_router(
    design_ws.router, prefix="/api/v1", tags=["design step websocket"]
)
app.include_router(analysis_ws.router, prefix="/api/v1", tags=["analysis step websocket"])

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
            logger.warning(
                f"Database connection attempt {retry_count} failed: {str(e)}"
            )
            if retry_count >= max_retries:
                logger.error("Max retries reached. Could not connect to database.")
                raise e
            time.sleep(2)

app.include_router(
    one_click.router, prefix="/api/v1", tags=["one click flow"]
)


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
