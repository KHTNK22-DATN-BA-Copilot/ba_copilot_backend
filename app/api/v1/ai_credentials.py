from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.ai_credential import AICredential
from app.models.user import User
from app.schemas.ai_credential import (
    ActivateAICredentialResponse,
    AICredentialResponse,
    ListAICredentialsResponse,
    ProviderModelsListResponse,
    ProviderModelsResponse,
    SaveAICredentialRequest,
    SaveAICredentialResponse,
    UpdateCurrentModelRequest,
    UpdateCurrentModelResponse,
)
from app.utils.encryption import decrypt_api_key, encrypt_api_key, mask_api_key

router = APIRouter()


FIXED_PROVIDER_MODELS = {
    "openai": [
        "gpt-4.1",
        "gpt-4.1-mini",
        "gpt-4o",
        "gpt-4o-mini",
    ],
    "openrouter": [
        "openai/gpt-4o-mini",
        "anthropic/claude-3.5-haiku",
        "meta-llama/llama-3.1-8b-instruct",
        "nvidia/nemotron-3-nano-30b-a3b:free",
    ],
    "google": [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash",
    ],
    "anthropic": [
        "claude-haiku-4-0",
        "claude-sonnet-4-0",
        "claude-opus-4-0",
    ],
}


def _build_ai_credential_response(
    credential: AICredential, masked_api_key: str
) -> dict:
    return {
        "id": credential.id,
        "provider": credential.provider,
        "status": credential.status,
        "current_model": credential.current_model,
        "models_json": credential.models_json or [],
        "masked_api_key": masked_api_key,
        "updated_at": credential.updated_at,
    }


@router.get("/models", response_model=ProviderModelsListResponse)
def get_all_provider_models():
    items = []
    for provider, models in FIXED_PROVIDER_MODELS.items():
        items.append(
            {
                "provider": provider,
                "models": models,
                "default_model": models[0] if models else None,
            }
        )
    return {"items": items}


@router.get("/models/{provider}", response_model=ProviderModelsResponse)
def get_provider_models(provider: str):
    normalized_provider = provider.strip().lower()
    models = FIXED_PROVIDER_MODELS.get(normalized_provider)
    if not models:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found in fixed model catalog",
        )

    return {
        "provider": normalized_provider,
        "models": models,
        "default_model": models[0] if models else None,
    }


@router.post("/api-key", response_model=SaveAICredentialResponse)
def save_api_key(
    request: SaveAICredentialRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fixed_models = FIXED_PROVIDER_MODELS.get(request.provider)
    if not fixed_models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported provider for fixed model catalog",
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
        models_json=fixed_models,
        current_model=fixed_models[0],
        status="active",
    )

    db.add(credential)
    db.commit()
    db.refresh(credential)

    try:
        masked = mask_api_key(
            decrypt_api_key(
                credential.encrypted_api_key, credential.iv, credential.auth_tag
            )
        )
    except ValueError:
        masked = ""

    return {
        "message": "API key saved successfully",
        "data": _build_ai_credential_response(credential, masked),
    }


@router.get("/api-keys", response_model=ListAICredentialsResponse)
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    credentials = (
        db.query(AICredential)
        .filter(AICredential.user_id == current_user.id)
        .order_by(AICredential.updated_at.desc())
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

    allowed_models = credential.models_json or []
    if request.current_model not in allowed_models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="current_model is not allowed for the active credential",
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

    return {
        **_build_ai_credential_response(credential, mask_api_key(plain_api_key)),
    }
