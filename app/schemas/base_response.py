from pydantic import BaseModel, field_validator
from datetime import datetime
from app.utils.datetime_utils import utc_to_vn


class BaseResponseModel(BaseModel):
    """
    Base model to auto convert all datetime fields to Vietnam timezone
    """

    @field_validator("*", mode="before")
    @classmethod
    def convert_datetime(cls, v):
        if isinstance(v, datetime):
            return utc_to_vn(v)
        return v
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
