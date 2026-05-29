import psycopg
import config

def get_conn():
    try:
        conn = psycopg.connect(
            host=config.DB_HOST,
            port=config.DB_PORT,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        return conn
    except psycopg.Error as e:
        # logging.exception("Database connection error")
        raise Exception("Database connection error") from e

def main():
    conn = get_conn()
    print("Database connection successful!")
    conn.close()

if __name__ == "__main__":
    main()
    