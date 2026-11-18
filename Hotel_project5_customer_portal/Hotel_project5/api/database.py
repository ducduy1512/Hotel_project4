"""FastAPI dependency cấp MySQL connection cho một request."""

from fastapi import HTTPException

from database import get_connection


def get_db():
    connection = None
    try:
        connection = get_connection()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Không thể kết nối MySQL. Kiểm tra MySQL Server và cấu hình "
                "DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME trong file .env."
            ),
        ) from exc

    try:
        yield connection
    finally:
        if connection and connection.is_connected():
            connection.close()
