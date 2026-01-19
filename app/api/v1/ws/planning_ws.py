import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends,status
from sqlalchemy.orm import Session
import logging
from app.core.database import get_db
from app.core.security import verify_token
from app.models.user import User
from app.core.step_task_registry import StepTaskRegistry
from app.services.step_ws_notifier import StepWSNotifier
from app.services.planning_runner import run_planning_step

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/projects/{project_id}/planning")
async def ws_planning(
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

    StepWSNotifier.register(project_id, "planning", websocket)
    notifier = StepWSNotifier(project_id, "planning")

    try:
        init_data = await websocket.receive_json()
        existing_task = StepTaskRegistry.get_task(
            project_id, current_user.id, "planning"
        )

        if existing_task:
            logger.info("Cancelling previous planning task")
            existing_task.cancel()
            try:
                await existing_task

            except asyncio.CancelledError:
                pass

        stop_event = asyncio.Event()

        task = StepTaskRegistry.start(
            project_id,
            current_user.id,
            "planning",
            run_planning_step(
                project_id=project_id,
                project_name=init_data["project_name"],
                description=init_data.get("description", ""),
                documents=init_data["documents"],
                db=db,
                current_user=current_user,
                notifier=notifier,
                stop_event=stop_event,
            ),
        )

        while not task.done():
            recv_task = asyncio.create_task(websocket.receive_json())
            done, pending = await asyncio.wait(
                [task, recv_task], return_when=asyncio.FIRST_COMPLETED
            )
            if task in done:
                recv_task.cancel()  
                break
            if recv_task in done:
                try:
                    msg = recv_task.result()
                    if isinstance(msg, dict) and msg.get("action") == "stop":
                        logger.info(
                            f"Received STOP signal from FE for project {project_id}"
                        )
                        stop_event.set()
                    else:
                        logger.warning(f"Ignored message during generation: {msg}")
                except WebSocketDisconnect:
                    raise
                except Exception as e:
                    logger.error(f"Socket receive error: {e}")
                    break
        await task
        await websocket.close()

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected by client for project {project_id}")
        task = StepTaskRegistry.get_task(project_id,current_user.id ,"planning")
        if task and not task.done():
            logger.info(f"Cancelling planning task for project {project_id}")
            task.cancel() 
            try:
                await task
            except asyncio.CancelledError:
                pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass
    finally:
        StepWSNotifier.unregister(project_id,"planning", websocket)
