class StepWSNotifier:
    _clients: dict[tuple[int, str], set] = {}

    def __init__(self, project_id: int, step: str):
        self.key = (project_id, step)

    @classmethod
    def register(cls, project_id: int, step: str, ws):
        cls._clients.setdefault((project_id, step), set()).add(ws)

    @classmethod
    def unregister(cls, project_id: int, step: str, ws):
        cls._clients.get((project_id, step), set()).discard(ws)

    async def send(self, payload: dict):
        for ws in self._clients.get(self.key, []):
            await ws.send_json(payload)
