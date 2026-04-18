from datetime import datetime
from typing import List, Optional

from pydantic import Field
from pydantic import field_validator

from app.schemas.base_response import BaseResponseModel


class SaveAICredentialRequest(BaseResponseModel):
    provider: str
    api_key: str

    @field_validator("provider")
    @classmethod
    def provider_not_empty(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("provider is required")
        return normalized

    @field_validator("api_key")
    @classmethod
    def api_key_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("api_key is required")
        return value.strip()


class UpdateCurrentModelRequest(BaseResponseModel):
    current_model: str

    @field_validator("current_model")
    @classmethod
    def current_model_not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("current_model is required")
        return trimmed


class AICredentialResponse(BaseResponseModel):
    id: int
    provider: str
    status: str
    current_model: Optional[str] = None
    models_json: List[str] = Field(default_factory=list)
    masked_api_key: str
    updated_at: datetime

    class Config:
        from_attributes = True


class SaveAICredentialResponse(BaseResponseModel):
    message: str
    data: AICredentialResponse


class UpdateCurrentModelResponse(BaseResponseModel):
    message: str
    data: AICredentialResponse


class ListAICredentialsResponse(BaseResponseModel):
    items: List[AICredentialResponse] = Field(default_factory=list)


class ActivateAICredentialResponse(BaseResponseModel):
    message: str
    data: AICredentialResponse


class ProviderModelsResponse(BaseResponseModel):
    provider: str
    models: List[str] = Field(default_factory=list)
    default_model: Optional[str] = None


class ProviderModelsListResponse(BaseResponseModel):
    items: List[ProviderModelsResponse] = Field(default_factory=list)
