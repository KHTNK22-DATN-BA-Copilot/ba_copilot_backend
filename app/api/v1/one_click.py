from fastapi import WebSocket, APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.core.security import verify_token

from app.api.v1.srs import generate_srs
from app.api.v1.wireframe import generate_wireframe
from app.api.v1.diagram import generate_usecase_diagram


router = APIRouter()


@router.websocket("/one-click/{project_id}")
async def websocket_one_click(
    websocket: WebSocket,
    project_id: int,
    db: Session = Depends(get_db),
):
    await websocket.accept()

    # =============================
    # 1. Lấy token từ query param
    # =============================

    token = websocket.query_params.get("token")

    if not token:
        await websocket.send_json({"error": "Missing token"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # =============================
    # 2. Verify token (như HTTP)
    # =============================

    payload, error = verify_token(token)

    if error == "expired":
        await websocket.send_json({"error": "Token expired"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if error == "invalid":
        await websocket.send_json({"error": "Invalid token"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    email = payload.get("sub")
    if not email:
        await websocket.send_json({"error": "Invalid token payload"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # =============================
    # 3. Get user từ DB
    # =============================

    current_user = db.query(User).filter(User.email == email).first()

    if not current_user:
        await websocket.send_json({"error": "User not found"})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # =============================
    # 4. Main process steps
    # =============================

    steps = ["srs", "wireframe", "diagram"]
    description = "Auto generate description"
    project_name = "Auto Gen Project"

    for step in steps:
        try:
            if step == "srs":
                res = await generate_srs(
                    project_id=project_id,
                    project_name=project_name,
                    description=description,
                    db=db,
                    current_user=current_user,
                )

            elif step == "wireframe":
                res = await generate_wireframe(
                    project_id=project_id,
                    device_type="mobile",
                    wireframe_name="Auto Wireframe",
                    description=description,
                    db=db,
                    current_user=current_user,
                )

            elif step == "diagram":
                res = await generate_usecase_diagram(
                    project_id=project_id,
                    diagram_type="usecase",
                    title="Auto Diagram",
                    description=description,
                    db=db,
                    current_user=current_user,
                )

        except Exception as e:
            await websocket.send_json(
                {"error": f"{step} generation failed", "detail": str(e)}
            )
            await websocket.close()
            return

        # thông báo cho FE biết step đã xong
        await websocket.send_json(
            {
                "step": step,
                "status": "success",
                "message": f"{step.upper()} generated successfully",
                "res": res.model_dump(),
            }
        )

        # hỏi người dùng có muốn tiếp tục
        await websocket.send_json({"action": "confirm_continue"})

        reply = await websocket.receive_text()

        if reply.lower().strip() != "yes":
            await websocket.send_json({"status": "stopped_by_user"})
            await websocket.close()
            return

    # =============================
    # 5. Xong tất cả steps
    # =============================

    await websocket.send_json({"status": "completed"})
    await websocket.close()
