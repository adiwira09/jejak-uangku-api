from fastapi import APIRouter, HTTPException

from schemas import SpreadsheetConfigRequest
from database.spreadsheet_configs_table import (
    get_spreadsheet_config, 
    upsert_spreadsheet_config, 
    delete_spreadsheet_config
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

    except Exception as e:
        # logging.exception(f"Error inserting/updating spreadsheet config: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/{telegram_id}")
def get_spreadsheet_config(telegram_id: str):
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
    except Exception as e:
        # logging.exception(f"Error retrieving spreadsheet config: {str(e)}")
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
    except Exception as e:
        # logging.exception(f"Error deleting spreadsheet config: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )