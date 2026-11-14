
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date
from typing import Optional

from api.database import get_db


router = APIRouter(
    prefix="/api/payments",
    tags=["Payments"]
)


# =========================
# CONSTANTS
# =========================

PAYMENT_METHODS = [
    "TIEN_MAT",
    "CHUYEN_KHOAN",
    "THE"
]

PAYMENT_STATUSES = [
    "CHO_THANH_TOAN",
    "THANH_CONG",
    "THAT_BAI",
    "HOAN_TIEN"
]


# =========================
# SCHEMAS
# =========================

class PaymentCreate(BaseModel):
    booking_id: int = Field(..., gt=0)
    ngay_thanh_toan: date
    so_tien: Decimal = Field(..., gt=0)
    method: str
    status: str = "CHO_THANH_TOAN"


class PaymentUpdate(BaseModel):
    ngay_thanh_toan: Optional[date] = None
    so_tien: Optional[Decimal] = Field(None, gt=0)
    method: Optional[str] = None
    status: Optional[str] = None


# =========================
# HELPER FUNCTIONS
# =========================

def get_payment_by_id(cursor, payment_id: int):
    cursor.execute("""
        SELECT
            p.id,
            p.booking_id,
            p.ngay_thanh_toan,
            p.so_tien,
            p.method,
            p.status,
            b.phong_id,
            b.khach_id,
            b.ngay_nhan,
            b.ngay_tra,
            b.trang_thai AS booking_trang_thai
        FROM pay p
        LEFT JOIN booking b ON p.booking_id = b.id
        WHERE p.id = %s
    """, (payment_id,))

    return cursor.fetchone()


def check_booking_exists(cursor, booking_id: int):
    cursor.execute(
        "SELECT id FROM booking WHERE id = %s",
        (booking_id,)
    )

    if cursor.fetchone() is None:
        raise HTTPException(
            status_code=404,
            detail="Booking không tồn tại."
        )


def validate_payment_method(method: str):
    if method not in PAYMENT_METHODS:
        raise HTTPException(
            status_code=422,
            detail=f"Phương thức thanh toán không hợp lệ. "
                   f"Các giá trị được chấp nhận: {PAYMENT_METHODS}"
        )


def validate_payment_status(status: str):
    if status not in PAYMENT_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Trạng thái thanh toán không hợp lệ. "
                   f"Các giá trị được chấp nhận: {PAYMENT_STATUSES}"
        )


# =========================
# GET ALL PAYMENTS
# =========================

@router.get("/")
def get_payments(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                p.id,
                p.booking_id,
                p.ngay_thanh_toan,
                p.so_tien,
                p.method,
                p.status,
                b.phong_id,
                b.khach_id,
                b.ngay_nhan,
                b.ngay_tra,
                b.trang_thai AS booking_trang_thai
            FROM pay p
            LEFT JOIN booking b ON p.booking_id = b.id
            ORDER BY p.id DESC
        """)

        payments = cursor.fetchall()

        return {
            "message": "Lấy danh sách thanh toán thành công",
            "total": len(payments),
            "payments": payments
        }

    finally:
        cursor.close()


# =========================
# GET PAYMENT BY ID
# =========================

@router.get("/{payment_id}")
def get_payment(payment_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        payment = get_payment_by_id(cursor, payment_id)

        if payment is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy thanh toán."
            )

        return {
            "message": "Lấy thông tin thanh toán thành công",
            "payment": payment
        }

    finally:
        cursor.close()


# =========================
# CREATE PAYMENT
# =========================

@router.post("/", status_code=201)
def create_payment(data: PaymentCreate, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        check_booking_exists(cursor, data.booking_id)
        validate_payment_method(data.method)
        validate_payment_status(data.status)

        # Không tạo thanh toán thành công ngay từ đầu.
        # Cần cập nhật trạng thái sau khi hóa đơn đã tồn tại.
        if data.status == "THANH_CONG":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Không tạo thanh toán với trạng thái THANH_CONG. "
                    "Hãy tạo ở trạng thái CHO_THANH_TOAN, "
                    "đảm bảo hóa đơn đã được lập và đúng số tiền, "
                    "sau đó dùng PUT để xác nhận thanh toán."
                )
            )

        cursor.execute("""
            INSERT INTO pay (
                booking_id,
                ngay_thanh_toan,
                so_tien,
                method,
                status
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data.booking_id,
            data.ngay_thanh_toan,
            data.so_tien,
            data.method,
            data.status
        ))

        new_id = cursor.lastrowid
        db.commit()

        payment = get_payment_by_id(cursor, new_id)

        return {
            "message": "Tạo thanh toán thành công",
            "id": new_id,
            "payment": payment
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Lỗi khi tạo thanh toán: {str(e)}"
        )

    finally:
        cursor.close()


# =========================
# UPDATE PAYMENT
# =========================

@router.put("/{payment_id}")
def update_payment(
    payment_id: int,
    data: PaymentUpdate,
    db=Depends(get_db)
):
    cursor = db.cursor(dictionary=True)

    try:
        existing = get_payment_by_id(cursor, payment_id)

        if existing is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy thanh toán."
            )

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="Không có thông tin nào được gửi để cập nhật."
            )

        if "method" in update_data:
            validate_payment_method(update_data["method"])

        if "status" in update_data:
            validate_payment_status(update_data["status"])

        allowed_fields = [
            "ngay_thanh_toan",
            "so_tien",
            "method",
            "status"
        ]

        fields = [
            field for field in update_data
            if field in allowed_fields
        ]

        set_clause = ", ".join(
            f"{field} = %s" for field in fields
        )

        values = [update_data[field] for field in fields]
        values.append(payment_id)

        cursor.execute(
            f"""
            UPDATE pay
            SET {set_clause}
            WHERE id = %s
            """,
            tuple(values)
        )

        db.commit()

        updated_payment = get_payment_by_id(cursor, payment_id)

        return {
            "message": "Cập nhật thanh toán thành công",
            "payment": updated_payment
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "Không thể cập nhật thanh toán. "
                "Có thể trigger từ chối do hóa đơn chưa tồn tại, "
                "số tiền không khớp hoặc dữ liệu vi phạm ràng buộc. "
                f"Chi tiết: {str(e)}"
            )
        )

    finally:
        cursor.close()


# =========================
# DELETE PAYMENT
# =========================

@router.delete("/{payment_id}")
def delete_payment(payment_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        existing = get_payment_by_id(cursor, payment_id)

        if existing is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy thanh toán."
            )

        cursor.execute(
            "DELETE FROM pay WHERE id = %s",
            (payment_id,)
        )

        db.commit()

        return {
            "message": "Xóa thanh toán thành công",
            "id": payment_id
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "Không thể xóa thanh toán. "
                "Có thể thanh toán đang được liên kết với hóa đơn. "
                f"Chi tiết: {str(e)}"
            )
        )

    finally:
        cursor.close()
