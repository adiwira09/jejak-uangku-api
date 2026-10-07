import logging
import requests

from fastapi import APIRouter, HTTPException

from schemas import SpreadsheetConfigRequest
from database.spreadsheet_configs_table import (
    get_spreadsheet_config, 
    upsert_spreadsheet_config, 
    delete_spreadsheet_config
)

from database.oauth_tokens_table import get_oauth_tokens_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

router = APIRouter()

@router.post("/insert")
def insert(data: SpreadsheetConfigRequest):
    try:
        upsert_spreadsheet_config(
            telegram_id=data.telegram_id,
            spreadsheet_id=data.spreadsheet_id,
            sheet_name=data.sheet_name
        )

        return {
            "status": "success",
            "message": "Spreadsheet config saved successfully",
            "spreadsheet_id": data.spreadsheet_id,
            "sheet_name": data.sheet_name
        }

    except Exception:
        logging.exception(f"Error inserting/updating spreadsheet config")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/{telegram_id}")
def get_config(telegram_id: str):
    try:
        spreadsheet_config = get_spreadsheet_config(telegram_id)
        if spreadsheet_config is None:
            raise HTTPException(
                status_code=404,
                detail="Spreadsheet config not found for this user"
            )
        return spreadsheet_config
    
    except HTTPException:
        raise

    except Exception:
        logging.exception(f"Error retrieving spreadsheet config")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.delete("/{telegram_id}")
def delete_config(telegram_id: str):
    try:
        deleted_rows = delete_spreadsheet_config(telegram_id)

        if not deleted_rows:
            raise HTTPException(
                status_code=404,
                detail="Spreadsheet config not found for this user"
            )

        return {
            "status": "success",
            "message": "Spreadsheet config deleted successfully"
        }
    
    except HTTPException:
        raise

    except Exception:
        logging.exception(f"Error deleting spreadsheet config")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/sheets/{telegram_id}/{spreadsheet_id}")
def get_sheets(telegram_id: str, spreadsheet_id: str):
    try:
        oauth_tokens = get_oauth_tokens_data(telegram_id)
        if oauth_tokens is None:
            raise HTTPException(
                status_code=404,
                detail="Google account not connected"
            )

        access_token = oauth_tokens["access_token"]
        if not access_token:
            raise HTTPException(
                status_code=401,
                detail="Google access token not found"
            )

        # get spreadsheet metadata from Google Sheets API
        response = requests.get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}",
            params={
                "fields": (
                    "spreadsheetId,"
                    "properties.title,"
                    "sheets.properties"
                )
            },
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            timeout=10
        )

        if response.status_code == 403:
            raise HTTPException(
                status_code=403,
                detail="No access to this spreadsheet"
            )

        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="Spreadsheet not found"
            )

        if response.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Google access token expired"
            )

        response.raise_for_status()

        data = response.json()

        sheets = []

        for sheet in data.get("sheets", []):
            properties = sheet.get("properties", {})

            sheets.append({
                "sheet_id": properties.get("sheetId"),
                "title": properties.get("title")
            })

        return {
            "spreadsheet_id": data.get("spreadsheetId"),
            "spreadsheet_title": data.get("properties", {}).get("title"),
            "sheets": sheets
        }

    except HTTPException:
        raise

    except requests.exceptions.RequestException:
        logging.exception("Error requesting Google Sheets API")
        raise HTTPException(
            status_code=502,
            detail="Failed to communicate with Google Sheets API"
        )

    except Exception:
        logging.exception("Error retrieving spreadsheet sheets")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )