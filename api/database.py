"""FastAPI dependency cấp MySQL connection cho một request."""

import logging

from fastapi import HTTPException
from database import get_connection

logger = logging.getLogger("hotel.database")


def get_db():
    connection = None

    try:
        connection = get_connection()
        if not connection.is_connected():
            raise RuntimeError("MySQL connection is not active.")
    except Exception as exc:
        # Keep the real exception in the backend log for diagnosis, while
        # avoiding disclosure of credentials or connection details to clients.
        logger.exception("MYSQL CONNECTION FAILED inside FastAPI get_db")
        raise HTTPException(
            status_code=503,
            detail=(
                "Không thể kết nối MySQL. "
                "Xem lỗi gốc trong Terminal Backend."
            ),
        ) from exc

    try:
        yield connection
    finally:
        if connection is not None:
            try:
                if connection.is_connected():
                    connection.close()
            except Exception:
                logger.exception("MYSQL CONNECTION CLOSE FAILED")
