import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, status
from sqlalchemy.orm import Session
import logging
from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User
from app.core.step_task_registry import StepTaskRegistry
from app.services.step_ws_notifier import StepWSNotifier
from app.services.design_runner import run_design_step

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/projects/{project_id}/upload")
async def ws_upload_file_notifier(
    websocket: WebSocket,
    project_id: int,
    db: Session = Depends(get_db),
):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    payload, error = verify_token(token)
    if error:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    email = payload.get("sub")
    current_user = db.query(User).filter(User.email == email).first()
    if not current_user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    StepWSNotifier.register(project_id, "upload", websocket)

    try:
        while True:
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        pass
    finally:
        StepWSNotifier.unregister(project_id, "upload", websocket)
