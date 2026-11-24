"""FastAPI dependency for the embedded SQLite database."""
from database import get_connection

def get_db():
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()
