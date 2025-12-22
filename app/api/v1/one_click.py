import asyncio
import logging
from fastapi import (
    WebSocket,
    APIRouter,
    Depends,
    status,
    WebSocketDisconnect,
    HTTPException,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.core.security import verify_token

from app.api.v1.planning import generate_planning_doc
from app.api.v1.design import generate_design

logger = logging.getLogger(__name__)
router = APIRouter()


# =========================
# WEBSOCKET ENDPOINT
# =========================
@router.websocket("/ws/generate/{project_id}")
async def websocket_generate_step(
    websocket: WebSocket,
    project_id: int,
    db: Session = Depends(get_db),
):
    # --------------------------------------------------
    # 1. AUTH
    # --------------------------------------------------
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
    logger.info(f"WS Connected | project_id={project_id} | user={email}")

    # --------------------------------------------------
    # 2. RUNTIME STATE
    # --------------------------------------------------
    continue_event = asyncio.Event()
    stop_event = asyncio.Event()
    orchestrator_task: asyncio.Task | None = None

    context = {
        "project_name": "",
        "description": "",
        "steps": [],
    }

    # --------------------------------------------------
    # 3. PROCESS SINGLE DOCUMENT
    # --------------------------------------------------
    async def process_single_doc(
        step: str,
        project_name: str,
        description: str,
        doc_type: str,
    ):
        try:
            await websocket.send_json(
                {
                    "type": "doc_start",
                    "step": step,
                    "doc_type": doc_type,
                }
            )

            # ----- CALL SERVICE -----
            if step == "planning":
                result = await generate_planning_doc(
                    project_id=project_id,
                    project_name=project_name,
                    doc_type=doc_type,
                    description=description,
                    db=db,
                    current_user=current_user,
                )

            elif step == "design":
                result = await generate_design(
                    project_id=project_id,
                    project_name=project_name,
                    design_type=doc_type,
                    description=description,
                    db=db,
                    current_user=current_user,
                )

            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported step: {step}",
                )

            res = result.model_dump() if hasattr(result, "model_dump") else result

            await websocket.send_json(
                {
                    "type": "doc_completed",
                    "step": step,
                    "doc_type": doc_type,
                    "data": res,
                }
            )

        except HTTPException as e:
            await websocket.send_json(
                {
                    "type": "doc_error",
                    "step": step,
                    "doc_type": doc_type,
                    "status_code": e.status_code,
                    "message": e.detail,
                }
            )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception("Unexpected error")
            await websocket.send_json(
                {
                    "type": "doc_error",
                    "step": step,
                    "doc_type": doc_type,
                    "message": "Internal server error",
                }
            )

    # --------------------------------------------------
    # 4. STEP ORCHESTRATOR (RUN BACKGROUND)
    # --------------------------------------------------
    async def run_steps():
        for step_cfg in context["steps"]:
            if stop_event.is_set():
                return

            step_name = step_cfg.get("name")
            documents = step_cfg.get("documents", [])

            if not step_name or not documents:
                await websocket.send_json(
                    {
                        "type": "step_error",
                        "step": step_name,
                        "message": "Invalid step configuration",
                    }
                )
                return

            await websocket.send_json(
                {
                    "type": "step_start",
                    "step": step_name,
                }
            )

            tasks = [
                asyncio.create_task(
                    process_single_doc(
                        step=step_name,
                        project_name=context["project_name"],
                        description=context["description"],
                        doc_type=doc["type"],
                    )
                )
                for doc in documents
            ]

            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                for t in tasks:
                    t.cancel()
                raise

            await websocket.send_json(
                {
                    "type": "step_finished",
                    "step": step_name,
                    "message": f"Finished step {step_name}",
                }
            )

            # ⏸ WAIT USER DECISION
            continue_event.clear()
            await websocket.send_json(
                {
                    "type": "await_decision",
                    "step": step_name,
                    "message": "Continue to next step?",
                }
            )

            await continue_event.wait()

        await websocket.send_json(
            {
                "type": "finished",
                "message": "All steps completed",
            }
        )

    # --------------------------------------------------
    # 5. WEBSOCKET MESSAGE LOOP
    # --------------------------------------------------
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            # ---------- ONE CLICK ----------
            if action == "one_click":
                context = {
                    "project_name": data["project_name"],
                    "description": data.get("description", ""),
                    "steps": data.get("steps", []),
                }

                if not context["steps"]:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "No steps provided from FE",
                        }
                    )
                    continue

                stop_event.clear()
                continue_event.clear()

                orchestrator_task = asyncio.create_task(run_steps())

            # ---------- CONTINUE ----------
            elif action == "continue":
                continue_event.set()

            # ---------- STOP ----------
            elif action == "stop":
                stop_event.set()
                if orchestrator_task:
                    orchestrator_task.cancel()

                await websocket.send_json(
                    {
                        "type": "stopped",
                        "message": "Process stopped by user",
                    }
                )

            # ---------- DISCONNECT ----------
            elif action == "disconnect":
                stop_event.set()
                if orchestrator_task:
                    orchestrator_task.cancel()
                await websocket.close()
                return

    except WebSocketDisconnect:
        stop_event.set()
        if orchestrator_task:
            orchestrator_task.cancel()
        logger.info("WS disconnected")

    except Exception:
        logger.exception("WS fatal error")
        if orchestrator_task:
            orchestrator_task.cancel()
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
