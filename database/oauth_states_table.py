from database.connect import get_conn

from fastapi import HTTPException

def get_oauth_states_data(state):
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT telegram_id
                    FROM jejak_uangku.oauth_states
                    WHERE state = %s
                    """,
                    (state,)
                )

                row = cursor.fetchone()

                if row is None:
                    raise HTTPException(status_code=404, detail="State not found")
                
                return {
                    "telegram_id": row[0]
                }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
    
def insert_oauth_state(telegram_id, state):
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO jejak_uangku.oauth_states (telegram_id, state)
                VALUES (%s, %s)
                """,
                (telegram_id, state)
            )
            conn.commit()

def delete_oauth_state(state):
    try:
        with get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM jejak_uangku.oauth_states
                    WHERE state = %s
                    """,
                    (state,)
                )
                conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")        