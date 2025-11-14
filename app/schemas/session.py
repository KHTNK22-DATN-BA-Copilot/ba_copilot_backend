from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class GetSessionResponse(BaseModel):
    role: str
    message: str
    create_at: datetime


class ListSessionResponse(BaseModel):
    Sessions: List[GetSessionResponse] = Field(
        ..., description="List of srs session"
    )
