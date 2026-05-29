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
        raise HTTPException(status_code=500, detail=f"Request to Google failed: {str(e)}")
    
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

    return Response(
        content="""
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login Berhasil</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f4f6f9;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        .card {
            background: #ffffff;
            padding: 40px 30px;
            border-radius: 24px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
            text-align: center;
            max-width: 400px;
            width: 100%;
        }
        .icon-success {
            width: 64px;
            height: 64px;
            background-color: #e6f7ed;
            color: #2ec4b6;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
            font-size: 32px;
            font-weight: bold;
        }
        h2 {
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 12px;
            color: #1a1a1a;
        }
        p {
            font-size: 15px;
            color: #666;
            line-height: 1.5;
            margin-bottom: 8px;
        }
        .highlight {
            color: #0088cc;
            font-weight: 600;
        }
        .timer-container {
            margin: 32px 0 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }
        /* Animasi lingkaran timer 3 detik */
        .countdown-circle {
            width: 40px;
            height: 40px;
            border: 3px solid #f0f0f0;
            border-top: 3px solid #0088cc;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .btn-telegram {
            display: inline-block;
            width: 100%;
            background-color: #0088cc;
            color: #ffffff;
            text-decoration: none;
            padding: 14px;
            border-radius: 12px;
            font-weight: 600;
            font-size: 15px;
            transition: background-color 0.2s;
            margin-top: 10px;
        }
        .btn-telegram:active {
            background-color: #006699;
        }
    </style>
</head>
<body>

    <div class="card">
        <div class="icon-success">✓</div>
        
        <h2>Login Berhasil</h2>
        <p>Akun Google Anda telah terhubung dengan <span class="highlight">Jejak Uangku</span>.</p>
        
        <div class="timer-container">
            <div class="countdown-circle"></div>
            <p style="font-size: 13px; color: #999;">Mengalihkan kembali ke Telegram dalam <span id="countdown">3</span> detik...</p>
        </div>

        <a href="tg://resolve?domain=jejak_uangku_bot" class="btn-telegram">Kembali ke Telegram</a>
    </div>

    <script>
        let seconds = 3;
        const countdownEl = document.getElementById('countdown');
        const telegramUrl = "tg://resolve?domain=jejak_uangku_bot";

        const interval = setInterval(() => {
            seconds--;
            countdownEl.textContent = seconds;
            
            if (seconds <= 0) {
                clearInterval(interval);
                window.location.href = telegramUrl;
            }
        }, 1000);

        // Trigger redirect instan saat page load selesai diluar info text pembantu
        setTimeout(() => {
            window.location.href = telegramUrl;
        }, 3000);
    </script>

</body>
</html>
""",
media_type="text/html",
status_code=200
    )  
    
@router.get("/token/status/{telegram_id}")
def get_status_google(telegram_id: str):
    try:
        data = get_oauth_tokens_data(telegram_id)
        if data is None:
            raise HTTPException(status_code=404, detail="User not found")

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