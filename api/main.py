from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from api.database import get_db
from database import DB_CONFIG, Error, initialize_database
from api.routers.auth import require_admin, require_customer
from api.routers import (
    auth,
    bookings,
    customers,
    invoices,
    payments,
    peak_seasons,
    reports,
    room_types,
    rooms,
    services,
    customer_portal,
    payment_gateway,
)

DATABASE_NAME = Path(DB_CONFIG["database"]).name
initialize_database()
REQUIRED_ERD_TABLES = {
    "loaiphong", "phong", "khach", "booking",
    "dichvu", "muacaodiem", "pay", "hoadon",
}
REQUIRED_SUPPORT_TABLES = {"users", "payment_qr", "sepay_webhook_events"}

app = FastAPI(
    title="Hotel Booking Management API",
    description="REST API for the Hotel Management ERD database",
    version="2.0.0",
)

# Authentication endpoints remain public where appropriate (register/login).
app.include_router(auth.router)

# Customer-facing portal: every endpoint is scoped to the authenticated customer.
app.include_router(customer_portal.router, dependencies=[Depends(require_customer)])

# Public callback from the payment provider. This endpoint performs its own HMAC/API-key check.
app.include_router(payment_gateway.router)

# Every management endpoint requires an authenticated ADMIN account.
# CUSTOMER accounts can register/login but cannot access the desktop admin API.
for module in (
    customers,
    room_types,
    rooms,
    bookings,
    peak_seasons,
    services,
    payments,
    invoices,
    reports,
):
    app.include_router(module.router, dependencies=[Depends(require_admin)])


PROJECT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_DIR / "frontend"
IMAGES_DIR = PROJECT_DIR / "images"

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
# Room-type photos are stored outside frontend/ in the project-level images/ folder.
# Expose them at /images/<filename> so the Customer Portal can load them reliably.
app.mount("/images", StaticFiles(directory=str(IMAGES_DIR)), name="room-images")


@app.get("/", include_in_schema=False)
def home():
    """Serve the HTML5 interface without allowing an old cached entrypoint."""
    return FileResponse(
        str(FRONTEND_DIR / "index.html"),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/api-info", include_in_schema=False)
def api_info():
    return {
        "message": "Hotel Booking Management API is running",
        "database": DATABASE_NAME,
        "docs": "/docs",
        "frontend": "/",
    }


@app.get("/health")
def health_check():
    return {"status": "OK", "message": "FastAPI is running"}


@app.get("/health/db")
def database_health_check(db=Depends(get_db)):
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table','view','trigger')")
        objects = cursor.fetchall()
        tables = {row[0] for row in objects if row[1] == "table"}
        views = {row[0] for row in objects if row[1] == "view"}
        triggers = {row[0] for row in objects if row[1] == "trigger"}
        required = {
            "loaiphong", "phong", "khach", "booking", "dichvu", "muacaodiem",
            "phong_muacaodiem", "pay", "hoadon", "payment_qr", "sepay_webhook_events", "users",
        }
        missing = sorted(required - tables)
        if missing:
            raise HTTPException(status_code=503, detail={"message": "SQLite database thiếu bảng bắt buộc", "missing_tables": missing})
        cursor.execute("PRAGMA foreign_key_check")
        violations = cursor.fetchall()
        if violations:
            raise HTTPException(status_code=503, detail={"message": "Có lỗi khóa ngoại", "violations": violations[:10]})
        return {
            "status": "OK", "engine": "SQLite", "database": DATABASE_NAME,
            "database_file": str(DB_CONFIG["database"]),
            "tables": len(required), "views": len(views), "triggers": len(triggers),
            "stored_procedures": "Đã chuyển nghiệp vụ cần thiết sang Python service layer",
            "message": "SQLite đã được khởi tạo và kiểm tra thành công.",
        }
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=503, detail=f"Không kiểm tra được SQLite: {exc}") from exc
    finally:
        if cursor is not None:
            cursor.close()
