import asyncio
from typing import Dict, Tuple


class StepTaskRegistry:
    _tasks: Dict[Tuple[int,int, str], asyncio.Task] = {}

    @classmethod
    def get_task(cls, project_id: int,user_id:int ,step: str):
        return cls._tasks.get((project_id, user_id,step))

    @classmethod
    def start(cls, project_id: int,user_id:int ,step: str, coro):
        key = (project_id,user_id ,step)
        if key in cls._tasks:
            return cls._tasks[key]

        task = asyncio.create_task(coro)
        cls._tasks[key] = task
        return task

    @classmethod
    def finish(cls, project_id: int,user_id:int, step: str):
        cls._tasks.pop((project_id, user_id,step), None)
