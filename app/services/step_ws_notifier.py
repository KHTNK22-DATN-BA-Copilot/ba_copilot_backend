import logging
from typing import Dict, Set, Tuple
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class StepWSNotifier:
   
    _clients: Dict[Tuple[int, str], Set[WebSocket]] = {}

    def __init__(self, project_id: int, step: str):
       
        self.project_id = project_id
        self.step = step
        self.key = (project_id, step)

    @classmethod
    def register(cls, project_id: int, step: str, ws: WebSocket):
        
        key = (project_id, step)
        cls._clients.setdefault(key, set()).add(ws)
        logger.debug(
            f"WS Registered for {key}. Total clients: {len(cls._clients[key])}"
        )

    @classmethod
    def unregister(cls, project_id: int, step: str, ws: WebSocket):
       
        key = (project_id, step)
        if key in cls._clients:
            cls._clients[key].discard(ws)
            if not cls._clients[key]:
                del cls._clients[key]
        logger.debug(f"WS Unregistered for {key}")

    async def send(self, payload: dict):
        
        
        clients = self._clients.get(self.key, set())

        if not clients:
            return

       
        dead_sockets = []

        
        for ws in list(clients):
            try:
                await ws.send_json(payload)
            except RuntimeError as e:
              
                logger.warning(
                    f"WS Disconnected unexpectedly for project {self.project_id}: {e}"
                )
                dead_sockets.append(ws)
            except Exception as e:
               
                logger.error(f"WS Send Error: {e}")
                dead_sockets.append(ws)

       
        if dead_sockets:
            for ws in dead_sockets:
                self.unregister(self.project_id, self.step, ws)
