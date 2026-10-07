import logging

from fastapi import APIRouter, HTTPException

from database.users_table import (
    get_user,
    upsert_user,
    stop_user_data
)
from schemas import User

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

router = APIRouter()

@router.get("/{telegram_id}")
def get_user_data(telegram_id: str):
    try:
        user_data = get_user(telegram_id)

        if user_data is None:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        return user_data
    
    except HTTPException:
        raise

    except Exception:
        logging.exception(f"Error fetching user data")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error"
        )
    
@router.post("/upsert")
def upsert(user: User):
    try:
        user_data = get_user(user.telegram_id)
        if user_data is None:
            state = "new_user"
        else:
            state = (
                "reactivated" if not user_data["is_active"] else "returning_user"
            )

        upsert_user(
            telegram_id=user.telegram_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

        return {"status": "ok", "state": state}
    
    except Exception:
        logging.exception(f"Error inserting user data")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error"
        )

@router.post("/stop/{telegram_id}")
def stop(telegram_id: str):
    try:
        user_data = get_user(telegram_id)

        if user_data is None:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        if not user_data["is_active"]:
            return {"state": "already_stopped"}
        
        stop_user_data(telegram_id)
        return {"state": "stopped"}
    
    except HTTPException:
        raise
    
    except Exception:
        logging.exception(f"Error stopping user data")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error"
        )
    