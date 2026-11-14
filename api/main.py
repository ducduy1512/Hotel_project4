
# api/main.py

from fastapi import FastAPI, HTTPException, Depends
from mysql.connector import Error

from api.database import get_db
from api.routers import customers, room_types, rooms, bookings, peak_seasons, services, payments, invoices, reports
app = FastAPI(
    title="Hotel Booking Management API",
    description="REST API for Hotel Booking Management System",
    version="1.0.0"
)

app.include_router(customers.router)
app.include_router(room_types.router)
app.include_router(rooms.router)
app.include_router(bookings.router)
app.include_router(peak_seasons.router)
app.include_router(services.router)
app.include_router(payments.router)
app.include_router(invoices.router)
app.include_router(reports.router)
@app.get("/")
def home():
    return {
        "message": "Hotel Booking Management API is running",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {
        "status": "OK",
        "message": "FastAPI is running"
    }


@app.get("/health/db")
def database_health_check(db=Depends(get_db)):
    try:
        cursor = db.cursor()
        cursor.execute("SELECT DATABASE()")
        result = cursor.fetchone()
        cursor.close()

        database_name = result[0] if result else None

        if database_name != "hotel_management":
            raise HTTPException(
                status_code=500,
                detail=f"Đang kết nối nhầm database: {database_name}"
            )

        return {
            "status": "OK",
            "database": database_name,
            "message": "Kết nối MySQL thành công"
        }

    except HTTPException:
        raise

    except Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi truy vấn MySQL: {str(e)}"
        )
