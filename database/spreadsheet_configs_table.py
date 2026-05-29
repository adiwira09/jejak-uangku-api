from database.connect import get_conn
from fastapi import HTTPException

def get_spreadsheet_config(telegram_id: str):
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT spreadsheet_id, sheet_name
                FROM jejak_uangku.spreadsheet_configs
                WHERE telegram_id = %s
                """,
                (telegram_id,)
            )

            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="Spreadsheet config not found for this user"
                )

            return {
                "spreadsheet_id": row[0],
                "sheet_name": row[1]
            }
def upsert_spreadsheet_config(telegram_id: str, spreadsheet_id: str, sheet_name: str):
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO jejak_uangku.spreadsheet_configs (telegram_id, spreadsheet_id, sheet_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (telegram_id) DO UPDATE
                SET spreadsheet_id = EXCLUDED.spreadsheet_id,
                    sheet_name = EXCLUDED.sheet_name
                """,
                (telegram_id, spreadsheet_id, sheet_name)
            )
            conn.commit()
            
def delete_spreadsheet_config(telegram_id: str):
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM jejak_uangku.spreadsheet_configs
                WHERE telegram_id = %s
                """,
                (telegram_id,)
            )
            conn.commit()
            return cursor.rowcount