
# api/database.py

from database import get_connection


def get_db():
    """
    Dependency dùng để cấp kết nối MySQL cho các API.
    Mỗi request sử dụng một kết nối và đóng kết nối sau khi xử lý.
    """
    connection = get_connection()

    if connection is None:
        raise RuntimeError("Không thể kết nối đến MySQL.")

    try:
        yield connection
    finally:
        if connection.is_connected():
            connection.close()
