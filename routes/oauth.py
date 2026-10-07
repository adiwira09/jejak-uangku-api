import logging
import requests

from fastapi import APIRouter, Request
from fastapi.responses import Response
from fastapi import HTTPException

from config import (
    CLIENT_ID, 
    CLIENT_SECRET, 
    REDIRECT_URI
)

from schemas import OAuthStateRequest
from database.oauth_tokens_table import (
    upsert_oauth_tokens,
    get_oauth_tokens_data
)
from database.oauth_states_table import (
    get_oauth_states_data, 
    delete_oauth_state,
    insert_oauth_state
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

router = APIRouter()

@router.get("/callback")
def oauth_callback(request: Request, state: str, code: str):

    code = request.query_params.get("code")
    state = request.query_params.get("state")

    state_data = get_oauth_states_data(state)

    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid state")

    telegram_id = state_data["telegram_id"]
    try:
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code"
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            },
            timeout=10
        )

        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch token from Google")

        token = response.json()

    except requests.RequestException as e:
        logging.exception(f"Request to Google failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Request to Google failed")
    
    access_token = token.get("access_token")
    refresh_token = token.get("refresh_token")
    expires_at = token.get("expires_in")
    error = token.get("error")

    if error or not access_token or not refresh_token:
        raise HTTPException(status_code=400, detail="Invalid token response from Google")
    
    try:
        upsert_oauth_tokens(
            telegram_id=telegram_id, 
            access_token=access_token, 
            refresh_token=refresh_token, 
            expires_at=expires_at
        )
        delete_oauth_state(state)

    except Exception:
        logging.exception(f"Error saving OAuth tokens")
        raise HTTPException(status_code=500, detail="Failed to save OAuth tokens")

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Jejak Uangku</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body>
        <h2>Google Berhasil Terhubung</h2>

        <p>
            Akun Google Anda berhasil terhubung dengan Jejak Uangku.
        </p>

        <p>
            Silakan kembali ke Telegram untuk melanjutkan setup.
        </p>
    </body>
    </html>
    """

    return Response(
        content=html_content,
        media_type="text/html",
        status_code=200
    )
    
@router.get("/token/status/{telegram_id}")
def get_status_google(telegram_id: str):
    try:
        data = get_oauth_tokens_data(telegram_id)
        if data is None:
            raise HTTPException(status_code=404, detail="Google account not connected")

        return {
            "telegram_id": telegram_id,
            "status": "connected"
        }
    except HTTPException:
        raise

    except Exception:
        logging.exception(f"Error fetching token status")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error"
        )
    
@router.post("/states/insert")
def insert_states(data: OAuthStateRequest):
    try:
        insert_oauth_state(data.telegram_id, data.state)
        return {"status": "ok"}
    
    except Exception:
        logging.exception(f"Error inserting OAuth state")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error"
        )