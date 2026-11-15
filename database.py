import mysql.connector
from mysql.connector import Error


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "dinomtp16",
    "database": "hotel_management_v2",
    "port": 3306,
    "charset": "utf8mb4"
}


def get_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)

        if connection.is_connected():
            return connection

    except Error as error:
        print("Lỗi kết nối MySQL:", error)
        raise


def get_db():
    connection = get_connection()

    try:
        yield connection

    finally:
        if connection and connection.is_connected():
            connection.close()