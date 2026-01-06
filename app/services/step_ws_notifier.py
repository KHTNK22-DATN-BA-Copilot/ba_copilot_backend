import logging
from typing import Dict, Set, Tuple
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class StepWSNotifier:
   
    _clients: Dict[Tuple[int, str], Set[WebSocket]] = {}

    def __init__(self, project_id: int, step: str):
        """
        Khởi tạo notifier cho một task cụ thể.
        Lưu ý: Không tạo mới _clients ở đây, mà dùng chung biến class.
        """
        self.project_id = project_id
        self.step = step
        self.key = (project_id, step)

    @classmethod
    def register(cls, project_id: int, step: str, ws: WebSocket):
        """Đăng ký một WebSocket mới vào danh sách nhận tin"""
        key = (project_id, step)
        cls._clients.setdefault(key, set()).add(ws)
        logger.debug(
            f"WS Registered for {key}. Total clients: {len(cls._clients[key])}"
        )

    @classmethod
    def unregister(cls, project_id: int, step: str, ws: WebSocket):
        """Hủy đăng ký WebSocket (khi client disconnect chủ động)"""
        key = (project_id, step)
        if key in cls._clients:
            cls._clients[key].discard(ws)
            if not cls._clients[key]:
                del cls._clients[key]
        logger.debug(f"WS Unregistered for {key}")

    async def send(self, payload: dict):
        """
        Gửi tin nhắn đến tất cả client đang lắng nghe task này.
        Tự động dọn dẹp các socket đã chết.
        """
        # Lấy danh sách socket hiện tại của task này
        clients = self._clients.get(self.key, set())

        if not clients:
            return

        # Danh sách socket cần xóa (đã chết)
        dead_sockets = []

        # QUAN TRỌNG: Phải convert set sang list() để tạo bản sao khi lặp.
        # Vì nếu ta xoá phần tử trong khi đang lặp set gốc sẽ gây lỗi "RuntimeError: Set changed size during iteration"
        for ws in list(clients):
            try:
                await ws.send_json(payload)
            except RuntimeError as e:
                # Bắt lỗi: "Unexpected ASGI message..." hoặc "Local protocol error"
                # Đây là dấu hiệu client đã mất kết nối bất ngờ
                logger.warning(
                    f"WS Disconnected unexpectedly for project {self.project_id}: {e}"
                )
                dead_sockets.append(ws)
            except Exception as e:
                # Các lỗi khác
                logger.error(f"WS Send Error: {e}")
                dead_sockets.append(ws)

        # Dọn dẹp các socket hỏng
        if dead_sockets:
            for ws in dead_sockets:
                self.unregister(self.project_id, self.step, ws)
