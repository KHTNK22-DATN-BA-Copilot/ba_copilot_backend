from app.schemas.auth import CredentialsRequest
from app.core.database import get_db
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from fastapi.responses import RedirectResponse
from app.services.auth.google import get_google_login_url, get_google_credentials


router = APIRouter()


# return the URL to redirect the user to for login
@router.get("/{strategy}/login")
def login(strategy: str):
    auth_url = ""
    try:
        if strategy == "google":
            auth_url = get_google_login_url()
        else:
            raise Exception("Unsupported authentication strategy")
        return RedirectResponse(url=auth_url)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Handle the callback from the OAuth provider
@router.post("/{strategy}/credentials")
async def get_credentials(
    strategy: str, body: CredentialsRequest, db: Session = Depends(get_db)
):
    try:
        if strategy == "google":
            credentials = await get_google_credentials(body.code, db)
            return credentials
        else:
            raise Exception("Unsupported authentication strategy")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
