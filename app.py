from datetime import datetime
import requests

from fastapi import FastAPI

from routes.users import router as users_router
from routes.oauth import router as oauth_router
from routes.spreadsheet import router as spreadsheet_router

from schemas import TransactionPayload

from config import CLIENT_ID, CLIENT_SECRET

from database.spreadsheet_configs_table import get_spreadsheet_config
from database.oauth_tokens_table import (
    get_access_tokens,
    get_refresh_tokens,
    upsert_oauth_tokens
)

app = FastAPI(
    title="Jejak Uangku API Server",
    version="1.0.0"
)

# routes
app.include_router(users_router, prefix="/users", tags=["Users"])
app.include_router(oauth_router, prefix="/oauth", tags=["Oauth"])
app.include_router(spreadsheet_router, prefix="/spreadsheet", tags=["Spreadsheet"])

def refresh_access_token(telegram_id):
    refresh_token = get_refresh_tokens(telegram_id)["refresh_token"]
    
    url = "https://oauth2.googleapis.com/token"

    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    response = requests.post(url, data=payload)
    response.raise_for_status()

    token_data = response.json()

    upsert_oauth_tokens(
        telegram_id=telegram_id,
        access_token=token_data["access_token"],
        refresh_token=None,
        expires_at=token_data.get("expires_in")
    )
    return token_data["access_token"]

def google_request(method, url, telegram_id, **kwargs):
    access_token = get_access_tokens(telegram_id)["access_token"]
    
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {access_token}"
    
    response = requests.request(method, url, headers=headers, **kwargs)
    
    if response.status_code == 401:
        new_access_token = refresh_access_token(telegram_id)
        headers["Authorization"] = f"Bearer {new_access_token}"
        response = requests.request(method, url, headers=headers, **kwargs)
    
    response.raise_for_status()
    return response

def get_sheet_data(telegram_id, spreadsheet_id, sheet_name):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}"
    
    response = google_request("GET", url, telegram_id)
    data = response.json()
    return data.get("values", [])

def check_and_add_header(telegram_id, spreadsheet_id, sheet_name):

    existing_data = get_sheet_data(telegram_id, spreadsheet_id, sheet_name)
    
    # jika sheet kosong, tambahkan header
    if not existing_data:
        header_row = [["Tanggal", "Item", "Nominal"]]
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}!A:C:append"
        
        response =  google_request(
            "POST",
            url,
            telegram_id,
            headers={"Content-Type": "application/json"},
            json={"values": header_row},
            params={"valueInputOption": "USER_ENTERED"}
        )

def write_to_sheet(rows, telegram_id, spreadsheet_id, sheet_name):

    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}!A:C:append"
    response = google_request(
        "POST",
        url,
        telegram_id,
        headers={"Content-Type": "application/json"},
        json={"values": rows},
        params={"valueInputOption": "USER_ENTERED"}
    )
    return response.json()

def get_last_date(telegram_id, spreadsheet_id, sheet_name):
    data = get_sheet_data(telegram_id, spreadsheet_id, sheet_name)

    if len(data) <= 1:
        return None

    for row in reversed(data[1:]):
        if len(row) > 0 and row[0].strip():
            return row[0]
    
    return None
    
@app.post("/add-transaction/")
def add_transaction(data: TransactionPayload, group_by_date: bool = True):

    spreadsheet_config = get_spreadsheet_config(data.telegram_id)
    if spreadsheet_config is None:
        return {
            "status": "error",
            "message": "Spreadsheet config not found for this telegram_id"
        }
    
    spreadsheet_id = spreadsheet_config["spreadsheet_id"]
    sheet_name = spreadsheet_config["sheet_name"]

    check_and_add_header(data.telegram_id, spreadsheet_id, sheet_name)

    today = datetime.now().strftime("%d-%m-%Y")
    rows = []

    if group_by_date:
        last_date = get_last_date(data.telegram_id, spreadsheet_id, sheet_name)
        first_date = today if last_date != today else "" # hari sama, cell Tanggal kosong

        for i, trx in enumerate(data.transactions):
            rows.append([
                first_date if i == 0 else "",
                trx.item,
                trx.amount
            ])
    else:
        for trx in data.transactions:
            rows.append([
                today,
                trx.item,
                trx.amount
            ])

    result = write_to_sheet(rows, data.telegram_id, spreadsheet_id, sheet_name)

    return {
        "status": "success",
        "inserted": len(rows),
        "google_response": result
    }