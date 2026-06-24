from collections import defaultdict
from app.models.ai_provider_model import AIProviderModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import case

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.ai_credential import AICredential
from app.models.user import User
from app.schemas.ai_credential import (
    ActivateAICredentialResponse,
    AICredentialResponse,
    DeleteAICredentialResponse,
    ListAICredentialsResponse,
    ProviderModelsListResponse,
    ProviderModelsResponse,
    SaveAICredentialRequest,
    SaveAICredentialResponse,
    UpdateCurrentModelRequest,
    UpdateCurrentModelResponse,
    ClearActiveAICredentialResponse,
)
from app.utils.encryption import decrypt_api_key, encrypt_api_key, mask_api_key

router = APIRouter()


## helper functions
def _get_active_models_for_provider(
    db: Session, provider: str
) -> list[AIProviderModel]:
    return (
        db.query(AIProviderModel)
        .filter(
            AIProviderModel.provider == provider,
            AIProviderModel.is_active == True,
        )
        .order_by(AIProviderModel.is_default.desc(), AIProviderModel.id.asc())
        .all()
    )


def _get_default_model_name(models: list[AIProviderModel]) -> str | None:
    for model in models:
        if model.is_default:
            return model.model_name
    return models[0].model_name if models else None


def _build_provider_models_response(
    provider: str,
    models: list[AIProviderModel],
) -> dict:
    return {
        "provider": provider,
        "models": [model.model_name for model in models],
        "default_model": _get_default_model_name(models),
    }


def _build_ai_credential_response(
    credential: AICredential, masked_api_key: str
) -> dict:
    return {
        "id": credential.id,
        "provider": credential.provider,
        "status": credential.status,
        "current_model": credential.current_model,
        "masked_api_key": masked_api_key,
        "updated_at": credential.updated_at,
    }


# This endpoint returns the list of all providers with their active models. Providers without any active model will be excluded from the list.
@router.get("/models", response_model=ProviderModelsListResponse)
def get_all_provider_models(db: Session = Depends(get_db)):
    rows = db.query(AIProviderModel).filter(AIProviderModel.is_active == True).all()

    grouped_providers: dict[str, list[AIProviderModel]] = defaultdict(list)
    for row in rows:
        grouped_providers[row.provider].append(row)

    items = []
    for provider, models in grouped_providers.items():
        items.append(
            _build_provider_models_response(provider, models),
        )

    return {"items": items}


# This endpoint returns the list of active models for a given provider. The provider name is case-insensitive and whitespace-trimmed. If the provider does not exist or has no active models, it returns a 404 error.
@router.get("/models/{provider}", response_model=ProviderModelsResponse)
def get_provider_models(provider: str, db: Session = Depends(get_db)):
    normalized_provider = provider.strip().lower()
    models = _get_active_models_for_provider(db, normalized_provider)
    if not models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found or has no active models",
        )

    return _build_provider_models_response(normalized_provider, models)


# This endpoint saves a new API key for the user. It will automatically deactivate any existing active keys for the user to enforce single active credential. The API key is encrypted before saving, and the response includes a masked version of the key.
@router.post("/api-key", response_model=SaveAICredentialResponse)
def save_api_key(
    request: SaveAICredentialRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    provider_models = _get_active_models_for_provider(db, request.provider)
    default_model = _get_default_model_name(provider_models)
    if not default_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported provider or provider has no active models",
        )

    # Enforce single active key per user by deactivating older active rows.
    db.query(AICredential).filter(
        AICredential.user_id == current_user.id,
        AICredential.status == "active",
    ).update({"status": "inactive"}, synchronize_session=False)

    try:
        encrypted_api_key, iv, auth_tag = encrypt_api_key(request.api_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc

    credential = AICredential(
        user_id=current_user.id,
        provider=request.provider,
        encrypted_api_key=encrypted_api_key,
        iv=iv,
        auth_tag=auth_tag,
        current_model=default_model,
        status="active",
    )

    db.add(credential)
    db.commit()
    db.refresh(credential)

    return {
        "message": "API key saved successfully",
        "data": _build_ai_credential_response(
            credential, mask_api_key(request.api_key)
        ),
    }


# This endpoint lists all API credentials for the user, including inactive ones, with masked API keys.
@router.get("/api-keys", response_model=ListAICredentialsResponse)
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    credentials = (
        db.query(AICredential)
        .filter(AICredential.user_id == current_user.id)
        .order_by(
            case(
                (AICredential.status == "active", 0),
                else_=1,
            ),
            AICredential.updated_at.desc())
        .all()
    )

    items = []
    for credential in credentials:
        try:
            plain_api_key = decrypt_api_key(
                credential.encrypted_api_key,
                credential.iv,
                credential.auth_tag,
            )
            masked = mask_api_key(plain_api_key)
        except ValueError:
            masked = ""

        items.append(_build_ai_credential_response(credential, masked))

    return {"items": items}


# This endpoint allows changing the current_model for the active credential.
@router.patch("/api-key/current-model", response_model=UpdateCurrentModelResponse)
def update_current_model(
    request: UpdateCurrentModelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    credential = (
        db.query(AICredential)
        .filter(
            AICredential.user_id == current_user.id,
            AICredential.status == "active",
        )
        .order_by(AICredential.updated_at.desc())
        .first()
    )

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active API credential found",
        )

    allowed_model = (
        db.query(AIProviderModel)
        .filter(
            AIProviderModel.provider == credential.provider,
            AIProviderModel.is_active == True,
            AIProviderModel.model_name == request.current_model,
        )
        .first()
    )
    if not allowed_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="current_model is not allowed for this provider or not active",
        )

    credential.current_model = request.current_model
    db.commit()
    db.refresh(credential)

    try:
        plain_api_key = decrypt_api_key(
            credential.encrypted_api_key,
            credential.iv,
            credential.auth_tag,
        )
        masked = mask_api_key(plain_api_key)
    except ValueError:
        masked = ""

    return {
        "message": "Current model updated successfully",
        "data": _build_ai_credential_response(credential, masked),
    }


# This endpoint returns the currently active API credential for the user.
@router.get("/api-key", response_model=AICredentialResponse)
def get_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    credential = (
        db.query(AICredential)
        .filter(
            AICredential.user_id == current_user.id,
            AICredential.status == "active",
        )
        .order_by(AICredential.updated_at.desc())
        .first()
    )

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active API key found",
        )

    try:
        plain_api_key = decrypt_api_key(
            credential.encrypted_api_key,
            credential.iv,
            credential.auth_tag,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt API key",
        ) from exc

    return _build_ai_credential_response(credential, mask_api_key(plain_api_key))


# This endpoint allow users to deactivate all their active credentials.
@router.patch("/api-key/clear-active", response_model=ClearActiveAICredentialResponse)
def clear_active_api_credential(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(AICredential).filter(
        AICredential.user_id == current_user.id,
        AICredential.status == "active",
    ).update({"status": "inactive"}, synchronize_session=False)

    db.commit()

    return {"message": "Active AI credential cleared successfully"}


# This endpoint allows activating an existing credential by its ID. It will deactivate any other active credentials for the user.
@router.patch(
    "/api-key/{credential_id}/activate", response_model=ActivateAICredentialResponse
)
def activate_api_credential(
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    credential = (
        db.query(AICredential)
        .filter(
            AICredential.id == credential_id,
            AICredential.user_id == current_user.id,
        )
        .first()
    )

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI credential not found",
        )

    db.query(AICredential).filter(
        AICredential.user_id == current_user.id,
        AICredential.status == "active",
    ).update({"status": "inactive"}, synchronize_session=False)

    credential.status = "active"
    db.commit()
    db.refresh(credential)

    try:
        plain_api_key = decrypt_api_key(
            credential.encrypted_api_key,
            credential.iv,
            credential.auth_tag,
        )
        masked = mask_api_key(plain_api_key)
    except ValueError:
        masked = ""

    return {
        "message": "AI credential activated successfully",
        "data": _build_ai_credential_response(credential, masked),
    }

# This endpoint allows deleting an existing credential by its ID. 
@router.delete("/api-key/{credential_id}", response_model=DeleteAICredentialResponse)
def delete_api_credential(
    credential_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    credential = (
        db.query(AICredential)
        .filter(
            AICredential.id == credential_id,
            AICredential.user_id == current_user.id,
        )
        .first()
    )

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI credential not found",
        )

    db.delete(credential)
    db.commit()

    return {"message": "AI credential deleted successfully"}

# This endpoint allows changing the current_model for a specific credential by its ID.
@router.patch("/api-key/{credential_id}/current-model", response_model=UpdateCurrentModelResponse)
def update_credential_model(
    credential_id: int,
    request: UpdateCurrentModelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    credential = (
        db.query(AICredential)
        .filter(
            AICredential.id == credential_id,
            AICredential.user_id == current_user.id,
        )
        .first()
    )

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI credential not found",
        )

    allowed_model = (
        db.query(AIProviderModel)
        .filter(
            AIProviderModel.provider == credential.provider,
            AIProviderModel.is_active == True,
            AIProviderModel.model_name == request.current_model,
        )
        .first()
    )
    if not allowed_model:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="current_model is not allowed for this provider or not active",
        )

    credential.current_model = request.current_model
    db.commit()
    db.refresh(credential)

    try:
        plain_api_key = decrypt_api_key(
            credential.encrypted_api_key,
            credential.iv,
            credential.auth_tag,
        )
        masked = mask_api_key(plain_api_key)
    except ValueError:
        masked = ""

    return {
        "message": "Current model updated successfully",
        "data": _build_ai_credential_response(credential, masked),
    }