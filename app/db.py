import os
import psycopg
from psycopg.rows import dict_row

from dotenv import load_dotenv
load_dotenv()

def get_db_connection():
    """Create and return a PostgreSQL connection to Supabase."""

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL belum diatur di environment.")

    return psycopg.connect(
        database_url,
        row_factory=dict_row,
        connect_timeout=10
    )


def test_database_connection():
    """Test connection to Supabase PostgreSQL."""

    connection = None

    try:
        connection = get_db_connection()

        with connection.cursor() as cursor:
            cursor.execute("SELECT version() AS version")
            result = cursor.fetchone()

        return True, f"Connected to Supabase PostgreSQL: {result['version']}"

    except Exception as error:
        return False, f"Database connection error: {error}"

    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    ok, message = test_database_connection()
    print(message)
