from datetime import timedelta, datetime, timezone

from app.core.config import settings
from sqlalchemy.orm import Session
from httpx import AsyncClient
import base64
import json
import uuid
from urllib.parse import urlencode
from app.models.user_identity import UserIdentity
from app.models.user import User
from app.models.token import Token
from app.core.security import create_access_token


def get_google_login_url():
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "prompt": "consent",
    }

    state = urlencode(params)
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{state}"
    return auth_url


async def get_google_credentials(code: str, db: Session):
    try:
        token_data = {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        }
        async with AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_data,
            )

        if token_response.status_code != 200:
            raise Exception(f"Failed to exchange code for token: {token_response.text}")

        token_json = token_response.json()
        id_token = token_json.get("id_token")
        encoded_payload = id_token.split(".")[1]
        payload = json.loads(base64.b64decode(encoded_payload + "==").decode("utf-8"))

        # Get user info from the id token payload
        email = payload.get("email")
        sub = payload.get("sub")
        given_name = payload.get("given_name")
        family_name = payload.get("family_name")

        # Get identity provider user record
        identity = (
            db.query(UserIdentity)
            .filter(UserIdentity.provider == "google", UserIdentity.provider_id == sub)
            .first()
        )

        if identity:
            # user have registered before, return the existing user
            user = db.query(User).filter(User.id == identity.user_id).first()
        else:
            # check if user with this email has alredy existed
            user = db.query(User).filter(User.email == email).first()
            if user:
                # Link Google identity to existing user
                new_identity = UserIdentity(
                    user_id=user.id,
                    provider="google",
                    provider_id=sub,
                )
                db.add(new_identity)
                db.commit()
            else:
                # New user, create new user and link Google identity
                try:
                    new_user = User(
                        email=email,
                        name=f"{given_name} {family_name}",
                        passwordhash="",  # No password since it's OAuth
                        email_verified=True,
                    )
                    db.add(new_user)
                    db.flush()

                    new_identity = UserIdentity(
                        user_id=new_user.id,
                        provider="google",
                        provider_id=sub,
                    )
                    db.add(new_identity)
                    db.commit()
                except Exception as e:
                    db.rollback()
                    raise Exception(f"Failed to create user and identity: {str(e)}")

        # Create session for user (generate internal access token and refresh token)
        internal_access_token = create_access_token(data={"sub": email})
        expired_at = datetime.now(timezone.utc) + timedelta(days=7)
        internal_refresh_token = str(uuid.uuid4())
        token_record = Token(
            token=internal_refresh_token,
            user_id=user.id if user else new_user.id,
            expiry_date=expired_at,
        )
        db.add(token_record)
        db.commit()

        return {
            "access_token": internal_access_token,
            "refresh_token": internal_refresh_token,
            "token_type": "bearer",
        }
    except Exception as e:
        raise Exception(f"Error during token exchange: {str(e)}")
