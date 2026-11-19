"""Cấu hình kết nối MySQL dùng chung cho FastAPI."""

import os
from pathlib import Path

import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Nạp .env ở thư mục gốc project, không ghi thông tin đăng nhập vào mã nguồn.
load_dotenv(Path(__file__).resolve().parent / ".env")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "hotel_management_erd"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "charset": "utf8mb4",
    "connection_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
}


def get_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
        raise RuntimeError("MySQL connection was not established.")
    except Error as error:
        raise RuntimeError(f"Không thể kết nối MySQL: {error}") from error


def get_db():
    connection = get_connection()
    try:
        yield connection
    finally:
        if connection and connection.is_connected():
            connection.close()
