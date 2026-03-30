from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.base_response import BaseResponseModel


class GetSessionResponse(BaseResponseModel):
    role: str
    message: str
    summary: Optional[str] = ""
    create_at: datetime


class ListSessionResponse(BaseResponseModel):
    Sessions: List[GetSessionResponse] = Field(
        ..., description="List of srs session"
    )
