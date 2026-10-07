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

    html_content = """
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>Jejak Uangku</title>

        <style>
            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                min-height: 100vh;

                display: flex;
                align-items: center;
                justify-content: center;

                padding: 24px;

                background: #f7f8fa;
                color: #171717;

                font-family:
                    -apple-system,
                    BlinkMacSystemFont,
                    "Segoe UI",
                    Roboto,
                    Helvetica,
                    Arial,
                    sans-serif;
            }

            .card {
                width: 100%;
                max-width: 400px;

                padding: 32px;

                background: #ffffff;

                border: 1px solid #e5e7eb;
                border-radius: 16px;

                text-align: center;
            }

            h1 {
                margin: 0;

                font-size: 24px;
                line-height: 1.3;
                font-weight: 650;

                letter-spacing: -0.3px;
            }

            .description {
                margin: 12px 0 0;

                color: #6b7280;

                font-size: 15px;
                line-height: 1.6;
            }

            .button {
                display: block;

                width: 100%;

                margin-top: 28px;
                padding: 13px 16px;

                border-radius: 10px;

                background: #229ed9;
                color: #ffffff;

                font-size: 15px;
                font-weight: 600;

                text-decoration: none;

                transition: background-color 0.15s ease;
            }

            .button:hover {
                background: #168dcc;
            }

            .hint {
                margin: 16px 0 0;

                color: #9ca3af;

                font-size: 13px;
                line-height: 1.5;
            }

            @media (max-width: 480px) {
                body {
                    padding: 16px;
                }

                .card {
                    padding: 28px 22px;
                }

                h1 {
                    font-size: 22px;
                }
            }
        </style>
    </head>
    <body>
        <main class="card">
            <h1>Google Berhasil Terhubung</h1>
            <p class="description">Akun Google Anda berhasil terhubung dengan Jejak Uangku</p>
            <a class="button" href="https://t.me/jejak_uangku_bot">Kembali ke Telegram</a>
            <p class="hint">
                Setelah kembali ke Telegram, tekan
                <strong>“Saya Sudah Login”</strong>
                untuk melanjutkan
            </p>
        </main>
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