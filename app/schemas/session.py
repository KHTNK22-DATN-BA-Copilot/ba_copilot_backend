from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class GetSessionResponse(BaseModel):
    role: str
    message: str
    summary: Optional[str] = ""
    create_at: datetime


class ListSessionResponse(BaseModel):
    Sessions: List[GetSessionResponse] = Field(
        ..., description="List of srs session"
    )
