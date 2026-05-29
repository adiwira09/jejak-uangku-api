from database.connect import get_conn

def get_user(telegram_id):
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
            """
            SELECT telegram_id, username, first_name, last_name, is_active, first_seen, last_seen
            FROM jejak_uangku.users
            WHERE telegram_id = %s
            """,
            (telegram_id,)
        )

            row = cursor.fetchone()
            if row is None:
                return None
        
            return {
                "telegram_id": row[0],
                "username": row[1],
                "first_name": row[2],
                "last_name": row[3],
                "is_active": row[4],
                "first_seen": row[5],
                "last_seen": row[6]
            }

def upsert_user(telegram_id, username, first_name, last_name):
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute ("""
                INSERT INTO jejak_uangku.users(
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                    is_active,
                    first_seen,
                    last_seen
                    )
                VALUES (%s, %s, %s, %s, TRUE, NOW(), NOW())
                ON CONFLICT (telegram_id)
            DO UPDATE SET 
                username = EXCLUDED.username, 
                first_name = EXCLUDED.first_name, 
                last_name = EXCLUDED.last_name, 
                is_active = EXCLUDED.is_active, 
                last_seen = EXCLUDED.last_seen
            """, (
                telegram_id,
                username,
                first_name,
                last_name,
            ))

def stop_user_data(telegram_id):
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE jejak_uangku.users
                SET is_active = FALSE,
                    last_seen = NOW()
                WHERE telegram_id = %s
            """, (telegram_id,))
            conn.commit()