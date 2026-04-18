from typing import Optional

from sqlalchemy.orm import Session

from app.models.ai_credential import AICredential
from app.utils.encryption import decrypt_api_key


def get_active_ai_credential_for_user(
    db: Session,
    user_id: int,
) -> Optional[AICredential]:
    return (
        db.query(AICredential)
        .filter(
            AICredential.user_id == user_id,
            AICredential.status == "active",
        )
        .order_by(AICredential.updated_at.desc())
        .first()
    )


def resolve_ai_headers_for_user(
    db: Session,
    user_id: int,
    model: Optional[str] = None,
) -> dict[str, str]:
    credential = get_active_ai_credential_for_user(db, user_id)
    if not credential:
        return {}

    resolved_model = model or credential.current_model
    decrypted_key = decrypt_api_key(
        credential.encrypted_api_key,
        credential.iv,
        credential.auth_tag,
    )

    headers = {
        "X-AI-Provider": credential.provider,
        "X-AI-API-Key": decrypted_key,
    }

    if resolved_model:
        headers["X-AI-Model"] = resolved_model

    return headers
