from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from mysql.connector import Error

from api.database import get_db
from database import DB_CONFIG
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

DATABASE_NAME = DB_CONFIG["database"]
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


FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
def home():
    """Serve the HTML5 web interface; REST endpoints remain unchanged under /api."""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


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
        cursor.execute("SELECT DATABASE()")
        row = cursor.fetchone()
        current_database = row[0] if row else None

        if current_database != DATABASE_NAME:
            raise HTTPException(
                status_code=503,
                detail=(
                    f"API đang kết nối database '{current_database}', "
                    f"nhưng project yêu cầu '{DATABASE_NAME}'."
                ),
            )

        cursor.execute(
            """
            SELECT TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
            """,
            (DATABASE_NAME,),
        )
        existing_tables = {item[0] for item in cursor.fetchall()}
        missing_erd_tables = sorted(REQUIRED_ERD_TABLES - existing_tables)
        missing_support_tables = sorted(REQUIRED_SUPPORT_TABLES - existing_tables)

        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA = %s",
            (DATABASE_NAME,),
        )
        trigger_count = cursor.fetchone()[0]
        cursor.execute(
            """SELECT COUNT(*) FROM information_schema.ROUTINES
               WHERE ROUTINE_SCHEMA = %s AND ROUTINE_TYPE = 'PROCEDURE'""",
            (DATABASE_NAME,),
        )
        procedure_count = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.VIEWS WHERE TABLE_SCHEMA = %s",
            (DATABASE_NAME,),
        )
        view_count = cursor.fetchone()[0]

        problems = {}
        if missing_erd_tables:
            problems["missing_erd_tables"] = missing_erd_tables
        if missing_support_tables:
            problems["missing_support_tables"] = missing_support_tables
        if trigger_count != 15:
            problems["trigger_count"] = {"actual": trigger_count, "expected": 15}
        if procedure_count != 18:
            problems["procedure_count"] = {"actual": procedure_count, "expected": 18}
        if view_count != 10:
            problems["view_count"] = {"actual": view_count, "expected": 10}

        if problems:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Database chưa hoàn chỉnh theo bộ SQL Hotel.",
                    "database": current_database,
                    "problems": problems,
                },
            )

        return {
            "status": "OK",
            "database": current_database,
            "erd_tables_found": len(REQUIRED_ERD_TABLES),
            "support_tables_found": len(REQUIRED_SUPPORT_TABLES),
            "payment_gateway": "QR / SePay webhook tables found",
            "triggers": trigger_count,
            "stored_procedures": procedure_count,
            "views": view_count,
            "message": "MySQL đã có đủ bảng, Trigger, Stored Procedure và View của Hotel.",
        }

    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Không kiểm tra được MySQL: {exc}",
        ) from exc
    finally:
        if cursor is not None:
            cursor.close()
