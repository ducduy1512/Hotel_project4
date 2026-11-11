
import mysql.connector
from mysql.connector import Error

# Cấu hình kết nối MySQL
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "dinomtp16",
    "database": "hotel_management",
    "port": 3306
}


def get_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)

        if connection.is_connected():
            return connection

    except Error as e:
        print("Lỗi kết nối MySQL:", e)

    return None


def test_connection():
    connection = get_connection()

    if connection:
        print("KẾT NỐI MYSQL THÀNH CÔNG!")

        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        database_name = cursor.fetchone()

        print("Database đang sử dụng:", database_name[0])

        cursor.close()
        connection.close()

    else:
        print("KẾT NỐI MYSQL THẤT BẠI!")


if __name__ == "__main__":
    test_connection()
