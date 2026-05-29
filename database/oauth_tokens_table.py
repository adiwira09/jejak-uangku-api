from database.connect import get_conn

def get_oauth_tokens_data(telegram_id):
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT access_token, refresh_token, expires_at
                FROM jejak_uangku.oauth_tokens
                WHERE telegram_id = %s
                """,
                (telegram_id,)
            )

            row = cursor.fetchone()
            if row is None:
                return None

            return {
                "access_token": row[0],
                "refresh_token": row[1],
                "expires_at": row[2]
            }

def get_access_tokens(telegram_id):
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT access_token
                FROM jejak_uangku.oauth_tokens
                WHERE telegram_id = %s
                """,
                (telegram_id,)
            )

            row = cursor.fetchone()

            if row is None:
                return None
            
            return {
                "access_token": row[0]
            }

def get_refresh_tokens(telegram_id):
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT refresh_token
                FROM jejak_uangku.oauth_tokens
                WHERE telegram_id = %s
                """,
                (telegram_id,)
            )

            row = cursor.fetchone()

            if row is None:
                return None
            
            return {
                "refresh_token": row[0]
            }

def upsert_oauth_tokens(telegram_id, access_token, refresh_token, expires_at, google_email=None):
    with get_conn() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO jejak_uangku.oauth_tokens 
                (
                    telegram_id,
                    google_email,
                    access_token, 
                    refresh_token, 
                    expires_at
                )
                VALUES (%s, %s, %s, %s, NOW() + (%s * interval '1 second'))
                ON CONFLICT (telegram_id) DO UPDATE
                SET access_token = EXCLUDED.access_token,
                    refresh_token = COALESCE(EXCLUDED.refresh_token, 
                                                      oauth_tokens.refresh_token),
                    expires_at = EXCLUDED.expires_at
                """,
                (telegram_id, google_email, access_token, refresh_token, expires_at)
            )
            conn.commit()